# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

import pytest
from wagtail.models import Page

from springfield.cms.models import RoutingCondition, RoutingRule
from springfield.cms.models.routing import RULE_STATUS_DRAFT
from springfield.cms.tests.factories import (
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)


@pytest.fixture
def _wnp_tree(db):
    """Build a small WNP tree: index → canonical → variant.

    Variant is a child of canonical (matching the production URL structure
    ``/whatsnew/156/lapsed/``) so descendant validation on RoutingRule
    ``target_page`` passes.
    """
    root = Page.objects.get(depth=1)
    home = root.get_children().first() or root.add_child(instance=Page(title="Home", slug="home"))
    index = WhatsNewIndexPageFactory(parent=home, title="WNP Index", slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, title="WNP 156", slug="156", version="156")
    variant = WhatsNewPage2026Factory(parent=canonical, title="WNP 156 lapsed", slug="lapsed", version="156")
    return {"index": index, "canonical": canonical, "variant": variant}


def _stringify_values_for_condition(spec):
    """Helper — turn a condition spec (``{signal, equals}`` legacy or
    ``{signal, op, values}`` new) into the raw storage tuple
    (signal_name, operator, expected_values_str)."""
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
    return signal_name, operator, expected_values


def _make_rule(_wnp_tree, *, condition=None, conditions=None, save=False, **overrides):
    """Create a RoutingRule (unsaved by default) with 0+ conditions.

    ``condition=`` — legacy single-condition convenience (dict, either
    ``{signal, equals}`` or ``{signal, op, values}``).
    ``conditions=`` — list of new-shape dicts for AND rules.
    ``save=True`` — saves the rule AND persists its conditions.

    Rules constructed without ``save=True`` return unsaved; conditions can
    only be added after save (they use ParentalKey and need a rule PK).
    """
    defaults = {
        "name": "lapsed users",
        "sort_order": 100,
        "parent_page": _wnp_tree["canonical"],
        "target_page": _wnp_tree["variant"],
        "status": RULE_STATUS_DRAFT,
    }
    defaults.update(overrides)
    rule = RoutingRule(**defaults)

    # Default: one condition on lapsed_user=True unless caller passes empty.
    if condition is None and conditions is None:
        condition = {"signal": "lapsed_user", "equals": True}

    specs = []
    if condition is not None and condition != {}:
        specs.append(condition)
    if conditions is not None:
        specs.extend(conditions)

    if save or specs:
        rule.save()
        for spec in specs:
            signal_name, operator, expected_values = _stringify_values_for_condition(spec)
            RoutingCondition.objects.create(
                rule=rule,
                signal_name=signal_name,
                operator=operator,
                expected_values=expected_values,
            )
    return rule


# ---------------------------------------------------------------------------
# RoutingCondition.as_dict — engine-facing shape
# ---------------------------------------------------------------------------


class TestConditionAsDict:
    """``RoutingCondition.as_dict()`` returns the rule engine's shape
    ``{"signal", "op", "values"}`` (or ``{}`` for the draft-not-filled state)."""

    def test_new_shape_multivalue(self):
        c = RoutingCondition(signal_name="country", operator="is", expected_values="US\nCA")
        assert c.as_dict() == {"signal": "country", "op": "is", "values": ["US", "CA"]}

    def test_is_not_operator(self):
        c = RoutingCondition(signal_name="country", operator="is_not", expected_values="US")
        assert c.as_dict() == {"signal": "country", "op": "is_not", "values": ["US"]}

    def test_bool_signal(self):
        c = RoutingCondition(signal_name="lapsed_user", operator="is", expected_values="true")
        assert c.as_dict() == {"signal": "lapsed_user", "op": "is", "values": [True]}

    def test_int_signal(self):
        c = RoutingCondition(signal_name="firefox_version", operator="is", expected_values="151")
        assert c.as_dict() == {"signal": "firefox_version", "op": "is", "values": [151]}

    def test_multivalue_from_newlines(self):
        c = RoutingCondition(signal_name="country", operator="is", expected_values="US\nCA\nGB")
        assert c.as_dict()["values"] == ["US", "CA", "GB"]

    def test_multivalue_from_commas(self):
        c = RoutingCondition(signal_name="country", operator="is", expected_values="US, CA, GB")
        assert c.as_dict()["values"] == ["US", "CA", "GB"]

    def test_empty_when_no_signal(self):
        c = RoutingCondition(signal_name="", expected_values="")
        assert c.as_dict() == {}


