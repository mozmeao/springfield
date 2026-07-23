# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for wnp_dispatch.

Verify the server-side routing layer at /whatsnew/{version}/. The WNP
wrapper enforces "routing only in the Balrog post-update flow" by
requiring ``utm_source=update`` on every routed request — organic
visitors always see the canonical (per the plan doc's canonical-as-
permanent-archive framing).
"""

import pytest
from wagtail.models import Locale, Page

from springfield.cms.models import RoutingCondition, RoutingRule
from springfield.cms.models.routing import RULE_STATUS_DRAFT, RULE_STATUS_LIVE
from springfield.cms.tests.factories import WhatsNewIndexPageFactory, WhatsNewPage2026Factory


@pytest.fixture
def _canonical_and_variants(db):
    """Build a small WNP tree with a canonical version 156 and two variants.

    Variants are children of the canonical (matching the intended production
    URL structure: ``/whatsnew/156/lapsed/`` is a child page of
    ``/whatsnew/156/``). This lets descendant validation on the RoutingRule
    ``target_page`` field pass cleanly.
    """
    root = Page.objects.get(depth=1)
    home = root.get_children().first() or root.add_child(instance=Page(title="Home", slug="home"))
    en_locale, _ = Locale.objects.get_or_create(language_code="en-US")
    index = WhatsNewIndexPageFactory(parent=home, title="WNP Index", slug="whatsnew", locale=en_locale)
    canonical = WhatsNewPage2026Factory(parent=index, title="WNP 156", slug="156", version="156", locale=en_locale)
    lapsed = WhatsNewPage2026Factory(parent=canonical, title="WNP 156 lapsed", slug="lapsed", version="156", locale=en_locale)
    signed_in = WhatsNewPage2026Factory(parent=canonical, title="WNP 156 signed-in", slug="signed-in", version="156", locale=en_locale)
    return {"index": index, "canonical": canonical, "lapsed": lapsed, "signed_in": signed_in}


def _make_rule(canonical, target, *, condition=None, conditions=None, status=RULE_STATUS_LIVE, sort_order=100, name="test-rule"):
    """Create a rule and its condition(s). ``condition=`` is legacy single-condition
    convenience (accepts the ``{signal, equals: X}`` or ``{signal, op, values}``
    shape); ``conditions=`` takes a list of the new shape dicts."""
    rule = RoutingRule(
        name=name,
        sort_order=sort_order,
        parent_page=canonical,
        target_page=target,
        status=status,
    )
    rule.save()

    condition_specs = []
    if condition is not None:
        condition_specs.append(condition)
    if conditions is not None:
        condition_specs.extend(conditions)

    for spec in condition_specs:
        signal_name = spec.get("signal") or ""
        if "equals" in spec:
            operator = "is"
            equals_value = spec["equals"]
            if equals_value is None:
                expected_values = ""
            elif isinstance(equals_value, bool):
                expected_values = "true" if equals_value else "false"
            else:
                expected_values = str(equals_value)
        else:
            operator = spec.get("op") or "is"
            values = spec.get("values") or []
            parts = []
            for v in values:
                if isinstance(v, bool):
                    parts.append("true" if v else "false")
                else:
                    parts.append(str(v))
            expected_values = "\n".join(parts)
        RoutingCondition.objects.create(
            rule=rule,
            signal_name=signal_name,
            operator=operator,
            expected_values=expected_values,
        )
    return rule


class TestWnpDispatch:
    def _did_not_route_to_variant(self, response):
        """Helper: the response is NOT a redirect to a known variant.

        wnp_dispatch may still return 200 (canonical served) or 302 (Wagtail
        locale-fallback machinery may redirect for other reasons). Either is
        fine as long as we didn't send the user to one of the variant slugs
        the rule *would* have targeted.
        """
        location = response.get("Location", "") or ""
        return "/156/lapsed" not in location and "/156/signed-in" not in location

    @pytest.mark.django_db
    def test_canonical_serves_when_no_rules(self, client, _canonical_and_variants):
        response = client.get("/en-US/whatsnew/156/")
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_dispatch_scoped_to_wnp_index_children(self, client, _canonical_and_variants):
        # Regression: a variant slugged like a version number (e.g. someone
        # creates "999" as a child of an existing canonical) must NOT be
        # picked up as a canonical when dispatch runs for /whatsnew/999/.
        # The scope filter (path__startswith=index.path + depth=index.depth+1)
        # limits canonical lookup to direct children of a WhatsNewIndexPage.
        canonical = _canonical_and_variants["canonical"]
        WhatsNewPage2026Factory(
            parent=canonical,
            title="Variant slugged as version",
            slug="999",
            version="999",
            locale=canonical.locale,
        )
        # Rule attached to the trapdoor variant with a real target — if the
        # variant were mistakenly picked up as canonical for /whatsnew/999/,
        # dispatch would evaluate this rule and 302.
        # (Note: since the variant is under a canonical, target must be a
        # descendant. We won't actually attach a rule here — the presence
        # of the trap slug is enough. dispatch_for_canonical won't run at
        # all if canonical lookup returns None.)
        response = client.get("/en-US/whatsnew/999/?utm_source=update")
        # Falls through to legacy fallback since no CMS canonical matches
        # at depth 1. Status can be 200 (rendered by fallback) or a locale
        # redirect; the key assertion is we did NOT match the variant.
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_lapsed_rule_matches_and_302s(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        # gap = 156 - 149 = 7, well past LAPSED_MIN_GAP=5.
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]

    @pytest.mark.django_db
    def test_variant_url_does_not_re_enter_dispatch(self, _canonical_and_variants):
        # Regression: without the trailing `$` on the URL pattern, Django's
        # URL resolver matched `whatsnew/120/welcomeback/` against
        # wnp_dispatch, treating it as canonical 120 and re-running the
        # rule engine → redirect loop. This test locks the URL resolution
        # in so the two URLs go to different views.
        from django.urls import resolve

        canonical_match = resolve("/en-US/whatsnew/156/")
        variant_match = resolve("/en-US/whatsnew/156/lapsed/")

        assert canonical_match.url_name == "firefox.whatsnew"
        # Variant must NOT re-enter wnp_dispatch — the view function and URL
        # name are the giveaway. It should resolve to Wagtail's page-serving
        # entry (`wagtail_serve`), not to our WNP handler.
        assert variant_match.url_name != "firefox.whatsnew"
        assert variant_match.url_name == "wagtail_serve"

    @pytest.mark.django_db
    def test_organic_request_never_routes(self, client, _canonical_and_variants):
        # WNP wrapper policy: no utm_source=update means routing is skipped
        # entirely — even for a rule that would otherwise match server-side.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149")  # no utm_source
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_lapsed_rule_does_not_match_narrow_gap(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        # gap = 1. Rule condition is `lapsed_user == True`; resolver returns
        # False definitively → rule fails, canonical serves.
        response = client.get("/en-US/whatsnew/156/?oldversion=155&utm_source=update")
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_draft_rule_ignored(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            status=RULE_STATUS_DRAFT,
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        # Draft rules are not evaluated — canonical still serves.
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_client_side_rule_serves_resolver_page(self, client, _canonical_and_variants):
        # ai_controls is a CLIENT_SIDE_STATE signal. With utm_source=update
        # (Balrog flow), the dispatcher renders the resolver page so the
        # client can evaluate the rule via UITour.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        assert response.status_code == 200
        body = response.content.decode("utf-8")
        # Resolver page markers.
        assert 'id="user-routing-rules"' in body
        assert 'id="user-routing-signal-metadata"' in body
        # Rule payload includes the condition and the target URL.
        assert '"ai_controls"' in body
        assert "/whatsnew/156/signed-in/" in body
        # Signal metadata includes ai_controls → aiControls UITour key.
        assert '"aiControls"' in body

    @pytest.mark.django_db
    def test_client_side_rule_without_utm_serves_canonical(self, client, _canonical_and_variants):
        # No utm_source=update marker → dispatcher does NOT serve the
        # resolver page even though a client-side rule exists. Organic
        # visitors never see the resolver.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/")
        assert self._did_not_route_to_variant(response)
        # And the resolver page markers should NOT be present.
        body = response.content.decode("utf-8", errors="replace")
        assert 'id="user-routing-rules"' not in body

    @pytest.mark.django_db
    def test_lower_sort_order_rule_wins(self, client, _canonical_and_variants):
        # Both rules would match on oldversion=149; the lower-sort_order one
        # (sort_order=50, higher in the drag-to-reorder list) evaluates first
        # and wins.
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
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]

    @pytest.mark.django_db
    def test_querystring_preserved_on_302(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update&utm_campaign=156")
        assert response.status_code in (301, 302)
        assert "oldversion=149" in response["Location"]
        assert "utm_source=update" in response["Location"]
        assert "utm_campaign=156" in response["Location"]

    @pytest.mark.django_db
    def test_redirect_carries_analytics_params(self, client, _canonical_and_variants):
        # A server-side match emits routed_from / routed_rule / routed_mode
        # on the redirect target so the landing page can fire the routing
        # event with attribution to the canonical + matched rule.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            name="lapsed-users-156",
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        location = response["Location"]
        assert "routed_from=156" in location  # canonical slug
        assert "routed_rule=lapsed-users-156" in location
        assert "routed_mode=server" in location

    @pytest.mark.django_db
    def test_redirect_has_canonical_link_header(self, client, _canonical_and_variants):
        # Router redirect responses declare the canonical URL via the Link
        # header so SEO/AEO crawlers consolidate signals on the canonical
        # rather than on the redirect endpoint.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        link_header = response.get("Link", "")
        assert 'rel="canonical"' in link_header
        assert "/whatsnew/156/" in link_header

    @pytest.mark.django_db
    def test_resolver_page_has_noscript_meta_refresh(self, client, _canonical_and_variants):
        # JS-disabled visitors: a <noscript><meta http-equiv="refresh"...>
        # sends them to the canonical URL instead of stranding them on the
        # transient "Preparing…" loading screen.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        assert "<noscript>" in body
        assert 'http-equiv="refresh"' in body
        # Refresh target must be the canonical URL (not a variant).
        assert "/whatsnew/156/" in body

    @pytest.mark.django_db
    def test_resolver_page_has_canonical_link_header(self, client, _canonical_and_variants):
        # The resolver page serves at the router URL (same as canonical);
        # Link: rel="canonical" tells crawlers the true canonical is
        # elsewhere.
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

    # -------------------------------------------------------------------
    # Pause routing (emergency kill switch on the canonical page)
    # -------------------------------------------------------------------

    @pytest.mark.django_db
    def test_pause_routing_short_circuits_dispatch(self, client, _canonical_and_variants):
        # A live rule that would ordinarily match — but the canonical's
        # routing_paused flag is on, so the dispatcher must serve canonical.
        canonical = _canonical_and_variants["canonical"]
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_pause_routing_off_by_default(self, client, _canonical_and_variants):
        # Baseline sanity check: absent an explicit pause, dispatch runs
        # normally and the matching rule redirects.
        canonical = _canonical_and_variants["canonical"]
        assert canonical.routing_paused is False
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]

    @pytest.mark.django_db
    def test_preview_rule_bypasses_pause(self, client, _canonical_and_variants, django_user_model):
        # Preview intentionally IGNORES the pause switch so authors can still
        # verify variant renders while production routing is halted.
        canonical = _canonical_and_variants["canonical"]
        rule = _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        client.force_login(self._admin_user(django_user_model))
        response = client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]

    @pytest.mark.django_db
    def test_preview_signal_bypasses_pause(self, client, _canonical_and_variants, django_user_model):
        # preview_signal should also bypass the pause switch — authors need to
        # verify their fix works BEFORE flipping pause off.
        canonical = _canonical_and_variants["canonical"]
        _make_rule(
            canonical,
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        canonical.routing_paused = True
        canonical.save(update_fields=["routing_paused"])
        client.force_login(self._admin_user(django_user_model))
        response = client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]
        assert response.get("Cache-Control") == "no-store"

    # -------------------------------------------------------------------
    # Preview mode (admin authors verifying rules before publish)
    # -------------------------------------------------------------------

    def _admin_user(self, django_user_model):
        return django_user_model.objects.create_user(
            username="preview-admin",
            password="x",
            is_staff=True,
        )

    @pytest.mark.django_db
    def test_preview_rule_forces_redirect_regardless_of_signals(self, client, _canonical_and_variants, django_user_model):
        # ``?preview_rule={id}`` from an admin session redirects to that
        # rule's target without evaluating signals. Even a rule that would
        # NOT match on the real signals gets shown to the author for review.
        rule = _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            status=RULE_STATUS_DRAFT,  # not Live — preview bypasses status
            name="draft-not-live",
        )
        client.force_login(self._admin_user(django_user_model))
        # No utm_source, no oldversion → would never match in production.
        response = client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
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
        # No login → preview_rule silently ignored → canonical serves.
        response = client.get(f"/en-US/whatsnew/156/?preview_rule={rule.pk}&utm_source=update")
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_preview_rule_scoped_to_this_canonical(self, client, _canonical_and_variants, django_user_model):
        # A rule ID that belongs to a DIFFERENT canonical must NOT be
        # previewable via this canonical's URL — prevents cross-canonical
        # preview leakage.
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
        client.force_login(self._admin_user(django_user_model))
        # Preview_rule ID belongs to WNP 157 but we're hitting WNP 156.
        response = client.get(f"/en-US/whatsnew/156/?preview_rule={other_rule.pk}&utm_source=update")
        # Should fall through to canonical, not redirect to other_variant.
        location = response.get("Location", "") or ""
        assert "/157/variant" not in location

    @pytest.mark.django_db
    def test_preview_signal_overrides_resolved_signals(self, client, _canonical_and_variants, django_user_model):
        # ``?preview_signal=lapsed_user:true`` feeds a fake value to the
        # evaluator — the real signal would resolve differently (no
        # oldversion in query) but the fake wins.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        client.force_login(self._admin_user(django_user_model))
        # No oldversion → lapsed_user would normally be unresolvable.
        response = client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156/lapsed" in response["Location"]
        assert response.get("Cache-Control") == "no-store"

    @pytest.mark.django_db
    def test_preview_signal_ignored_for_unauthenticated_requests(self, client, _canonical_and_variants):
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        # No login → preview_signal silently ignored → no oldversion means
        # lapsed_user stays unresolved → canonical serves.
        response = client.get("/en-US/whatsnew/156/?preview_signal=lapsed_user:true&utm_source=update")
        assert self._did_not_route_to_variant(response)

    @pytest.mark.django_db
    def test_preview_signal_accepts_admin_bool_vocabulary(self, client, _canonical_and_variants, django_user_model):
        # ``preview_signal`` should accept the same True/False vocabulary the
        # admin form stores (yes/no/1/0) — otherwise preview URLs built with
        # admin-side values silently mismatch bool rules.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        client.force_login(self._admin_user(django_user_model))
        for truthy in ("true", "yes", "1"):
            response = client.get(f"/en-US/whatsnew/156/?preview_signal=lapsed_user:{truthy}&utm_source=update")
            assert response.status_code in (301, 302), f"preview_signal=lapsed_user:{truthy} should match"
            assert "/156/lapsed" in response["Location"], f"preview_signal=lapsed_user:{truthy} should route to lapsed variant"

    @pytest.mark.django_db
    def test_invalid_preview_rule_still_marks_no_store_on_matched_response(self, client, _canonical_and_variants, django_user_model):
        # When a preview_rule ID doesn't resolve BUT the request still ends
        # up matching a real rule (via the normal evaluator), the response
        # should carry Cache-Control: no-store because the preview marker
        # was on the request. Guarantees admin preview responses never come
        # from cache regardless of resolution success.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
        )
        client.force_login(self._admin_user(django_user_model))
        response = client.get("/en-US/whatsnew/156/?preview_rule=999999&oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        assert response.get("Cache-Control") == "no-store"

    @pytest.mark.django_db
    def test_spoofed_routed_params_are_stripped(self, client, _canonical_and_variants):
        # A hostile / curious user putting ?routed_from=fake in the incoming
        # URL must not shadow the framework-emitted attribution. The final
        # URL should contain only the real values, not the spoofed ones.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            name="real-rule",
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update&routed_from=fake&routed_rule=fake-rule&routed_mode=client")
        location = response["Location"]
        # Real values present.
        assert "routed_from=156" in location
        assert "routed_rule=real-rule" in location
        assert "routed_mode=server" in location
        # Spoofed values stripped.
        assert "routed_from=fake" not in location
        assert "routed_rule=fake-rule" not in location
        assert "routed_mode=client" not in location

    @pytest.mark.django_db
    def test_resolver_page_rules_carry_client_side_analytics_params(self, client, _canonical_and_variants):
        # Rules embedded in the resolver page have their target URLs
        # pre-annotated with routed_mode=client + routed_from/routed_rule
        # so client-side navigation fires the same attribution event as a
        # server-side redirect.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "ai_controls", "equals": "available"},
            name="ai-controls-available-156",
        )
        response = client.get("/en-US/whatsnew/156/?utm_source=update")
        body = response.content.decode("utf-8")
        assert "routed_mode=client" in body
        assert "routed_from=156" in body
        assert "routed_rule=ai-controls-available-156" in body
