# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing models and their save-time validation (C3).

All framework state keys to ``wagtailcore.Page``, so these tests attach rules and
config to existing concrete pages (spec §0.3) — no dedicated test-harness page type
is introduced.
"""

from types import SimpleNamespace

from django.core.exceptions import ValidationError

import pytest

from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def tree():
    """A small page tree:

    root
    ├── canonical      (hosts rules)
    │   └── descendant (a valid target — descendant of canonical)
    └── outsider       (an invalid target — not under canonical)
    """
    root = SimpleRichTextPageFactory(slug="c3-root")
    canonical = SimpleRichTextPageFactory(slug="c3-canonical", parent=root)
    descendant = SimpleRichTextPageFactory(slug="c3-variant", parent=canonical)
    outsider = SimpleRichTextPageFactory(slug="c3-outsider", parent=root)
    return SimpleNamespace(root=root, canonical=canonical, descendant=descendant, outsider=outsider)


# ---------------------------------------------------------------------------
# Generic Page keying (plan §0.5, §3): rules attach to any concrete page.
# ---------------------------------------------------------------------------


def test_rules_attach_to_a_concrete_page_via_the_generic_relation(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    # The reverse accessor works from the concrete subclass instance, proving the
    # single generic table is shared without a per-consumer model.
    assert list(tree.canonical.routing_rules.all()) == [rule]


# ---------------------------------------------------------------------------
# Target descendant constraint (spec §5.1, §6.3) — enforced server-side in clean().
# ---------------------------------------------------------------------------


def test_descendant_target_is_valid(tree):
    rule = RoutingRule(page=tree.canonical, target=tree.descendant)
    rule.full_clean()  # does not raise


def test_non_descendant_target_raises(tree):
    rule = RoutingRule(page=tree.canonical, target=tree.outsider)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "target" in exc.value.error_dict


def test_canonical_itself_is_not_a_valid_target(tree):
    # A rule must route to a strict descendant, never to the canonical itself.
    rule = RoutingRule(page=tree.canonical, target=tree.canonical)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "target" in exc.value.error_dict


# ---------------------------------------------------------------------------
# Condition validation (spec §6.3).
# ---------------------------------------------------------------------------


@pytest.fixture
def rule(tree):
    return RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)


def test_valid_condition_passes(rule):
    condition = RoutingCondition(rule=rule, signal="platform", operator="is", expected_value="windows")
    condition.full_clean()  # does not raise


def test_valid_enum_set_membership_condition_passes(rule):
    condition = RoutingCondition(rule=rule, signal="platform", operator="in", expected_value="windows, osx")
    condition.full_clean()  # does not raise


def test_unknown_signal_raises(rule):
    condition = RoutingCondition(rule=rule, signal="not_a_signal", operator="is", expected_value="x")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "signal" in exc.value.error_dict


def test_illegal_operator_for_value_type_raises(rule):
    # `in` is a set-membership operator, not legal against a version signal (§4.3).
    condition = RoutingCondition(rule=rule, signal="firefox_version", operator="in", expected_value="129")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "operator" in exc.value.error_dict


def test_non_member_enum_value_raises(rule):
    condition = RoutingCondition(rule=rule, signal="platform", operator="is", expected_value="beos")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_non_member_in_enum_set_raises(rule):
    condition = RoutingCondition(rule=rule, signal="platform", operator="in", expected_value="windows, beos")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


# ---------------------------------------------------------------------------
# Priority / determinism (spec §5.3): position then id, older rule wins ties.
# ---------------------------------------------------------------------------


def test_ordering_is_position_then_id(tree):
    # Two rules sharing a position must order deterministically by ascending id.
    first = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, sort_order=0)
    second = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, sort_order=0)
    third = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, sort_order=-1)

    ordered = list(RoutingRule.objects.filter(page=tree.canonical))
    # sort_order -1 comes first; the tied 0-position rules break by ascending id.
    assert ordered == [third, first, second]
    # Reverse accessor honors the same ordering.
    assert list(tree.canonical.routing_rules.all()) == [third, first, second]


# ---------------------------------------------------------------------------
# Lifecycle (spec §5.4): no independent rule status.
# ---------------------------------------------------------------------------


def test_rule_has_no_independent_status_field():
    field_names = {f.name for f in RoutingRule._meta.get_fields()}
    for forbidden in ("status", "is_active", "active", "draft", "live", "published", "enabled"):
        assert forbidden not in field_names


# ---------------------------------------------------------------------------
# Kill switch (spec §5.4): missing RoutingConfig reads as not paused.
# ---------------------------------------------------------------------------


def test_missing_config_reads_as_not_paused(tree):
    assert RoutingConfig.is_paused_for(tree.canonical) is False


def test_config_reports_paused_state(tree):
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=True)
    assert RoutingConfig.is_paused_for(tree.canonical) is True


def test_config_present_but_not_paused_reads_as_not_paused(tree):
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=False)
    assert RoutingConfig.is_paused_for(tree.canonical) is False
