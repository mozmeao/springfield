# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing signal vocabulary and registry container (C1)."""

import pytest

from springfield.cms.routing.signals import (
    OPERATORS,
    VALUE_TYPE_OPERATORS,
    EnumValue,
    RoutingSignal,
    RoutingSignalError,
    RoutingSignalRegistry,
    Source,
    ValueType,
)

# ---------------------------------------------------------------------------
# Value type -> operator mapping matches spec §4.3 exactly.
# ---------------------------------------------------------------------------

# The expected mapping, transcribed straight from spec §4.3, kept independent of
# the module's own table so a drift in either is caught here.
EXPECTED_OPERATORS = {
    ValueType.ENUM: {"is", "is_not", "in", "not_in"},
    ValueType.STRING: {"is", "is_not", "in", "not_in"},
    ValueType.BOOLEAN: {"is", "is_not"},
    ValueType.VERSION: {"equals", "not_equals", "lt", "not_lt", "lte", "not_lte", "gt", "not_gt", "gte", "not_gte"},
    ValueType.INTEGER: {"equals", "not_equals", "lt", "not_lt", "lte", "not_lte", "gt", "not_gt", "gte", "not_gte"},
}


@pytest.mark.parametrize("value_type", list(ValueType))
def test_value_type_exposes_only_its_legal_operators(value_type):
    assert set(VALUE_TYPE_OPERATORS[value_type]) == EXPECTED_OPERATORS[value_type]


def test_every_value_type_is_mapped():
    assert set(VALUE_TYPE_OPERATORS) == set(ValueType)


def test_signal_operators_reflect_value_type():
    enum_signal = RoutingSignal(
        name="country",
        description="country",
        source=Source.CDN_GEO,
        value_type=ValueType.ENUM,
        enum_values=(EnumValue("US", "United States"),),
    )
    assert set(enum_signal.operator_values) == EXPECTED_OPERATORS[ValueType.ENUM]

    version_signal = RoutingSignal(
        name="version",
        description="version",
        source=Source.USER_AGENT,
        value_type=ValueType.VERSION,
    )
    assert set(version_signal.operator_values) == EXPECTED_OPERATORS[ValueType.VERSION]
    assert not version_signal.allows_operator("in")
    assert version_signal.allows_operator("gte")


# ---------------------------------------------------------------------------
# Operators: paired negations (spec §4.3 / §7.3).
# ---------------------------------------------------------------------------


def test_operators_are_paired_negations():
    for value, operator in OPERATORS.items():
        counterpart = OPERATORS[operator.counterpart]
        # The counterpart flips the negated flag and points back to this operator.
        assert counterpart.negated is not operator.negated
        assert counterpart.counterpart == value
        # The positive form of both members of a pair is the same operator value.
        assert operator.positive == counterpart.positive
        assert not OPERATORS[operator.positive].negated


# ---------------------------------------------------------------------------
# RoutingSignal validation.
# ---------------------------------------------------------------------------


def test_enum_signal_requires_enum_values():
    with pytest.raises(RoutingSignalError):
        RoutingSignal(
            name="broken",
            description="no values",
            source=Source.URL,
            value_type=ValueType.ENUM,
        )


def test_enum_entries_require_labels():
    with pytest.raises(RoutingSignalError):
        EnumValue("US", "")
    with pytest.raises(RoutingSignalError):
        EnumValue("US", None)


def test_non_enum_signal_rejects_enum_values():
    with pytest.raises(RoutingSignalError):
        RoutingSignal(
            name="broken",
            description="stray values",
            source=Source.URL,
            value_type=ValueType.STRING,
            enum_values=(EnumValue("US", "United States"),),
        )


def test_unknown_source_or_value_type_rejected():
    with pytest.raises(RoutingSignalError):
        RoutingSignal(name="x", description="d", source="cdn_geo", value_type=ValueType.STRING)
    with pytest.raises(RoutingSignalError):
        RoutingSignal(name="x", description="d", source=Source.URL, value_type="string")


# ---------------------------------------------------------------------------
# Registry container.
# ---------------------------------------------------------------------------


def _signal(name):
    return RoutingSignal(name=name, description=name, source=Source.URL, value_type=ValueType.STRING)


def test_registry_registers_and_retrieves():
    reg = RoutingSignalRegistry()
    signal = reg.register(_signal("utm_source"))
    assert reg.get("utm_source") is signal
    assert "utm_source" in reg
    assert reg.names() == ("utm_source",)
    assert len(reg) == 1


def test_registering_duplicate_name_errors():
    reg = RoutingSignalRegistry()
    reg.register(_signal("dupe"))
    with pytest.raises(RoutingSignalError):
        reg.register(_signal("dupe"))


def test_registry_only_accepts_routing_signals():
    reg = RoutingSignalRegistry()
    with pytest.raises(RoutingSignalError):
        reg.register(object())


def test_naming_avoids_django_dispatch_signal_collision():
    # The metadata class is named RoutingSignal, never bare Signal (spec §3).
    import springfield.cms.routing.signals as module

    assert not hasattr(module, "Signal")
    assert RoutingSignal.__name__ == "RoutingSignal"
