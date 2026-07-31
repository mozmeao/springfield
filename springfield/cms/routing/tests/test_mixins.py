# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing adoption mixin.

Method-level tests only: no test-harness page type is introduced, so the
full serve/edit-view integration lands with the first real consumer. Here we
prove the adoption-surface defaults, the tab's panel structure, and the per-instance
tab-visibility decision.
"""

from types import SimpleNamespace

from django.test import RequestFactory

import pytest
from wagtail.admin.panels import HelpPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Site

from springfield.cms.routing.arming import QueryParamArmingCondition
from springfield.cms.routing.mixins import RoutingMixin, RoutingObjectList, routing_tab_is_shown
from springfield.cms.routing.models import RoutingRule
from springfield.cms.routing.signals import registry
from springfield.cms.tests.factories import SimpleRichTextPageFactory

rf = RequestFactory()

# ---------------------------------------------------------------------------
# Adoption surface: the three hooks and their defaults.
# ---------------------------------------------------------------------------


def test_is_routing_canonical_defaults_to_false():
    # Fail-closed: a half-adopted consumer never routes.
    assert RoutingMixin.is_routing_canonical(SimpleNamespace()) is False


def test_routing_trigger_is_unset_by_default():
    assert RoutingMixin.get_routing_trigger(SimpleNamespace()) is None


def test_signal_subset_defaults_to_full_registry():
    assert RoutingMixin.get_routing_signal_names(SimpleNamespace()) == tuple(registry.names())


# ---------------------------------------------------------------------------
# The mixin adds no database fields, so adoption produces no migration.
# ---------------------------------------------------------------------------


def test_mixin_declares_no_database_fields():
    assert list(RoutingMixin._meta.local_fields) == []
    assert RoutingMixin._meta.abstract is True


# ---------------------------------------------------------------------------
# The "User Routing" tab wires both panels via Wagtail's inline-panel pattern.
# ---------------------------------------------------------------------------


def _inline_panels(panel):
    """Every InlinePanel in a panel tree (the kill switch is nested under a group)."""
    found = []
    for child in getattr(panel, "children", []):
        if isinstance(child, InlinePanel):
            found.append(child)
        found.extend(_inline_panels(child))
    return found


def test_routing_tab_holds_rules_and_kill_switch_panels():
    tab = RoutingMixin.get_routing_tab()
    assert isinstance(tab, RoutingObjectList)
    assert str(tab.heading) == "User Routing"

    # A generic guidance panel leads the tab.
    assert any(isinstance(child, HelpPanel) for child in tab.children)

    # Page-level settings sit under an "Options" group so more can nest there later.
    groups = [child for child in tab.children if isinstance(child, MultiFieldPanel)]
    assert any(str(group.heading) == "Options" for group in groups)

    panels = {panel.relation_name: panel for panel in _inline_panels(tab)}
    assert set(panels) == {"routing_rules", "routing_config"}

    # The kill switch is a single-item panel over RoutingConfig (0-or-1 per page). The
    # checkbox always renders with no "Add" step via RoutingPageForm auto-creating
    # the record, not via min_num — so no min_num here (it can't be met by an empty form).
    assert panels["routing_config"].max_num == 1
    assert panels["routing_config"].min_num is None
    assert str(panels["routing_config"].label) == "Kill switch"


# ---------------------------------------------------------------------------
# Tab visibility keys off eligibility: shown only on canonical instances.
# ---------------------------------------------------------------------------


def test_tab_shown_on_canonical_instance():
    canonical = SimpleNamespace(is_routing_canonical=lambda: True)
    assert routing_tab_is_shown(canonical) is True


def test_tab_suppressed_on_non_canonical_instance():
    non_canonical = SimpleNamespace(is_routing_canonical=lambda: False)
    assert routing_tab_is_shown(non_canonical) is False


def test_tab_suppressed_when_predicate_absent_or_none():
    assert routing_tab_is_shown(None) is False
    assert routing_tab_is_shown(SimpleNamespace()) is False


def test_bound_panel_is_shown_delegates_to_eligibility():
    # The RoutingObjectList tab's BoundPanel gates rendering on the instance predicate.
    bound = RoutingObjectList.BoundPanel.__new__(RoutingObjectList.BoundPanel)
    bound.instance = SimpleNamespace(is_routing_canonical=lambda: True)
    assert bound.is_shown() is True
    bound.instance = SimpleNamespace(is_routing_canonical=lambda: False)
    assert bound.is_shown() is False


# ---------------------------------------------------------------------------
# Serve-path flag sources: the thin adapter maps these onto decide_routing.
# Full request-level serve integration lands with the first consumer.
# ---------------------------------------------------------------------------


def test_routing_trigger_satisfied_maps_the_trigger_hook():
    armed = SimpleNamespace(get_routing_trigger=lambda: QueryParamArmingCondition("routing"))
    assert RoutingMixin._routing_trigger_satisfied(armed, rf.get("/?routing=1")) is True
    assert RoutingMixin._routing_trigger_satisfied(armed, rf.get("/")) is False
    # An unset trigger (the default) is never satisfied.
    unset = SimpleNamespace(get_routing_trigger=lambda: None)
    assert RoutingMixin._routing_trigger_satisfied(unset, rf.get("/?routing=1")) is False


@pytest.mark.django_db
def test_has_live_routing_rules_counts_only_live_targets():
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="c10-canonical", parent=site_root)
    live_target = SimpleRichTextPageFactory(slug="c10-live", parent=canonical, live=True)
    # No rules yet.
    assert RoutingMixin._has_live_routing_rules(canonical) is False
    RoutingRule.objects.create(page=canonical, target=live_target)
    assert RoutingMixin._has_live_routing_rules(canonical) is True

    # A rule pointing only at an unpublished target does not count.
    other = SimpleRichTextPageFactory(slug="c10-other", parent=site_root)
    dead_target = SimpleRichTextPageFactory(slug="c10-dead", parent=other, live=False)
    RoutingRule.objects.create(page=other, target=dead_target)
    assert RoutingMixin._has_live_routing_rules(other) is False
