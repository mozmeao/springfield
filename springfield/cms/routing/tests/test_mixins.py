# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing adoption mixin.

Method-level tests only: no test-harness page type is introduced, so the
full serve integration lands with the first real consumer. Here we prove the
adoption-surface defaults and the serve-path flag adapter.
"""

from types import SimpleNamespace

from django.test import RequestFactory

import pytest
from wagtail.models import Site

from springfield.cms.routing.arming import QueryParamArmingCondition
from springfield.cms.routing.mixins import RoutingMixin
from springfield.cms.routing.models import RoutingRule
from springfield.cms.tests.factories import SimpleRichTextPageFactory

rf = RequestFactory()

# ---------------------------------------------------------------------------
# Adoption surface: the two hooks and their defaults.
# ---------------------------------------------------------------------------


def test_is_routing_canonical_defaults_to_false():
    # Fail-closed: a half-adopted consumer never routes.
    assert RoutingMixin.is_routing_canonical(SimpleNamespace()) is False


def test_routing_trigger_is_unset_by_default():
    assert RoutingMixin.get_routing_trigger(SimpleNamespace()) is None


# ---------------------------------------------------------------------------
# The mixin adds no database fields, so adoption produces no migration.
# ---------------------------------------------------------------------------


def test_mixin_declares_no_database_fields():
    assert list(RoutingMixin._meta.local_fields) == []
    assert RoutingMixin._meta.abstract is True


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
    canonical = SimpleRichTextPageFactory(slug="live-rules-canonical", parent=site_root)
    live_target = SimpleRichTextPageFactory(slug="live-target", parent=canonical, live=True)
    # No rules yet.
    assert RoutingMixin._has_live_routing_rules(canonical) is False
    # match_all so the rule can route someone; a rule that cannot route is a separate
    # question, covered below.
    RoutingRule.objects.create(page=canonical, target=live_target, match_all=True)
    assert RoutingMixin._has_live_routing_rules(canonical) is True

    # A rule pointing only at an unpublished target does not count.
    other = SimpleRichTextPageFactory(slug="other-canonical", parent=site_root)
    dead_target = SimpleRichTextPageFactory(slug="draft-target", parent=other, live=False)
    RoutingRule.objects.create(page=other, target=dead_target, match_all=True)
    assert RoutingMixin._has_live_routing_rules(other) is False


# ---------------------------------------------------------------------------
# "This page has routing" and "these are the rules the client gets" must be the
# same question. When they diverge, a page either serves a resolver with nothing
# in it (holding page, then a bounce straight back) or refuses to route on rules
# that would have worked.
# ---------------------------------------------------------------------------


def _assert_gate_agrees_with_the_serializer(page):
    from springfield.cms.routing.resolver import serialize_rules

    assert RoutingMixin._has_live_routing_rules(page) is bool(serialize_rules(page))


@pytest.mark.django_db
def test_a_conditionless_rule_neither_routes_nor_counts():
    # No conditions and match_all off: the serializer drops it, so the gate must not
    # count it. Built via the ORM because the page form blocks authoring one.
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="conditionless-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="conditionless-target", parent=canonical, live=True)
    RoutingRule.objects.create(page=canonical, target=target, match_all=False)

    _assert_gate_agrees_with_the_serializer(canonical)
    assert RoutingMixin._has_live_routing_rules(canonical) is False


@pytest.mark.django_db
def test_a_target_with_no_version_in_this_locale_neither_routes_nor_counts(translated_wnp):
    # The German page's rule points at a variant that exists only in English, so it can
    # never route a German visitor.
    translated_wnp.de_variant.delete()

    _assert_gate_agrees_with_the_serializer(translated_wnp.de_canonical)
    assert RoutingMixin._has_live_routing_rules(translated_wnp.de_canonical) is False


@pytest.mark.django_db
def test_routing_survives_the_source_locale_target_being_unpublished(translated_wnp):
    # Only the English variant is a draft; the German one is live. The German page's rule
    # resolves to the German variant, so it still routes.
    translated_wnp.variant.unpublish()

    _assert_gate_agrees_with_the_serializer(translated_wnp.de_canonical)
    assert RoutingMixin._has_live_routing_rules(translated_wnp.de_canonical) is True
