# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing models and their save-time validation.

All framework state keys to ``wagtailcore.Page``, so these tests attach rules and
config to existing concrete pages — no dedicated test-harness page type
is introduced.
"""

from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError

import pytest
from wagtail.admin.widgets import AdminPageChooser
from wagtail.models import Site

from springfield.cms.models import WhatsNewPage2026
from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule, rule_panels, signal_choices
from springfield.cms.tests.factories import (
    SimpleRichTextPageFactory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)

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
# Generic Page keying: rules attach to any concrete page.
# ---------------------------------------------------------------------------


def test_rules_attach_to_a_concrete_page_via_the_generic_relation(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    # The reverse accessor works from the concrete subclass instance, proving the
    # single generic table is shared without a per-consumer model.
    assert list(tree.canonical.routing_rules.all()) == [rule]


# ---------------------------------------------------------------------------
# match_all + name fields.
# ---------------------------------------------------------------------------


def test_match_all_defaults_to_false(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    assert rule.match_all is False


def test_name_defaults_to_blank(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    assert rule.name == ""


def test_match_all_and_name_persist(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, match_all=True, name="Route everyone")
    rule.refresh_from_db()
    assert rule.match_all is True
    assert rule.name == "Route everyone"


# ---------------------------------------------------------------------------
# __str__: name when set, else a conditions → target summary.
# ---------------------------------------------------------------------------


def test_str_uses_name_when_set(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, name="My rule")
    assert str(rule) == "My rule"


def test_str_falls_back_to_match_all_summary(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, match_all=True)
    result = str(rule)
    assert "all triggered visitors" in result
    assert f"target {tree.descendant.id}" in result


def test_str_falls_back_to_conditions_summary(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows")
    result = str(rule)
    assert "platform is windows" in result
    assert f"target {tree.descendant.id}" in result


def test_str_falls_back_to_no_conditions_summary(tree):
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    result = str(rule)
    assert "no conditions" in result
    assert f"target {tree.descendant.id}" in result


# ---------------------------------------------------------------------------
# Target FK protection: deleting a targeted page is blocked.
# ---------------------------------------------------------------------------


def test_deleting_a_targeted_page_raises_protected_error(tree):
    RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)
    with pytest.raises(ProtectedError):
        tree.descendant.delete()


# ---------------------------------------------------------------------------
# Target descendant constraint — enforced server-side in clean().
# ---------------------------------------------------------------------------


def test_descendant_target_is_valid(tree):
    # match_all satisfies the condition floor so this isolates the target check.
    rule = RoutingRule(page=tree.canonical, target=tree.descendant, match_all=True)
    rule.full_clean()  # does not raise


def test_non_descendant_target_raises(tree):
    rule = RoutingRule(page=tree.canonical, target=tree.outsider, match_all=True)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "target" in exc.value.error_dict


def test_canonical_itself_is_not_a_valid_target(tree):
    # A rule must route to a strict descendant, never to the canonical itself.
    rule = RoutingRule(page=tree.canonical, target=tree.canonical, match_all=True)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "target" in exc.value.error_dict


def test_self_target_is_rejected(tree):
    # Self-targeting gets its own explicit message, distinct from the generic
    # descendant error.
    rule = RoutingRule(page=tree.canonical, target=tree.canonical, match_all=True)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "own page" in str(exc.value.error_dict["target"])


# ---------------------------------------------------------------------------
# Condition floor. Enforced on the page form (RoutingPageForm), not the
# model: modelcluster attaches nested conditions only at save time, so a model-level
# count check can't see them during a Wagtail save. The floor's authoring behaviour is
# covered in test_authoring.py; here we only assert the model doesn't over-reject.
# ---------------------------------------------------------------------------


def test_match_all_rule_without_conditions_passes_model_clean(tree):
    # A match-all rule legitimately has no conditions; model clean() must allow it.
    rule = RoutingRule(page=tree.canonical, target=tree.descendant, match_all=True)
    rule.full_clean()  # does not raise


def test_conditionless_rule_is_not_rejected_by_model_clean(tree):
    # The empty-rule floor is not a model concern (it lives on the page form), so
    # model clean() alone does not raise on a conditionless, non-match-all rule.
    rule = RoutingRule(page=tree.canonical, target=tree.descendant)
    rule.full_clean()  # does not raise


# ---------------------------------------------------------------------------
# Canonical-host guard: rules only fire on the canonical page.
# ---------------------------------------------------------------------------


@pytest.fixture
def wnp_tree():
    """A WhatsNewPage2026 tree where the variant is a non-canonical host.

    index
    └── canonical  (direct child of the index → is_routing_canonical True)
        └── variant     (nested → is_routing_canonical False)
            └── grandchild  (a valid descendant target of the variant)
    """
    site = Site.objects.get(is_default_site=True)
    index = WhatsNewIndexPageFactory(parent=site.root_page, slug="c16-whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="c16-200", version="200", live=True)
    variant = WhatsNewPage2026Factory(parent=canonical, slug="c16-200-b", version="200", live=True)
    grandchild = WhatsNewPage2026Factory(parent=variant, slug="c16-200-c", version="200", live=True)
    return SimpleNamespace(index=index, canonical=canonical, variant=variant, grandchild=grandchild)


def test_rule_on_canonical_page_is_valid(wnp_tree):
    rule = RoutingRule(page=wnp_tree.canonical, target=wnp_tree.variant, match_all=True)
    rule.full_clean()  # does not raise


def test_rule_on_non_canonical_page_is_rejected(wnp_tree):
    # A valid descendant target + match_all isolates the canonical-host error.
    rule = RoutingRule(page=wnp_tree.variant, target=wnp_tree.grandchild, match_all=True)
    with pytest.raises(ValidationError) as exc:
        rule.full_clean()
    assert "page" in exc.value.error_dict


# ---------------------------------------------------------------------------
# Condition validation.
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
    # `in` is a set-membership operator, not legal against a version signal.
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
# Priority / determinism: position then id, older rule wins ties.
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
# Lifecycle: no independent rule status.
# ---------------------------------------------------------------------------


def test_rule_has_no_independent_status_field():
    field_names = {f.name for f in RoutingRule._meta.get_fields()}
    for forbidden in ("status", "is_active", "active", "draft", "live", "published", "enabled"):
        assert forbidden not in field_names


# ---------------------------------------------------------------------------
# Kill switch: missing RoutingConfig reads as not paused.
# ---------------------------------------------------------------------------


def test_missing_config_reads_as_not_paused(tree):
    assert RoutingConfig.is_paused_for(tree.canonical) is False


def test_config_reports_paused_state(tree):
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=True)
    assert RoutingConfig.is_paused_for(tree.canonical) is True


def test_config_present_but_not_paused_reads_as_not_paused(tree):
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=False)
    assert RoutingConfig.is_paused_for(tree.canonical) is False


# ---------------------------------------------------------------------------
# Signal choices grouped by source and target-chooser scoping.
# ---------------------------------------------------------------------------


def test_signal_choices_are_grouped_by_source():
    # Django grouped-choices shape: [(source_label, [(name, name), ...]), ...].
    groups = {str(label): [value for value, _label in options] for label, options in signal_choices()}
    assert "platform" in groups["User-Agent"]
    assert "country" in groups["CDN geo header"]
    assert {"oldversion", "locale", "utm_source"} <= set(groups["URL"])


def _target_panel(panels):
    return next(panel for panel in panels if getattr(panel, "field_name", "") == "target")


def test_rule_panels_target_chooser_is_unrestricted_by_default():
    # No page-type scope -> a plain page chooser (no explicit AdminPageChooser widget).
    assert not isinstance(_target_panel(rule_panels()).widget, AdminPageChooser)


def test_rule_panels_scope_the_target_chooser_to_given_page_types():
    target_panel = _target_panel(rule_panels(["cms.WhatsNewPage2026"]))
    assert isinstance(target_panel.widget, AdminPageChooser)
    assert WhatsNewPage2026 in target_panel.widget.target_models


def test_conditions_panel_heading_states_the_and_semantics():
    # Editors should see the conjunction on the panel itself, not only in the tab help.
    conditions_panel = next(panel for panel in rule_panels() if getattr(panel, "relation_name", "") == "conditions")
    assert "AND" in str(conditions_panel.heading)
