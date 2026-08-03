# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the resolver page rendering and serialization."""

from types import SimpleNamespace

from django.test import RequestFactory
from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, Page, Site

from springfield.cms.routing.mixins import RoutingMixin
from springfield.cms.routing.models import RoutingCondition, RoutingRule
from springfield.cms.routing.resolver import render_resolver, serialize_manifest, serialize_rules
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]

rf = RequestFactory()


@pytest.fixture
def routed_page():
    # Build under the default site's root so pages have real URLs.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="resolver-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="resolver-variant", parent=canonical, live=True)
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


def test_serialize_rules_omits_conditions_from_a_match_all_rule(routed_page):
    # match_all means "every triggered visitor", which is what the client already does with
    # such a rule — so conditions on it are inert. Emitting them would make the payload
    # contradict itself and invite a future reader to "fix" the client into honouring them.
    rule = routed_page.rule
    rule.match_all = True
    rule.save()

    rules = serialize_rules(routed_page.canonical)
    assert rules[0]["matchAll"] is True
    assert rules[0]["conditions"] == []


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
    canonical = SimpleRichTextPageFactory(slug="conditionless-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="conditionless-variant", parent=canonical, live=True)
    RoutingRule.objects.create(page=canonical, target=target, match_all=False)
    assert serialize_rules(canonical) == []


def test_serialize_rules_drops_a_target_under_a_different_page():
    # Copying a page copies its rules, and the copies still point into the *source* page's
    # subtree — so a visitor to the copy would be routed to content belonging to the page
    # they didn't ask for. The page form blocks authoring this; the ORM/API path does not,
    # and a copy arrives that way.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="hosting-canonical", parent=site_root)
    unrelated = SimpleRichTextPageFactory(slug="unrelated-canonical", parent=site_root)
    stray = SimpleRichTextPageFactory(slug="unrelated-variant", parent=unrelated, live=True)
    rule = RoutingRule.objects.create(page=canonical, target=stray, match_all=True)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)

    assert serialize_rules(canonical) == []
    assert RoutingMixin._has_live_routing_rules(canonical) is False


def test_serialize_rules_drops_a_rule_that_targets_its_own_page():
    # Routing a visitor to the URL they are already on re-renders the resolver, which
    # evaluates and navigates again: the loop-breaker only rides along on the *fallback*
    # path, so nothing stops the cycle. The page form blocks it; the ORM/API path does not.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="self-targeting-canonical", parent=site_root, live=True)
    rule = RoutingRule.objects.create(page=canonical, target=canonical, match_all=True)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)

    assert serialize_rules(canonical) == []
    assert RoutingMixin._has_live_routing_rules(canonical) is False


def test_serialize_rules_drops_a_rule_whose_target_was_deleted(routed_page):
    # Deleting the target nulls it rather than blocking the delete, so the serializer meets a
    # rule with no target at all. It must drop it and carry on, not raise.
    routed_page.target.delete()

    assert serialize_rules(routed_page.canonical) == []
    assert RoutingMixin._has_live_routing_rules(routed_page.canonical) is False


def test_serialize_rules_keeps_the_alias_locale_the_visitor_asked_for(fallback_locale_wnp):
    # es-AR has no pages of its own, so the es-MX page is served at the es-AR URL. A target
    # URL carrying /es-MX/ would move the visitor out of the locale they asked for, on the
    # one navigation the resolver exists to perform.
    request = rf.get(fallback_locale_wnp.alias_url + "?utm_source=update")
    with translation.override("es-AR"):
        rules = serialize_rules(fallback_locale_wnp.canonical, request)

    assert rules[0]["target"].startswith("/es-AR/")
    assert "/es-MX/" not in rules[0]["target"]


def test_serialize_rules_still_emits_a_url_for_a_plain_page_target():
    # Only springfield CMS pages carry the alias-aware URL helper, and the ORM/API path can
    # attach any page as a target. Such a rule must still serve — a triggered visitor
    # getting a 500 would be worse than a URL with the un-rewritten locale prefix.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="plain-target-canonical", parent=site_root)
    plain = Page(title="Plain target", slug="plain-target", live=True)
    canonical.add_child(instance=plain)
    RoutingRule.objects.create(page=canonical, target=plain, match_all=True)

    rules = serialize_rules(canonical)
    assert rules[0]["target"].endswith("/plain-target/")


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


# ---------------------------------------------------------------------------
# Translated pages: rules are copied by Wagtail but their target FK is not remapped.
# ---------------------------------------------------------------------------


@pytest.fixture
def translated_tree(routed_page):
    """The routed page copied into a German locale, as copy_for_translation leaves it."""
    german = Locale.objects.get_or_create(language_code="de")[0]
    canonical_de = routed_page.canonical.copy_for_translation(german, copy_parents=True)
    canonical_de.save()
    canonical_de.refresh_from_db()
    target_de = routed_page.target.copy_for_translation(german)
    target_de.live = True
    target_de.save()
    return SimpleNamespace(canonical=canonical_de, target=target_de, source=routed_page)


def test_translation_copies_rules_still_pointing_at_the_source_locale(translated_tree):
    # Pins the Wagtail behaviour the fix exists for: the rule comes across, but its
    # stored target is still the English variant. If Wagtail ever remaps this itself,
    # this test fails and localized_target can be reconsidered.
    rule = translated_tree.canonical.routing_rules.get()
    assert rule.target_id == translated_tree.source.target.pk
    assert not rule.target.is_descendant_of(translated_tree.canonical)


def test_serialize_routes_a_translated_page_to_its_own_locale_target(translated_tree):
    # The German page must route to the German variant, never the English one.
    serialized = serialize_rules(translated_tree.canonical)
    assert len(serialized) == 1
    assert serialized[0]["target"] == translated_tree.target.get_url()
    assert serialized[0]["target"] != translated_tree.source.target.get_url()


def test_serialize_drops_a_rule_whose_target_is_not_translated(translated_tree):
    # Fail safe the way the rest of the framework does: with no German variant, the
    # visitor stays on the German canonical rather than being sent to English content.
    translated_tree.target.delete()
    assert serialize_rules(translated_tree.canonical) == []


def test_serialize_drops_a_rule_whose_translated_target_is_unpublished(translated_tree):
    # Same outcome by a different route — the existing live check catches this one.
    translated_tree.target.live = False
    translated_tree.target.save()
    assert serialize_rules(translated_tree.canonical) == []


def test_serialize_is_unaffected_for_an_untranslated_page(routed_page):
    serialized = serialize_rules(routed_page.canonical)
    assert serialized[0]["target"] == routed_page.target.get_url()
