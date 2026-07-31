# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the arming-condition abstraction and routing param constants."""

from django.test import RequestFactory

import pytest

from springfield.cms.routing import params
from springfield.cms.routing.arming import (
    ArmingCondition,
    QueryParamArmingCondition,
    QueryParamValueArmingCondition,
)

rf = RequestFactory()


# ---------------------------------------------------------------------------
# Query-param arming condition (v1 realization).
# ---------------------------------------------------------------------------


def test_armed_when_trigger_param_present():
    condition = QueryParamArmingCondition("routing")
    assert condition.is_satisfied(rf.get("/whatsnew/?routing=1")) is True


def test_not_armed_when_trigger_param_absent():
    condition = QueryParamArmingCondition("routing")
    assert condition.is_satisfied(rf.get("/whatsnew/")) is False
    # A different, unrelated param does not arm routing.
    assert condition.is_satisfied(rf.get("/whatsnew/?utm_source=x")) is False


def test_presence_based_empty_value_still_arms():
    condition = QueryParamArmingCondition("routing")
    assert condition.is_satisfied(rf.get("/whatsnew/?routing=")) is True


def test_defaults_to_the_framework_trigger_param():
    condition = QueryParamArmingCondition()
    assert condition.param_name == params.TRIGGER_PARAM
    assert condition.is_satisfied(rf.get(f"/?{params.TRIGGER_PARAM}=1")) is True


def test_each_consumer_can_use_its_own_param():
    paid = QueryParamArmingCondition("r")
    assert paid.is_satisfied(rf.get("/landing/?r=1")) is True
    assert paid.is_satisfied(rf.get("/landing/?routing=1")) is False


# ---------------------------------------------------------------------------
# Value-matching arming condition: present AND value in the set.
# ---------------------------------------------------------------------------


def test_value_condition_armed_when_value_matches():
    condition = QueryParamValueArmingCondition("utm_source", {"update"})
    assert condition.is_satisfied(rf.get("/whatsnew/?utm_source=update")) is True


def test_value_condition_not_armed_when_param_absent():
    condition = QueryParamValueArmingCondition("utm_source", {"update"})
    assert condition.is_satisfied(rf.get("/whatsnew/")) is False


def test_value_condition_not_armed_on_value_mismatch():
    condition = QueryParamValueArmingCondition("utm_source", {"update"})
    assert condition.is_satisfied(rf.get("/whatsnew/?utm_source=newsletter")) is False


def test_value_condition_empty_value_does_not_arm():
    # Unlike the presence-only condition, an empty value is a mismatch.
    condition = QueryParamValueArmingCondition("utm_source", {"update"})
    assert condition.is_satisfied(rf.get("/whatsnew/?utm_source=")) is False


def test_value_condition_accepts_any_of_several_values():
    condition = QueryParamValueArmingCondition("utm_source", {"update", "upgrade"})
    assert condition.is_satisfied(rf.get("/?utm_source=update")) is True
    assert condition.is_satisfied(rf.get("/?utm_source=upgrade")) is True
    assert condition.is_satisfied(rf.get("/?utm_source=other")) is False


# ---------------------------------------------------------------------------
# The abstraction is a real seam: callers depend only on is_satisfied().
# ---------------------------------------------------------------------------


def test_abstraction_is_swappable():
    class AlwaysArmed(ArmingCondition):
        def is_satisfied(self, request):
            return True

    # A caller that only knows the interface works with any realization.
    def caller_arms(condition, request):
        return condition.is_satisfied(request)

    assert caller_arms(AlwaysArmed(), rf.get("/")) is True
    assert caller_arms(QueryParamArmingCondition("routing"), rf.get("/")) is False


def test_base_class_requires_a_realization():
    with pytest.raises(NotImplementedError):
        ArmingCondition().is_satisfied(rf.get("/"))


# ---------------------------------------------------------------------------
# Param constants are centralized.
# ---------------------------------------------------------------------------


def test_param_constants_are_defined():
    assert params.TRIGGER_PARAM == "routing"
    assert params.LOOP_BREAKER_PARAM == "routed"
    assert params.PREVIEW_RULE_PARAM == "preview_rule"
    assert params.PREVIEW_SIGNAL_PARAM == "preview_signal"


def test_param_constants_are_distinct():
    names = {
        params.TRIGGER_PARAM,
        params.LOOP_BREAKER_PARAM,
        params.PREVIEW_RULE_PARAM,
        params.PREVIEW_SIGNAL_PARAM,
    }
    assert len(names) == 4
