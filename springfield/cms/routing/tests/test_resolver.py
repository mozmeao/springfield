# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the resolver page rendering and serialization."""

from types import SimpleNamespace

from django.test import RequestFactory

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.routing.models import RoutingCondition, RoutingRule
from springfield.cms.routing.resolver import render_resolver, serialize_manifest, serialize_rules
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]

rf = RequestFactory()


@pytest.fixture
def routed_page():
    # Build under the default site's root so pages have real URLs.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="c8-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="c8-variant", parent=canonical, live=True)
    rule = RoutingRule.objects.create(page=canonical, target=target)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)
    RoutingCondition.objects.create(rule=rule, signal="country", operator="is", expected_value="US", sort_order=1)
    return SimpleNamespace(canonical=canonical, target=target, rule=rule)


# ---------------------------------------------------------------------------
# Serialization (the data the client evaluator needs).
# ---------------------------------------------------------------------------


def test_serialize_rules_carries_target_and_typed_conditions(routed_page):
    rules = serialize_rules(routed_page.canonical)
    assert len(rules) == 1
    rule = rules[0]
    assert rule["target"] == routed_page.target.get_url()
    assert [c["signal"] for c in rule["conditions"]] == ["platform", "country"]
    # Value type is drawn from the registry so the evaluator compares correctly.
    assert rule["conditions"][0]["valueType"] == "enum"
    assert rule["conditions"][0]["operator"] == "is"
    assert rule["conditions"][0]["expected"] == "windows"


def test_serialize_rules_skips_unpublished_targets(routed_page):
    routed_page.target.live = False
    routed_page.target.save()
    assert serialize_rules(routed_page.canonical) == []


def test_serialize_rules_emits_match_all_flag(routed_page):
    # A conditionful rule carries matchAll=False.
    rules = serialize_rules(routed_page.canonical)
    assert rules[0]["matchAll"] is False


def test_serialize_rules_emits_match_all_rule_with_no_conditions(routed_page):
    RoutingRule.objects.create(page=routed_page.canonical, target=routed_page.target, match_all=True, sort_order=1)
    rules = serialize_rules(routed_page.canonical)
    # The match-all rule is emitted with no conditions (and matchAll=True).
    match_all_rules = [rule for rule in rules if rule["matchAll"]]
    assert len(match_all_rules) == 1
    assert match_all_rules[0]["conditions"] == []


def test_serialize_rules_skips_empty_non_match_all_rule(routed_page):
    # A rule with neither conditions nor match_all is defensively dropped, never
    # emitted as a match-everyone rule.
    RoutingRule.objects.create(page=routed_page.canonical, target=routed_page.target, sort_order=1)
    rules = serialize_rules(routed_page.canonical)
    assert len(rules) == 1
    assert rules[0]["conditions"] != []


def test_serialize_rules_drops_a_lone_conditionless_non_match_all_rule():
    # The page-form floor blocks *authoring* a conditionless, non-match-all rule (it would
    # match the whole triggered audience), but the ORM/API path has no such floor and does not
    # call clean(). serialize_rules is the runtime backstop, and it is the *only* guard on that
    # path — so pin it directly: a lone ORM-created rule with no conditions and match_all=False
    # is dropped entirely and never reaches the client, even with a perfectly live target.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="c29-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="c29-variant", parent=canonical, live=True)
    RoutingRule.objects.create(page=canonical, target=target, match_all=False)
    assert serialize_rules(canonical) == []


def test_serialize_manifest_maps_signals_to_source_metadata(routed_page):
    manifest = serialize_manifest(serialize_rules(routed_page.canonical))
    assert manifest["platform"] == {"source": "user_agent", "browserStateKey": None, "valueType": "enum"}
    assert manifest["country"]["source"] == "cdn_geo"


# ---------------------------------------------------------------------------
# Rendering.
# ---------------------------------------------------------------------------


def _render(routed_page):
    request = rf.get("/en-US/whatsnew/?routing=1")
    response = render_resolver(request, routed_page.canonical)
    if hasattr(response, "render"):
        response.render()
    return response, response.content.decode("utf-8")


def test_resolver_renders_country_rules_and_manifest(routed_page):
    _response, html = _render(routed_page)
    assert "data-country-code=" in html
    assert "data-routing-rules=" in html
    assert "data-routing-manifest=" in html
    # The serialized target and a signal name reach the client blob.
    assert routed_page.target.get_url() in html
    assert "platform" in html


def test_resolver_renders_localized_status_and_noscript(routed_page):
    _response, html = _render(routed_page)
    assert "Preparing your page" in html
    assert "<noscript>" in html


def test_resolver_response_is_cacheable(routed_page):
    response, _html = _render(routed_page)
    # The plain resolver must stay CDN-cacheable — no no-store (previews add it).
    assert "no-store" not in response.get("Cache-Control", "")


def test_resolver_has_no_inline_script_or_style(routed_page):
    _response, html = _render(routed_page)
    soup = BeautifulSoup(html, "html.parser")
    # CSP: every script is an external bundle (has src); no inline <script> blocks.
    scripts = soup.find_all("script")
    assert scripts, "expected bundled scripts"
    assert all(script.get("src") for script in scripts)
    # All CSS ships via <link> bundles; no inline <style>.
    assert soup.find_all("style") == []
