# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the browse-only User Routing rules listing."""

from django.urls import NoReverseMatch, reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms import wagtail_hooks
from springfield.cms.routing.models import RoutingCondition, RoutingRule
from springfield.cms.routing.signals import registry
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


def _rule_on(slug, title):
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug=slug, title=title, parent=site_root)
    target = SimpleRichTextPageFactory(slug=f"{slug}-t", title=f"{title} target", parent=canonical, live=True)
    return RoutingRule.objects.create(page=canonical, target=target)


def test_listing_renders_rules_from_multiple_pages(admin_client):
    _rule_on("canonical-alpha", "Canonical Alpha")
    _rule_on("canonical-beta", "Canonical Beta")

    response = admin_client.get(reverse("cms_routing_rules"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Canonical Alpha" in content
    assert "Canonical Beta" in content


def test_listing_handles_no_rules(admin_client):
    response = admin_client.get(reverse("cms_routing_rules"))
    assert response.status_code == 200
    assert "No routing rules" in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Status column: a rule the serve path drops looks perfectly healthy in a plain
# listing, so each way that happens has to be named here.
# ---------------------------------------------------------------------------


def _matchable(rule):
    """Give a rule a condition so the status column reports its target, not its emptiness."""
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)
    return rule


def _status_cell(content, rule_name):
    """The status text for the row carrying ``rule_name``."""
    row = next(tr for tr in BeautifulSoup(content, "html.parser").select("table.listing tbody tr") if rule_name in tr.get_text())
    return " ".join(row.select("td")[-1].get_text(" ", strip=True).split())


def test_listing_marks_a_healthy_rule_as_firing(admin_client):
    rule = _matchable(_rule_on("healthy-canonical", "Healthy"))
    rule.name = "Healthy rule"
    rule.save()

    content = admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8")
    assert "Will fire" in _status_cell(content, "Healthy rule")


def test_listing_flags_an_unpublished_target_as_waiting(admin_client):
    # Publishing the variant is work already in flight, so this must not read as an error.
    rule = _matchable(_rule_on("draft-target-canonical", "Draft target"))
    rule.name = "Awaiting publish"
    rule.save()
    rule.target.unpublish()

    status = _status_cell(admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8"), "Awaiting publish")
    assert "Waiting" in status
    assert "not published" in status
    assert "Won" not in status  # not the won't-fire treatment


def test_listing_flags_an_untranslated_target_as_waiting(admin_client, translated_wnp):
    # The ordinary state of a staged translation: the German page's rule points at a variant
    # that has not been translated yet.
    translated_wnp.de_variant.delete()
    rule = translated_wnp.de_canonical.routing_rules.first()
    rule.name = "Awaiting translation"
    rule.save()

    status = _status_cell(admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8"), "Awaiting translation")
    assert "Waiting" in status
    assert "not translated" in status


def test_listing_flags_a_target_outside_the_page_as_wont_fire(admin_client):
    # A page-copy artefact: nothing in the row itself reveals that the target belongs to a
    # different page's subtree. This one stays broken until an author fixes it.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="stray-host", title="Stray host", parent=site_root)
    unrelated = SimpleRichTextPageFactory(slug="unrelated-host", title="Unrelated", parent=site_root)
    stray = SimpleRichTextPageFactory(slug="stray-target", title="Stray target", parent=unrelated, live=True)
    rule = _matchable(RoutingRule.objects.create(page=canonical, target=stray, name="Cross subtree"))

    status = _status_cell(admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8"), "Cross subtree")
    assert "Won" in status  # won't fire
    assert "not part of this page" in status
    assert "Waiting" not in status
    assert rule.target_id == stray.pk


def test_listing_flags_a_rule_that_can_never_match_as_wont_fire(admin_client):
    rule = _rule_on("conditionless-host", "Conditionless host")
    rule.name = "No conditions"
    rule.save()

    status = _status_cell(admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8"), "No conditions")
    assert "Won" in status
    assert "No conditions" in status


def test_listing_shows_the_rule_name(admin_client):
    # Display: an author-given rule name appears in the browse listing.
    rule = _rule_on("canonical-named", "Canonical Named")
    rule.name = "Windows updaters"
    rule.save()

    content = admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8")
    assert "Rule" in content  # the new column header
    assert "Windows updaters" in content


# ---------------------------------------------------------------------------
# The listing is browse-only: no add affordance.
# ---------------------------------------------------------------------------


def test_no_add_route_is_registered():
    with pytest.raises(NoReverseMatch):
        reverse("cms_routing_rules_add")


def test_listing_has_no_add_form_or_button(admin_client):
    content = admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8").lower()
    # A read/browse aggregation: no create form, no "add rule" affordance.
    assert "<form" not in content
    assert "add rule" not in content


# ---------------------------------------------------------------------------
# The "User Routing" submenu is registered with the Rules item.
# ---------------------------------------------------------------------------


def test_user_routing_submenu_is_registered():
    submenu = wagtail_hooks.register_user_routing_menu()
    assert str(submenu.label) == "User Routing"
    assert submenu.menu is wagtail_hooks.user_routing_menu


def test_rules_item_is_in_the_submenu():
    labels = [str(item.label) for item in wagtail_hooks.user_routing_menu.registered_menu_items]
    assert "Rules" in labels


# ---------------------------------------------------------------------------
# Signals reference page — generated from the registry, never drifts.
# ---------------------------------------------------------------------------


def test_signals_reference_lists_every_registered_signal(admin_client):
    response = admin_client.get(reverse("cms_routing_signals"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    for name in registry.names():
        assert name in content


def test_signals_reference_shows_source_type_and_enum_values(admin_client):
    content = admin_client.get(reverse("cms_routing_signals")).content.decode("utf-8")
    assert "User-Agent" in content  # a source label
    assert "enum" in content  # a value type
    assert "windows" in content  # an enum value


def test_signals_reference_renders_source_badges(admin_client):
    # Each source gets a per-source badge class (drives the accent + dark-mode styling).
    content = admin_client.get(reverse("cms_routing_signals")).content.decode("utf-8")
    for source_key in ("cdn_geo", "user_agent", "uitour", "url"):
        assert f"routing-badge--{source_key}" in content


def test_signals_reference_shows_the_uitour_delay_note(admin_client):
    # The ~500 ms UITour note is real authoring guidance and must be present.
    content = admin_client.get(reverse("cms_routing_signals")).content.decode("utf-8")
    assert "UITour" in content
    assert "500" in content


def test_signals_reference_shows_type_aware_value_hints(admin_client):
    # Booleans read "true or false" (not "Free text"); version shows examples; the
    # long country list is available behind a collapsible disclosure.
    content = admin_client.get(reverse("cms_routing_signals")).content.decode("utf-8")
    assert "true or false" in content  # boolean signals
    assert "130.0.1" in content  # version example
    assert "<details" in content  # collapsible locale/country value list
    assert ">US<" in content or "US" in content  # a country code inside the disclosure


def test_adding_a_signal_makes_it_appear_with_no_page_edit(admin_client, temp_signal):
    content = admin_client.get(reverse("cms_routing_signals")).content.decode("utf-8")
    assert temp_signal.name in content


def test_signals_reference_item_is_in_the_submenu():
    labels = [str(item.label) for item in wagtail_hooks.user_routing_menu.registered_menu_items]
    assert "Signals reference" in labels
