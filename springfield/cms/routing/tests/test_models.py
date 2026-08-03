# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing models and their save-time validation.

All framework state keys to ``wagtailcore.Page``, so these tests attach rules and
config to existing concrete pages — no dedicated test-harness page type
is introduced.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

import pytest
from wagtail.admin.widgets import AdminPageChooser
from wagtail.models import Site

from springfield.cms.models import WhatsNewPage2026
from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule, rule_panels, signal_choices
from springfield.cms.routing.value_lists import CLOSED_SET_SIGNALS
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
    root = SimpleRichTextPageFactory(slug="rules-root")
    canonical = SimpleRichTextPageFactory(slug="rules-canonical", parent=root)
    descendant = SimpleRichTextPageFactory(slug="rules-variant", parent=canonical)
    outsider = SimpleRichTextPageFactory(slug="rules-outsider", parent=root)
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
# Deleting a target clears it from its rules. This deliberately reverses the
# earlier PROTECT behaviour: blocking the delete made any *ancestor* of a
# rule-bearing page undeletable through the admin, and never protected the case
# that actually hurts (unpublishing has the same cached-resolver window).
# ---------------------------------------------------------------------------


def test_deleting_a_targeted_page_clears_the_target_and_keeps_the_rule(tree):
    # Kept as the record that this behaviour was changed on purpose: it used to raise
    # ProtectedError.
    rule = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)

    tree.descendant.delete()

    rule.refresh_from_db()
    assert rule.target_id is None
    assert RoutingRule.objects.filter(pk=rule.pk).exists()


def test_deleting_the_page_that_hosts_a_rule_succeeds(tree):
    # The reported bug: the rule is cascade-deleted with its own page, but PROTECT saw the
    # target reference and refused, so the admin 500'd.
    RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)

    tree.canonical.delete()

    assert not RoutingRule.objects.filter(page_id=tree.canonical.pk).exists()


def test_deleting_an_ancestor_of_a_rule_bearing_page_succeeds(tree):
    # The case a friendlier error message would not have fixed: the whole subtree goes,
    # including both the rule and its target.
    RoutingRule.objects.create(page=tree.canonical, target=tree.descendant)

    tree.root.delete()

    assert not RoutingRule.objects.exists()


def test_deleting_one_target_leaves_other_rules_alone(tree):
    # Blast radius is per-target, not per-page: a sibling rule pointing at a live variant
    # keeps working.
    survivor_target = SimpleRichTextPageFactory(slug="surviving-variant", parent=tree.canonical, live=True)
    doomed = RoutingRule.objects.create(page=tree.canonical, target=tree.descendant, sort_order=0)
    survivor = RoutingRule.objects.create(page=tree.canonical, target=survivor_target, sort_order=1)

    tree.descendant.delete()

    doomed.refresh_from_db()
    survivor.refresh_from_db()
    assert doomed.target_id is None
    assert survivor.target_id == survivor_target.pk


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
    index = WhatsNewIndexPageFactory(parent=site.root_page, slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="wnp-200", version="200", live=True)
    variant = WhatsNewPage2026Factory(parent=canonical, slug="wnp-200-variant", version="200", live=True)
    grandchild = WhatsNewPage2026Factory(parent=variant, slug="wnp-200-nested", version="200", live=True)
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


def test_off_list_country_raises(rule):
    # country is a STRING signal, but its value set is the complete ISO region list, so an
    # off-list value can never match and would leave the rule silently dead. Enforced like
    # an enum rather than left to the client.
    condition = RoutingCondition(rule=rule, signal="country", operator="is", expected_value="bleh")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_off_list_locale_raises(rule):
    condition = RoutingCondition(rule=rule, signal="locale", operator="is", expected_value="zz")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_served_locale_without_cms_content_is_accepted(rule):
    # The set is every locale the site serves, not the smaller CMS-content set — targeting
    # a locale that has no CMS translations is legitimate and must not be rejected.
    served = {code for code, _label in settings.LANGUAGES}
    cms_content = {code for code, _label in settings.WAGTAIL_CONTENT_LANGUAGES}
    outside_cms = sorted(served - cms_content)[0]

    condition = RoutingCondition(rule=rule, signal="locale", operator="is", expected_value=outside_cms)
    condition.full_clean()  # must not raise


def test_browser_language_accepts_an_unserved_language(rule):
    # Targeting a Norwegian who was served English is the point of the signal, so the
    # server must accept a language we publish nothing in.
    RoutingCondition(rule=rule, signal="browser_language", operator="is", expected_value="no").full_clean()
    RoutingCondition(rule=rule, signal="browser_language", operator="is", expected_value="dz").full_clean()


def test_browser_language_rejects_a_non_language(rule):
    condition = RoutingCondition(rule=rule, signal="browser_language", operator="is", expected_value="xx")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_browser_language_rejects_a_regional_tag(rule):
    # The reader strips the region, so a regional tag could never match — fail loudly at
    # authoring time rather than saving a rule that silently never fires.
    condition = RoutingCondition(rule=rule, signal="browser_language", operator="is", expected_value="en-au")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_off_list_language_raises(rule):
    # `language` had no coverage on any side until now, and its set is *derived* from the
    # served locales rather than written out — so a break in that derivation lands here.
    condition = RoutingCondition(rule=rule, signal="language", operator="is", expected_value="zz")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


