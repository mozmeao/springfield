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

from springfield.cms.models import RoutingRule
from springfield.cms.models.routing import RULE_STATUS_DRAFT, RULE_STATUS_LIVE
from springfield.cms.tests.factories import WhatsNewIndexPageFactory, WhatsNewPage2026Factory


@pytest.fixture
def _canonical_and_variants(db):
    """Build a small WNP tree with a canonical version 156 and two variants."""
    root = Page.objects.get(depth=1)
    home = root.get_children().first() or root.add_child(instance=Page(title="Home", slug="home"))
    en_locale, _ = Locale.objects.get_or_create(language_code="en-US")
    index = WhatsNewIndexPageFactory(parent=home, title="WNP Index", slug="whatsnew", locale=en_locale)
    canonical = WhatsNewPage2026Factory(parent=index, title="WNP 156", slug="156", version="156", locale=en_locale)
    lapsed = WhatsNewPage2026Factory(parent=index, title="WNP 156 lapsed", slug="156-lapsed", version="156", locale=en_locale)
    signed_in = WhatsNewPage2026Factory(parent=index, title="WNP 156 signed-in", slug="156-signed-in", version="156", locale=en_locale)
    return {"index": index, "canonical": canonical, "lapsed": lapsed, "signed_in": signed_in}


def _make_rule(canonical, target, *, condition, status=RULE_STATUS_LIVE, priority=100, name="test-rule"):
    rule = RoutingRule(
        name=name,
        priority=priority,
        parent_page=canonical,
        target_page=target,
        condition=condition,
        status=status,
    )
    rule.save()
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
        return "/156-lapsed" not in location and "/156-signed-in" not in location

    @pytest.mark.django_db
    def test_canonical_serves_when_no_rules(self, client, _canonical_and_variants):
        response = client.get("/en-US/whatsnew/156/")
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
        assert "/156-lapsed" in response["Location"]

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
        assert "/whatsnew/156-signed-in/" in body
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
    def test_lower_priority_rule_wins(self, client, _canonical_and_variants):
        # Both rules would match on oldversion=149; the lower-priority one
        # (priority=50) evaluates first and wins.
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["signed_in"],
            condition={"signal": "lapsed_user", "equals": True},
            priority=100,
            name="high-priority",
        )
        _make_rule(
            _canonical_and_variants["canonical"],
            _canonical_and_variants["lapsed"],
            condition={"signal": "lapsed_user", "equals": True},
            priority=50,
            name="low-priority",
        )
        response = client.get("/en-US/whatsnew/156/?oldversion=149&utm_source=update")
        assert response.status_code in (301, 302)
        assert "/156-lapsed" in response["Location"]

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