class TestValueParsing:
    def test_bool_accepts_true_yes_1(self):
        for text in ("true", "True", "yes", "1"):
            c = RoutingCondition(signal_name="lapsed_user", expected_values=text)
            assert c.as_dict()["values"] == [True], text

    def test_bool_accepts_false_no_0(self):
        for text in ("false", "False", "no", "0"):
            c = RoutingCondition(signal_name="lapsed_user", expected_values=text)
            assert c.as_dict()["values"] == [False], text

    def test_bool_unparseable_dropped_from_values(self):
        c = RoutingCondition(signal_name="lapsed_user", expected_values="maybe")
        # Unparseable values are dropped from the getter's list — the rule
        # will then have zero values, which the evaluator treats as no-match.
        assert c.as_dict()["values"] == []

    def test_int_parses_number(self):
        c = RoutingCondition(signal_name="firefox_version", expected_values="151")
        assert c.as_dict()["values"] == [151]

    def test_int_multivalue(self):
        c = RoutingCondition(signal_name="firefox_version", expected_values="150\n151\n152")
        assert c.as_dict()["values"] == [150, 151, 152]

    def test_string_multivalue_country(self):
        c = RoutingCondition(signal_name="country", expected_values="US\nCA\nGB")
        assert c.as_dict()["values"] == ["US", "CA", "GB"]


class TestSignalChoices:
    """The signal_name field pulls its choices from the registry at render
    time, grouped by resolver type."""

    def test_choices_grouped_by_resolver_type(self):
        from springfield.cms.models.routing import _signal_choices

        groups = _signal_choices()
        group_names = [name for name, _entries in groups]
        assert "Server signals" in group_names
        assert "Browser signals" in group_names

    def test_server_signals_in_server_group(self):
        from springfield.cms.models.routing import _signal_choices

        groups = dict(_signal_choices())
        server_names = {entry[0] for entry in groups["Server signals"]}
        assert "country" in server_names
        assert "lapsed_user" in server_names
        assert "platform" in server_names
        # Should NOT appear in the server group.
        assert "ai_controls" not in server_names

    def test_browser_signals_in_browser_group(self):
        from springfield.cms.models.routing import _signal_choices

        groups = dict(_signal_choices())
        browser_names = {entry[0] for entry in groups["Browser signals"]}
        assert "ai_controls" in browser_names
        assert "default_browser" in browser_names
        # Server-side signals should NOT appear here.
        assert "country" not in browser_names


# ---------------------------------------------------------------------------
# RoutingCondition validation
# ---------------------------------------------------------------------------


class TestRoutingConditionClean:
    @pytest.mark.django_db
    def test_rejects_unknown_signal(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, condition={}, save=True)
        c = RoutingCondition(rule=rule, signal_name="does_not_exist", operator="is", expected_values="true")
        with pytest.raises(ValidationError, match="Unknown signal"):
            c.full_clean()

    @pytest.mark.django_db
    def test_rejects_unparseable_int(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, condition={}, save=True)
        c = RoutingCondition(rule=rule, signal_name="firefox_version", operator="is", expected_values="not-a-number")
        with pytest.raises(ValidationError, match="could not be parsed"):
            c.full_clean()

    @pytest.mark.django_db
    def test_rejects_enum_violation(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, condition={}, save=True)
        c = RoutingCondition(rule=rule, signal_name="ai_controls", operator="is", expected_values="not-a-valid-value")
        with pytest.raises(ValidationError, match="must be one of"):
            c.full_clean()

    @pytest.mark.django_db
    def test_accepts_empty_draft(self, _wnp_tree):
        # An empty condition (no signal chosen) is a valid draft state.
        rule = _make_rule(_wnp_tree, condition={}, save=True)
        c = RoutingCondition(rule=rule, signal_name="", operator="is", expected_values="")
        c.full_clean()  # should not raise


