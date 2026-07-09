# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

import pytest
from wagtail.models import Page

from springfield.cms.models import RoutingRule
from springfield.cms.models.routing import RULE_STATUS_DRAFT
from springfield.cms.tests.factories import (
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)


@pytest.fixture
def _wnp_tree(db):
    """Build a small WNP tree: index → canonical + variant."""
    root = Page.objects.get(depth=1)
    home = root.get_children().first() or root.add_child(instance=Page(title="Home", slug="home"))
    index = WhatsNewIndexPageFactory(parent=home, title="WNP Index", slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, title="WNP 156", slug="156", version="156")
    variant = WhatsNewPage2026Factory(parent=index, title="WNP 156 lapsed", slug="156-lapsed", version="156")
    return {"index": index, "canonical": canonical, "variant": variant}


def _make_rule(_wnp_tree, **overrides):
    defaults = {
        "name": "lapsed users",
        "priority": 100,
        "parent_page": _wnp_tree["canonical"],
        "target_page": _wnp_tree["variant"],
        "condition": {"signal": "lapsed_user", "equals": True},
        "status": RULE_STATUS_DRAFT,
    }
    defaults.update(overrides)
    return RoutingRule(**defaults)


# ---------------------------------------------------------------------------
# Condition — synthesized from structured fields
# ---------------------------------------------------------------------------


class TestConditionProperty:
    """The ``condition`` property is the read/write shim between the
    rule engine's ``{"signal", "op", "values"}`` shape and the structured
    ``signal_name`` / ``operator`` / ``expected_values`` fields.

    The setter also accepts the legacy ``{"signal", "equals"}`` shape for
    backward compatibility with test helpers written pre-multi-value.
    """

    def test_setter_new_shape_multivalue(self):
        rule = RoutingRule()
        rule.condition = {"signal": "country", "op": "is", "values": ["US", "CA"]}
        assert rule.signal_name == "country"
        assert rule.operator == "is"
        assert rule.expected_values == "US\nCA"

    def test_setter_new_shape_is_not(self):
        rule = RoutingRule()
        rule.condition = {"signal": "country", "op": "is_not", "values": ["US"]}
        assert rule.operator == "is_not"
        assert rule.expected_values == "US"

    def test_setter_legacy_bool_shape(self):
        rule = RoutingRule()
        rule.condition = {"signal": "lapsed_user", "equals": True}
        assert rule.signal_name == "lapsed_user"
        assert rule.operator == "is"
        assert rule.expected_values == "true"

    def test_setter_legacy_string_shape(self):
        rule = RoutingRule()
        rule.condition = {"signal": "ai_controls", "equals": "available"}
        assert rule.signal_name == "ai_controls"
        assert rule.operator == "is"
        assert rule.expected_values == "available"

    def test_setter_legacy_int_shape(self):
        rule = RoutingRule()
        rule.condition = {"signal": "firefox_version", "equals": 151}
        assert rule.signal_name == "firefox_version"
        assert rule.expected_values == "151"

    def test_getter_returns_new_shape(self):
        rule = RoutingRule(signal_name="lapsed_user", operator="is", expected_values="true")
        assert rule.condition == {"signal": "lapsed_user", "op": "is", "values": [True]}

    def test_getter_multivalue_from_newlines(self):
        rule = RoutingRule(signal_name="country", operator="is", expected_values="US\nCA\nGB")
        assert rule.condition == {"signal": "country", "op": "is", "values": ["US", "CA", "GB"]}

    def test_getter_multivalue_from_commas(self):
        rule = RoutingRule(signal_name="country", operator="is", expected_values="US, CA, GB")
        assert rule.condition == {"signal": "country", "op": "is", "values": ["US", "CA", "GB"]}

    def test_getter_is_not_operator(self):
        rule = RoutingRule(signal_name="country", operator="is_not", expected_values="US")
        assert rule.condition == {"signal": "country", "op": "is_not", "values": ["US"]}

    def test_getter_empty_when_no_signal(self):
        rule = RoutingRule(signal_name="", expected_values="")
        assert rule.condition == {}

    def test_setter_handles_non_dict(self):
        rule = RoutingRule(signal_name="lapsed_user", expected_values="true")
        rule.condition = None
        assert rule.signal_name == ""
        assert rule.expected_values == ""


