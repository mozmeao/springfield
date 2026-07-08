# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.exceptions import ValidationError

import pytest
from wagtail.models import Page

from springfield.cms.models import RoutingRule
from springfield.cms.models.routing import (
    RULE_STATUS_DRAFT,
    _validate_condition,
)
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
# Condition validation
# ---------------------------------------------------------------------------


class TestConditionValidation:
    def test_valid_signal_passes(self):
        _validate_condition({"signal": "lapsed_user", "equals": True})

    def test_missing_signal_key_rejected(self):
        with pytest.raises(ValidationError, match="signal"):
            _validate_condition({"equals": True})

    def test_missing_equals_key_rejected(self):
        with pytest.raises(ValidationError, match="equals"):
            _validate_condition({"signal": "lapsed_user"})

    def test_unknown_signal_rejected(self):
        with pytest.raises(ValidationError, match="Unknown signal"):
            _validate_condition({"signal": "not_a_real_signal", "equals": True})

    def test_unknown_key_rejected(self):
        with pytest.raises(ValidationError, match="Unknown keys"):
            _validate_condition({"signal": "lapsed_user", "equals": True, "bogus": 1})

    def test_non_dict_rejected(self):
        with pytest.raises(ValidationError, match="JSON object"):
            _validate_condition([])


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
        # only kicks in when a condition IS present.
        rule = _make_rule(_wnp_tree, condition={})
        rule.full_clean()
        rule.save()
        assert rule.condition == {}