# ---------------------------------------------------------------------------
# RoutingRule model behavior
# ---------------------------------------------------------------------------


class TestRoutingRuleModel:
    @pytest.mark.django_db
    def test_create_and_save(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, save=True)
        rule.full_clean()
        assert rule.pk is not None
        assert RoutingRule.objects.filter(pk=rule.pk).exists()
        # And the associated condition exists.
        assert rule.conditions.count() == 1

    @pytest.mark.django_db
    def test_str_repr(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, name="lapsed rule", save=True)
        assert "lapsed rule" in str(rule)
        assert _wnp_tree["variant"].title in str(rule)

    @pytest.mark.django_db
    def test_default_ordering_by_parent_then_sort_order(self, _wnp_tree):
        second_canonical = WhatsNewPage2026Factory(parent=_wnp_tree["index"], title="WNP 157", slug="157", version="157")
        _make_rule(_wnp_tree, name="low", sort_order=50, save=True)
        _make_rule(_wnp_tree, name="high", sort_order=200, save=True)
        _make_rule(_wnp_tree, name="other", sort_order=100, parent_page=second_canonical, save=True)

        # Ordering is by parent_page then sort_order — the same-parent rules
        # sort together, with lower sort_order first.
        names = list(RoutingRule.objects.values_list("name", flat=True))
        # Within the same parent, low (50) should come before high (200).
        assert names.index("low") < names.index("high")

    @pytest.mark.django_db
    def test_clean_rejects_parent_targeting_itself(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, target_page=_wnp_tree["canonical"], condition={}, save=True)
        with pytest.raises(ValidationError, match="cannot target"):
            rule.full_clean()

    @pytest.mark.django_db
    def test_clean_rejects_non_descendant_target(self, _wnp_tree):
        # A rule attached to canonical 156 must target a descendant of that
        # canonical — routing to a sibling (unrelated) page is a common
        # authoring mistake and rejected at save time.
        second_canonical = WhatsNewPage2026Factory(
            parent=_wnp_tree["index"],
            title="WNP 157",
            slug="157",
            version="157",
        )
        rule = _make_rule(_wnp_tree, target_page=second_canonical, condition={}, save=True)
        with pytest.raises(ValidationError, match="descendant"):
            rule.full_clean()

    @pytest.mark.django_db
    def test_clean_accepts_descendant_target(self, _wnp_tree):
        # The default fixture's variant IS a descendant of canonical; make
        # sure the descendant check passes.
        rule = _make_rule(_wnp_tree, save=True)
        rule.full_clean()  # should not raise

    @pytest.mark.django_db
    def test_target_page_protect_prevents_delete(self, _wnp_tree):
        from django.db.models import ProtectedError

        _make_rule(_wnp_tree, save=True)
        with pytest.raises(ProtectedError):
            _wnp_tree["variant"].delete()

    @pytest.mark.django_db
    def test_parent_page_cascade_deletes_rules(self, _wnp_tree):
        # Verify ParentalKey CASCADE — deleting the canonical removes its
        # attached rules. Use a sibling (non-descendant) target here so that
        # Wagtail's cascade on the canonical's descendants doesn't collide
        # with the rule's PROTECTED target_page. Since save() doesn't invoke
        # clean(), the sibling target is fine for this specific test.
        sibling_target = WhatsNewPage2026Factory(
            parent=_wnp_tree["index"],
            title="Sibling target",
            slug="sibling-target",
            version="156",
        )
        rule = _make_rule(_wnp_tree, target_page=sibling_target, save=True)
        rule_id = rule.pk
        _wnp_tree["canonical"].delete()
        assert not RoutingRule.objects.filter(pk=rule_id).exists()

    @pytest.mark.django_db
    def test_status_defaults_to_draft(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, save=True)
        assert rule.status == RULE_STATUS_DRAFT

    @pytest.mark.django_db
    def test_rule_with_no_conditions_permitted(self, _wnp_tree):
        # A rule may exist as a draft with no condition rows attached yet —
        # marketing might save the rule shell and come back to configure
        # conditions later. Only clean() is exercised here; evaluation-time
        # behavior (a zero-condition rule can never match) is covered by
        # evaluator tests.
        rule = _make_rule(_wnp_tree, condition={}, save=True)
        rule.full_clean()
        assert rule.conditions.count() == 0


