# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for wnp_dispatch under the client-side architecture.

The dispatcher does NO rule matching. If ``utm_source=update`` is present and
at least one live rule exists on the canonical, the resolver page renders
(200) with the full rule set as JSON; the browser evaluates and navigates.

Preview URL params keep their behavior:
* ``?preview_rule={id}`` (admin) still 302s to that rule's target — a
  server-side shortcut so authors can eyeball variant pages without needing
  live signals to actually match.
* ``?preview_signal=name:value`` (admin) is now embedded into the resolver
  page's ``#user-routing-preview-signals`` JSON blob — the client applies it
  on top of its normal signal resolution.
"""

import json
import re

from django.test import override_settings

import pytest
from wagtail.models import Locale, Page

from springfield.cms.models import RoutingCondition, RoutingRule
from springfield.cms.models.routing import RULE_STATUS_DRAFT, RULE_STATUS_LIVE
from springfield.cms.tests.factories import WhatsNewIndexPageFactory, WhatsNewPage2026Factory

# Fixture-scope helpers ---------------------------------------------------


@pytest.fixture
def _canonical_and_variants(db):
    """WNP tree with a canonical 156 and two variants (children of canonical)."""
    root = Page.objects.get(depth=1)
    home = root.get_children().first() or root.add_child(instance=Page(title="Home", slug="home"))
    en_locale, _ = Locale.objects.get_or_create(language_code="en-US")
    index = WhatsNewIndexPageFactory(parent=home, title="WNP Index", slug="whatsnew", locale=en_locale)
    canonical = WhatsNewPage2026Factory(parent=index, title="WNP 156", slug="156", version="156", locale=en_locale)
    lapsed = WhatsNewPage2026Factory(parent=canonical, title="WNP 156 lapsed", slug="lapsed", version="156", locale=en_locale)
    signed_in = WhatsNewPage2026Factory(parent=canonical, title="WNP 156 signed-in", slug="signed-in", version="156", locale=en_locale)
    return {"index": index, "canonical": canonical, "lapsed": lapsed, "signed_in": signed_in}


def _make_rule(
    canonical,
    target,
    *,
    condition=None,
    conditions=None,
    status=RULE_STATUS_LIVE,
    sort_order=100,
    name="test-rule",
):
    """Create a rule and its condition(s). ``condition=`` is the single-condition
    convenience; ``conditions=`` is a list of dicts of the same shape."""
    rule = RoutingRule(name=name, sort_order=sort_order, parent_page=canonical, target_page=target, status=status)
    rule.save()

    specs = []
    if condition is not None:
        specs.append(condition)
    if conditions is not None:
        specs.extend(conditions)

    for spec in specs:
        signal_name = spec.get("signal") or ""
        if "equals" in spec:
            operator = "is"
            eq = spec["equals"]
            if eq is None:
                expected_values = ""
            elif isinstance(eq, bool):
                expected_values = "true" if eq else "false"
            else:
                expected_values = str(eq)
        else:
            operator = spec.get("op") or "is"
            values = spec.get("values") or []
            parts = ["true" if v is True else "false" if v is False else str(v) for v in values]
            expected_values = "\n".join(parts)
        RoutingCondition.objects.create(rule=rule, signal_name=signal_name, operator=operator, expected_values=expected_values)
    return rule


@pytest.fixture
def _admin_client(client, django_user_model, db):
    """Yield a Django test ``client`` authenticated as a staff user.

    Wraps login in ``override_settings(AUTHENTICATION_BACKENDS=(ModelBackend,),
    USE_SSO_AUTH=False)`` — otherwise ``mozilla_django_oidc.middleware.SessionRefresh``
    sees a logged-in user with no OIDC token in the session and 302s every
    admin request to the Auth0 login URL, defeating the preview-flow
    assertions. Mirrors the ``admin_client`` fixture in
    ``springfield/cms/tests/conftest.py``.
    """
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        user = django_user_model.objects.create_user(username="preview-admin", password="x", is_staff=True)
        client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        yield client


def _parse_json_blob(body: str, element_id: str):
    """Extract and JSON-parse a ``<script id="{id}" type="application/json">``
    block from the resolver page body."""
    pattern = rf'<script[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</script>'
    match = re.search(pattern, body, re.DOTALL)
    assert match is not None, f"Blob {element_id!r} missing from response body"
    return json.loads(match.group(1))


# ---------------------------------------------------------------------------
# Dispatch gate: no rules / no marker / paused / draft
# ---------------------------------------------------------------------------


class TestDispatchGate:
    def _no_resolver(self, response):
        body = response.content.decode("utf-8", errors="replace")
        return 'id="user-routing-rules"' not in body

    @pytest.mark.django_db
    def test_canonical_serves_when_no_rules(self, client, _canonical_and_variants):
        response = client.get("/en-US/whatsnew/156/")
        assert self._no_resolver(response)

    @pytest.mark.django_db
    def test_organic_request_never_serves_resolver(self, client, _canonical_and_variants):
        # No utm_source=update → WNP wrapper gate is closed → resolver never
        # renders, even when a live rule exists.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149")
        assert self._no_resolver(response)

    @pytest.mark.django_db
    def test_routed_mode_param_short_circuits(self, client, _canonical_and_variants):
        # Loop-breaker: a request that already carries ``routed_mode`` has
        # been through routing once. Re-running the router would render the
        # resolver again → client navigates back with the same URL → infinite
        # loop. wnp_dispatch must skip routing when routed_mode is present,
        # regardless of value.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update&routed_mode=none")
        assert self._no_resolver(response)

    @pytest.mark.django_db
    def test_draft_rule_ignored(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            status=RULE_STATUS_DRAFT,
        )
        # Only draft rules exist → resolver would have no rules → dispatcher
        # returns None → canonical serves.
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert self._no_resolver(response)

    @pytest.mark.django_db
    def test_pause_routing_short_circuits_dispatch(self, client, _canonical_and_variants):
        # Emergency kill switch: canonical serves regardless of live rules.
        canonical = _canonical_and_variants["canonical"]
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert self._no_resolver(response)

    @pytest.mark.django_db
    def test_pause_routing_off_by_default(self, client, _canonical_and_variants):
        canonical = _canonical_and_variants["canonical"]
        assert canonical.routing_paused is False
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        # Live rule + utm_source=update + not paused → resolver page.
        assert response.status_code == 200
        assert 'id="user-routing-rules"' in response.content.decode("utf-8")

    @pytest.mark.django_db
    def test_dispatch_scoped_to_wnp_index_children(self, client, _canonical_and_variants):
        # A variant slugged like a version number must NOT be treated as a
        # canonical by the dispatcher. Scope filter limits canonical lookup
        # to direct children of a WhatsNewIndexPage.
        canonical = _canonical_and_variants["canonical"]
        WhatsNewPage2026Factory(
            parent=canonical,
            title="Variant slugged as version",
            slug="999",
            version="999",
            locale=canonical.locale,
        )
        response = client.get("/en-US/whatsnew/999/?utm_source=update")
        # No CMS canonical matches at depth 1 → dispatcher does not run →
        # legacy fallback / locale redirect. The key assertion: no resolver.
        body = response.content.decode("utf-8", errors="replace")
        assert 'id="user-routing-rules"' not in body

    @pytest.mark.django_db
    def test_variant_url_does_not_re_enter_dispatch(self, _canonical_and_variants):
        # URL resolver locks the trailing $ on wnp_dispatch so the variant
        # URL routes to Wagtail's page-serving entry, not back to dispatch.
        from django.urls import resolve

        canonical_match = resolve("/en-US/whatsnew/156/")
        variant_match = resolve("/en-US/whatsnew/156/lapsed/")
        assert canonical_match.url_name == "firefox.whatsnew"
        assert variant_match.url_name == "wagtail_serve"


# ---------------------------------------------------------------------------
# Resolver page: live rules under utm_source=update render the resolver
# ---------------------------------------------------------------------------


class TestResolverPage:
    @pytest.mark.django_db
    def test_live_rule_serves_resolver_page(self, client, _canonical_and_variants):
        # Any live rule + utm_source=update → resolver page (200) with the
        # full rule payload. Signal type doesn't matter — everything is
        # evaluated client-side under the new architecture.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert 'id="user-routing-rules"' in body
        assert 'id="user-routing-signal-metadata"' in body

    @pytest.mark.django_db
    def test_uitour_signal_metadata_emitted(self, client, _canonical_and_variants):
        # UITour-resolved signals need per-request metadata (which UITour key
        # to fetch). Signal-metadata blob carries the mapping.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        metadata = _parse_json_blob(body, "user-routing-signal-metadata")
        assert metadata.get("ai_controls", {}).get("uitour_key") == "aiControls"

    @pytest.mark.django_db
    def test_rules_blob_shape(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            name="lapsed-users-156",
            sort_order=50,
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        rules = _parse_json_blob(body, "user-routing-rules")
        assert isinstance(rules, list) and len(rules) == 1
        rule = rules[0]
        assert rule["name"] == "lapsed-users-156"
        assert rule["priority"] == 50
        assert isinstance(rule["conditions"], list) and rule["conditions"]
        assert "/whatsnew/156/lapsed/" in rule["target_url"]

    @pytest.mark.django_db
    def test_multiple_rules_all_present(self, client, _canonical_and_variants):
        # Two live rules → both appear in the rules blob; the client sorts by
        # priority (sort_order) and evaluates. The server does no ordering
        # beyond preserving priority in the payload.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "lapsed_user", "equals": True},
            sort_order=100,
            name="lower-in-list",
        )
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            sort_order=50,
            name="higher-in-list",
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        rules = _parse_json_blob(response.content.decode("utf-8"), "user-routing-rules")
        by_name = {r["name"]: r for r in rules}
        assert set(by_name) == {"lower-in-list", "higher-in-list"}
        assert by_name["higher-in-list"]["priority"] == 50
        assert by_name["lower-in-list"]["priority"] == 100

    @pytest.mark.django_db
    def test_querystring_preserved_in_variant_target_urls(self, client, _canonical_and_variants):
        # The client navigates to the rule's target_url — the user's incoming
        # utm_* params must survive that hop so downstream analytics see the
        # same query.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update&utm_campaign=156")
        rules = _parse_json_blob(response.content.decode("utf-8"), "user-routing-rules")
        target_url = rules[0]["target_url"]
        assert "oldversion=149" in target_url
        assert "utm_source=update" in target_url
        assert "utm_campaign=156" in target_url

    @pytest.mark.django_db
    def test_resolver_target_urls_carry_client_analytics_params(self, client, _canonical_and_variants):
        # Each embedded target URL gets routed_from / routed_rule /
        # routed_mode=client attribution appended so the client-navigated
        # landing fires the routing event.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
            name="ai-controls-available-156",
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        rules = _parse_json_blob(response.content.decode("utf-8"), "user-routing-rules")
        target_url = rules[0]["target_url"]
        assert "routed_mode=client" in target_url
        assert "routed_from=156" in target_url
        assert "routed_rule=ai-controls-available-156" in target_url

    @pytest.mark.django_db
    def test_spoofed_routed_params_stripped_from_target_urls(self, client, _canonical_and_variants):
        # A hostile / curious user putting ?routed_from=fake on the incoming
        # URL must not shadow the framework-emitted attribution on the target
        # URLs the client will navigate to. (Spoofed ``routed_mode`` is
        # handled separately by the WNP loop-breaker — that request never
        # reaches the resolver at all; see test_routed_mode_param_short_circuits.)
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            name="real-rule",
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update&routed_from=fake&routed_rule=fake-rule")
        rules = _parse_json_blob(response.content.decode("utf-8"), "user-routing-rules")
        target_url = rules[0]["target_url"]
        assert "routed_from=156" in target_url
        assert "routed_rule=real-rule" in target_url
        assert "routed_mode=client" in target_url
        assert "routed_from=fake" not in target_url
        assert "routed_rule=fake-rule" not in target_url

    @pytest.mark.django_db
    def test_resolver_page_has_noscript_meta_refresh(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        assert "<noscript>" in body
        assert 'http-equiv="refresh"' in body
        assert "/whatsnew/156/" in body

    @pytest.mark.django_db
    def test_resolver_page_has_canonical_link_header(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        assert response.status_code == 200
        link_header = response.get("Link", "")
        assert 'rel="canonical"' in link_header
        assert "/whatsnew/156/" in link_header

    @pytest.mark.django_db
    def test_country_code_rendered_on_html_tag(self, client, _canonical_and_variants):
        # Geo signal reaches the client via the site-wide <html
        # data-country-code> attribute (rendered by base-protocol.html from
        # the geo context processor). Verify it's present on the resolver
        # page — the client's country resolver reads it.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "country", "equals": "US"},
        )
        response = client.get(
            "/en-US/whatsnew/156/?utm_source=update",
            HTTP_CLOUDFRONT_VIEWER_COUNTRY="DE",
        )
        body = response.content.decode("utf-8")
        assert 'data-country-code="DE"' in body

    @pytest.mark.django_db
    def test_preview_signals_blob_empty_for_organic_traffic(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        preview = _parse_json_blob(body, "user-routing-preview-signals")
        assert preview == {}

    @pytest.mark.django_db
    def test_canonical_url_blob_carries_loop_breaker(self, client, _canonical_and_variants):
        # The client falls back to this URL when no rule matches. The URL
        # must carry ``routed_mode=none`` so the WNP wrapper's loop-breaker
        # trips and skips re-entering the router. Also asserts the canonical
        # slug attribution rides along for no-match analytics.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update&oldversion=149")
        body = response.content.decode("utf-8")
        canonical_url = _parse_json_blob(body, "user-routing-canonical-url")
        assert "routed_mode=none" in canonical_url
        assert "routed_from=156" in canonical_url
        # Original querystring survives so the loop-breaker doesn't wipe
        # legitimate params (utm_source is what got us into the router).
        assert "utm_source=update" in canonical_url
        assert "oldversion=149" in canonical_url

    @pytest.mark.django_db
    def test_empty_condition_does_not_kill_rule(self, client, _canonical_and_variants):
        # A rule with N valid conditions plus one draft (blank signal_name)
        # condition should still match when the N valid conditions match.
        # RoutingCondition.as_dict() returns {} for blank signals; if those
        # empties reach the client, the whole rule silently fails via AND.
        rule = _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        # Add a blank draft condition alongside the valid one.
        RoutingCondition.objects.create(rule=rule, signal_name="", operator="is", expected_values="")
        response = client.get("/en-US/whatsnew/156/?utm_source=update&oldversion=149")
        rules = _parse_json_blob(response.content.decode("utf-8"), "user-routing-rules")
        assert len(rules) == 1
        # Only the non-empty condition survives serialization.
        assert len(rules[0]["conditions"]) == 1
        assert rules[0]["conditions"][0]["signal"] == "lapsed_user"


# ---------------------------------------------------------------------------
# Preview: preview_rule stays a server-side 302 shortcut
# ---------------------------------------------------------------------------


class TestPreviewRule:
    @pytest.mark.django_db
    def test_preview_rule_forces_redirect_regardless_of_signals(self, _admin_client, _canonical_and_variants):
        # ``?preview_rule={id}`` from an admin session redirects to that
        # rule's target without evaluating signals. Applies even to draft
        # rules — marketing needs to eyeball unpublished variants.
        rule = _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            status=RULE_STATUS_DRAFT,
            name="draft-not-live",
        )
        response = _admin_client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]
        assert response.get("Cache-Control") == "no-store"

    @pytest.mark.django_db
    def test_preview_rule_ignored_for_unauthenticated_requests(self, client, _canonical_and_variants):
        rule = _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            status=RULE_STATUS_DRAFT,
        )
        response = client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
        # No login → preview ignored. Draft-only rules → no live-rule
        # resolver page either → canonical serves.
        body = response.content.decode("utf-8", errors="replace")
        location = response.get("Location", "") or ""
        assert "/156/lapsed" not in location
        assert 'id="user-routing-rules"' not in body

    @pytest.mark.django_db
    def test_preview_rule_scoped_to_this_canonical(self, _admin_client, _canonical_and_variants):
        # A rule ID that belongs to a DIFFERENT canonical must NOT be
        # previewable via this canonical's URL.
        other_canonical = WhatsNewPage2026Factory(
            parent=_canonical_and_variants["index"],
            title="WNP 157",
            slug="157",
            version="157",
        )
        other_variant = WhatsNewPage2026Factory(
            parent=other_canonical,
            title="WNP 157 variant",
            slug="variant",
            version="157",
        )
        other_rule = _make_rule(
            other_canonical,
            other_variant,
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = _admin_client.get(f"/en-US/whatsnew/156/?preview_rule={other_rule.pk}&utm_source=update")
        location = response.get("Location", "") or ""
        assert "/157/variant" not in location

    @pytest.mark.django_db
    def test_preview_rule_bypasses_pause(self, _admin_client, _canonical_and_variants):
        # Preview intentionally ignores routing_paused so authors can verify
        # while production routing is halted.
        canonical = _canonical_and_variants["canonical"]
        rule = _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        response = _admin_client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]


# ---------------------------------------------------------------------------
# Preview: preview_signal is now embedded into the resolver page's blob
# ---------------------------------------------------------------------------


class TestPreviewSignal:
    @pytest.mark.django_db
    def test_preview_signal_embedded_in_resolver(self, _admin_client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = _admin_client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        assert response.status_code == 200
        preview = _parse_json_blob(response.content.decode("utf-8"), "user-routing-preview-signals")
        assert preview == {"lapsed_user": True}
        # Preview responses must never be cached — freshness matters more
        # than throughput while authors are iterating.
        assert response.get("Cache-Control") == "no-store"

    @pytest.mark.django_db
    def test_preview_signal_bypasses_pause(self, _admin_client, _canonical_and_variants):
        # An admin previewing must still see the resolver page even when
        # routing_paused is on, so they can verify their fix before flipping
        # pause off.
        canonical = _canonical_and_variants["canonical"]
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        response = _admin_client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert 'id="user-routing-rules"' in body
        preview = _parse_json_blob(body, "user-routing-preview-signals")
        assert preview == {"lapsed_user": True}

    @pytest.mark.django_db
    def test_preview_signal_ignored_for_unauthenticated_requests(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        # No login → preview signal ignored → resolver blob is empty.
        body = response.content.decode("utf-8")
        preview = _parse_json_blob(body, "user-routing-preview-signals")
        assert preview == {}
        # Un-authed request must NOT be marked no-store — cacheability is
        # the whole point of the client-side architecture.
        assert response.get("Cache-Control") != "no-store"

    @pytest.mark.django_db
    def test_preview_signal_accepts_admin_bool_vocabulary(self, _admin_client, _canonical_and_variants):
        # true / false / yes / no coerce to Python bools so preview URLs
        # built with admin-side values match rules the admin authored.
        # ``1`` / ``0`` are deliberately NOT in this list — they coerce to
        # integers so INT-typed signal previews (firefox_version:151) work.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        for truthy in ("true", "yes"):
            response = _admin_client.get(f"/en-US/whatsnew/156/?preview_signal=lapsed_user:{truthy}&utm_source=update")
            assert response.status_code == 200, truthy
            preview = _parse_json_blob(response.content.decode("utf-8"), "user-routing-preview-signals")
            assert preview == {"lapsed_user": True}, truthy

    @pytest.mark.django_db
    def test_preview_signal_int_values_stay_int(self, _admin_client, _canonical_and_variants):
        # INT-typed signals (firefox_version, profile_age_days) need int
        # preview values. Regression guard for the earlier bool-first
        # coercion order that silently mapped ``1`` to True and broke
        # int-signal previews.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "firefox_version", "equals": 151},
        )
        response = _admin_client.get("/en-US/whatsnew/156/?preview_signal=firefox_version:151&utm_source=update")
        preview = _parse_json_blob(response.content.decode("utf-8"), "user-routing-preview-signals")
        assert preview == {"firefox_version": 151}
        # Edge case: ``firefox_version:1`` must be int 1, not True.
        response = _admin_client.get("/en-US/whatsnew/156/?preview_signal=firefox_version:1&utm_source=update")
        preview = _parse_json_blob(response.content.decode("utf-8"), "user-routing-preview-signals")
        assert preview == {"firefox_version": 1}

    @pytest.mark.django_db
    def test_preview_signal_supports_string_values(self, _admin_client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = _admin_client.get("/en-US/whatsnew/156/?preview_signal=ai_controls:available&utm_source=update")
        preview = _parse_json_blob(response.content.decode("utf-8"), "user-routing-preview-signals")
        assert preview == {"ai_controls": "available"}

    @pytest.mark.django_db
    def test_invalid_preview_rule_still_marks_no_store_on_resolver(self, _admin_client, _canonical_and_variants):
        # A bogus preview_rule ID should silently miss but the request is
        # still an admin preview, so the resolver response (rendered because
        # a real live rule exists) still gets Cache-Control: no-store.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = _admin_client.get("/en-US/whatsnew/156/?preview_rule=999999&oldversion=149&utm_source=update")
        assert response.status_code == 200
        assert response.get("Cache-Control") == "no-store"