def test_language_accepts_a_region_free_served_language(rule):
    RoutingCondition(rule=rule, signal="language", operator="is", expected_value="de").full_clean()
    RoutingCondition(rule=rule, signal="language", operator="in", expected_value="de, fr\nes").full_clean()


def test_language_rejects_a_regional_locale(rule):
    # The signal drops the region on purpose — `en` covers en-US, en-GB and en-CA — so a
    # regional tag could never match.
    condition = RoutingCondition(rule=rule, signal="language", operator="is", expected_value="en-US")
    with pytest.raises(ValidationError) as exc:
        condition.full_clean()
    assert "expected_value" in exc.value.error_dict


@pytest.mark.parametrize("signal", sorted(CLOSED_SET_SIGNALS))
def test_an_empty_value_list_blocks_the_save_instead_of_accepting_anything(rule, signal):
    # Every one of these sets is computed from settings or product data, so a rename or a
    # data problem upstream can empty one. Read as "unconstrained", that would switch
    # validation off in silence and let through values that can never match at runtime.
    with patch("springfield.cms.routing.models.known_value_lists", return_value={}):
        condition = RoutingCondition(rule=rule, signal=signal, operator="is", expected_value="anything at all")
        with pytest.raises(ValidationError) as exc:
            condition.full_clean()
    assert "expected_value" in exc.value.error_dict
    # The message must name the real cause: no value the author can type will fix it.
    assert "unavailable" in str(exc.value)


def test_a_signal_with_no_value_list_by_design_stays_unconstrained(rule):
    # The counterpart guard: utm_* signals are free text, and an empty list is correct there.
    RoutingCondition(rule=rule, signal="utm_campaign", operator="is", expected_value="anything at all").full_clean()


def test_valid_country_and_membership_list_pass(rule):
    RoutingCondition(rule=rule, signal="country", operator="is", expected_value="DE").full_clean()
    RoutingCondition(rule=rule, signal="country", operator="in", expected_value="DE, GB\nUS").full_clean()


def test_expected_values_splits_on_newlines_and_commas(rule):
    # A set-membership list may be entered one-per-line, comma-separated, or a mix.
    condition = RoutingCondition(rule=rule, signal="platform", operator="in", expected_value="windows\nosx, linux\n")
    assert condition.expected_values() == ["windows", "osx", "linux"]


def test_single_value_operator_reads_the_whole_trimmed_string(rule):
    # Non-membership operators are not split — the value is the whole (trimmed) string.
    condition = RoutingCondition(rule=rule, signal="platform", operator="is", expected_value="  windows  ")
    assert condition.expected_values() == ["windows"]


def test_expected_value_is_an_uncapped_textfield():
    # Long in/not_in lists need a roomy multi-line textarea, so the field is an uncapped
    # TextField rather than a length-limited CharField.
    field = RoutingCondition._meta.get_field("expected_value")
    assert field.get_internal_type() == "TextField"
    assert field.max_length is None


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


def test_a_second_config_for_one_page_is_rejected(tree):
    # The admin panel's max_num=1 is presentation only: two editors opening the same page
    # before either saves would otherwise produce two rows.
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=False)
    with pytest.raises(IntegrityError):
        RoutingConfig.objects.create(page=tree.canonical, routing_paused=True)


def test_any_paused_config_counts_as_paused(tree):
    # Defence for a database that predates the constraint and already holds a duplicate: the
    # unpaused row must not be able to shadow the paused one by being read first. Asserted on
    # the page's own children, since the constraint now stops two such rows being *created*.
    page = tree.canonical
    page.routing_config = [
        RoutingConfig(page=page, routing_paused=False),
        RoutingConfig(page=page, routing_paused=True),
    ]
    assert RoutingConfig.is_paused_for(page) is True


def test_a_page_built_from_a_revision_reports_its_staged_pause(tree):
    # A Wagtail preview builds the page with get_latest_revision_as_object(), so the staged
    # config lives on *that* object. Reading the live table instead would report the live
    # pause state while every other field on the page previews as staged.
    RoutingConfig.objects.create(page=tree.canonical, routing_paused=False)
    page = tree.canonical
    config = page.routing_config.first()
    config.routing_paused = True
    # Assignment, not mutation: modelcluster's manager hands back fresh instances, so
    # editing one in place never reaches the cluster that gets serialized into the revision.
    page.routing_config = [config]
    page.save_revision()

    staged = page.get_latest_revision_as_object()
    assert RoutingConfig.is_paused_for(staged) is True
    # The live page is untouched: a draft save stages the pause, it does not apply it.
    assert RoutingConfig.is_paused_for(type(page).objects.get(pk=page.pk)) is False


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