# ---------------------------------------------------------------------------
# AND semantics — a rule's conditions all must match
# ---------------------------------------------------------------------------


class TestAndSemantics:
    """Rules with multiple conditions match only when EVERY condition matches
    (AND semantics). Covered here at the model + engine layer."""

    @pytest.mark.django_db
    def test_conditions_as_dicts_returns_all(self, _wnp_tree):
        rule = _make_rule(
            _wnp_tree,
            condition=None,
            conditions=[
                {"signal": "country", "op": "is", "values": ["US"]},
                {"signal": "lapsed_user", "op": "is", "values": [True]},
            ],
            save=True,
        )
        dicts = rule.conditions_as_dicts()
        assert len(dicts) == 2
        signals = {d["signal"] for d in dicts}
        assert signals == {"country", "lapsed_user"}

    @pytest.mark.django_db
    def test_all_conditions_match_rule_matches(self, _wnp_tree):
        from springfield.cms.routing.evaluator import evaluate_rules

        rule = _make_rule(
            _wnp_tree,
            condition=None,
            conditions=[
                {"signal": "country", "op": "is", "values": ["US"]},
                {"signal": "lapsed_user", "op": "is", "values": [True]},
            ],
            save=True,
        )
        result = evaluate_rules([rule], {"country": "US", "lapsed_user": True})
        assert result.matched is rule

    @pytest.mark.django_db
    def test_one_failing_condition_rejects_rule(self, _wnp_tree):
        from springfield.cms.routing.evaluator import evaluate_rules

        rule = _make_rule(
            _wnp_tree,
            condition=None,
            conditions=[
                {"signal": "country", "op": "is", "values": ["US"]},
                {"signal": "lapsed_user", "op": "is", "values": [True]},
            ],
            save=True,
        )
        # country matches, lapsed_user doesn't → rule fails (AND).
        result = evaluate_rules([rule], {"country": "US", "lapsed_user": False})
        assert result.matched is None

    @pytest.mark.django_db
    def test_unresolved_condition_marks_rule_unresolved(self, _wnp_tree):
        from springfield.cms.routing.evaluator import evaluate_rules

        rule = _make_rule(
            _wnp_tree,
            condition=None,
            conditions=[
                {"signal": "country", "op": "is", "values": ["US"]},
                {"signal": "default_browser", "op": "is", "values": [True]},
            ],
            save=True,
        )
        # country matches, default_browser not in resolved → unresolved (need client).
        result = evaluate_rules([rule], {"country": "US"})
        assert result.matched is None
        assert rule in result.unresolved

    @pytest.mark.django_db
    def test_false_short_circuits_over_unresolved(self, _wnp_tree):
        # Precedence check: if any condition is definitively False, the rule
        # is False even if another condition is unresolved. One failing
        # AND-clause is enough — waiting for other signals to resolve isn't
        # going to save it.
        from springfield.cms.routing.evaluator import evaluate_rules

        rule = _make_rule(
            _wnp_tree,
            condition=None,
            conditions=[
                {"signal": "country", "op": "is", "values": ["US"]},
                {"signal": "default_browser", "op": "is", "values": [True]},
            ],
            save=True,
        )
        # country resolves False; default_browser unresolved → rule False.
        result = evaluate_rules([rule], {"country": "DE"})
        assert result.matched is None
        assert rule not in result.unresolved