class TestValueParsing:
    def test_bool_accepts_true_yes_1(self):
        for text in ("true", "True", "yes", "1"):
            rule = RoutingRule(signal_name="lapsed_user", expected_values=text)
            assert rule.condition["values"] == [True], text

    def test_bool_accepts_false_no_0(self):
        for text in ("false", "False", "no", "0"):
            rule = RoutingRule(signal_name="lapsed_user", expected_values=text)
            assert rule.condition["values"] == [False], text

    def test_bool_unparseable_dropped_from_values(self):
        rule = RoutingRule(signal_name="lapsed_user", expected_values="maybe")
        # Unparseable values are dropped from the getter's list — the rule
        # will then have zero values, which the evaluator treats as no-match.
        assert rule.condition["values"] == []

    def test_int_parses_number(self):
        rule = RoutingRule(signal_name="firefox_version", expected_values="151")
        assert rule.condition["values"] == [151]

    def test_int_multivalue(self):
        rule = RoutingRule(signal_name="firefox_version", expected_values="150\n151\n152")
        assert rule.condition["values"] == [150, 151, 152]

    def test_string_multivalue_country(self):
        rule = RoutingRule(signal_name="country", expected_values="US\nCA\nGB")
        assert rule.condition["values"] == ["US", "CA", "GB"]


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
# Model behavior
# ---------------------------------------------------------------------------


class TestRoutingRuleModel:
    @pytest.mark.django_db
    def test_create_and_save(self, _wnp_tree):
        rule = _make_rule(_wnp_tree)
        rule.full_clean()
        rule.save()
        assert rule.pk is not None
        assert RoutingRule.objects.filter(pk=rule.pk).exists()

    @pytest.mark.django_db
    def test_str_repr(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, name="lapsed rule")
        rule.save()
        assert "lapsed rule" in str(rule)
        assert _wnp_tree["variant"].title in str(rule)

    @pytest.mark.django_db
    def test_default_ordering_by_parent_then_priority(self, _wnp_tree):
        second_canonical = WhatsNewPage2026Factory(parent=_wnp_tree["index"], title="WNP 157", slug="157", version="157")
        rule_low = _make_rule(_wnp_tree, name="low", priority=50)
        rule_high = _make_rule(_wnp_tree, name="high", priority=200)
        rule_other = _make_rule(_wnp_tree, name="other", priority=100, parent_page=second_canonical)
        rule_low.save()
        rule_high.save()
        rule_other.save()

        # Ordering is by parent_page then priority — the same-parent rules
        # sort together, with lower priority first.
        names = list(RoutingRule.objects.values_list("name", flat=True))
        # Within the same parent, low (50) should come before high (200).
        assert names.index("low") < names.index("high")

    @pytest.mark.django_db
    def test_clean_rejects_unknown_signal(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, condition={"signal": "does_not_exist", "equals": True})
        with pytest.raises(ValidationError):
            rule.full_clean()

    @pytest.mark.django_db
    def test_clean_rejects_parent_targeting_itself(self, _wnp_tree):
        rule = _make_rule(_wnp_tree, target_page=_wnp_tree["canonical"])
        with pytest.raises(ValidationError, match="cannot target"):
            rule.full_clean()

    @pytest.mark.django_db
    def test_target_page_protect_prevents_delete(self, _wnp_tree):
        from django.db.models import ProtectedError

        rule = _make_rule(_wnp_tree)
        rule.save()
        with pytest.raises(ProtectedError):
            _wnp_tree["variant"].delete()

    @pytest.mark.django_db
    def test_parent_page_cascade_deletes_rules(self, _wnp_tree):
        rule = _make_rule(_wnp_tree)
        rule.save()
        rule_id = rule.pk
        _wnp_tree["canonical"].delete()
        assert not RoutingRule.objects.filter(pk=rule_id).exists()

    @pytest.mark.django_db
    def test_status_defaults_to_draft(self, _wnp_tree):
        rule = _make_rule(_wnp_tree)
        rule.save()
        assert rule.status == RULE_STATUS_DRAFT

    @pytest.mark.django_db
    def test_empty_condition_permitted(self, _wnp_tree):
        # A rule may be saved as a draft with no condition yet — validation
        # only kicks in when a signal IS chosen. Emulates marketing creating
        # a rule and coming back later to fill it in.
        rule = _make_rule(_wnp_tree, condition={})
        rule.full_clean()
        rule.save()
        assert rule.signal_name == ""
        assert rule.expected_values == ""
        assert rule.condition == {}

    @pytest.mark.django_db
    def test_clean_rejects_unparseable_value(self, _wnp_tree):
        # firefox_version expects an integer; "abc" cannot be parsed.
        rule = _make_rule(
            _wnp_tree,
            condition={"signal": "firefox_version", "equals": "abc"},
        )
        with pytest.raises(ValidationError, match="could not be parsed"):
            rule.full_clean()

    @pytest.mark.django_db
    def test_clean_rejects_value_outside_enum(self, _wnp_tree):
        # ai_controls has enum_values = (enabled, available, blocked).
        rule = _make_rule(
            _wnp_tree,
            condition={"signal": "ai_controls", "equals": "sometimes"},
        )
        with pytest.raises(ValidationError, match="must be one of"):
            rule.full_clean()
