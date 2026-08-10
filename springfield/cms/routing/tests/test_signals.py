# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the routing signal vocabulary and registry container."""

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
# Value type -> operator mapping matches the canonical operator table exactly.
# ---------------------------------------------------------------------------

# The expected mapping, transcribed by hand, kept independent of
# the module's own table so a drift in either is caught here.
EXPECTED_OPERATORS = {
    ValueType.ENUM: {"is", "is_not", "in", "not_in"},
    ValueType.STRING: {"is", "is_not", "in", "not_in"},
    ValueType.BOOLEAN: {"is", "is_not"},
    # Ordered types carry no negated comparisons: the opposite of each one is already
    # another operator in the set, so a negated form would only duplicate it.
    ValueType.VERSION: {"equals", "not_equals", "lt", "lte", "gt", "gte"},
    ValueType.INTEGER: {"equals", "not_equals", "lt", "lte", "gt", "gte"},
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
# Operators: every one names its opposite, and the opposite names it back.
# ---------------------------------------------------------------------------


def test_operator_counterparts_point_back():
    """Two families share the ``counterpart`` field, with different invariants.

    Negation pairs (``is``/``is_not``) flip the negated flag. Ordered comparisons
    (``lt``/``gte``) are both positive and simply oppose each other, because the negation
    of a comparison is another comparison that already exists.
    """
    for value, operator in OPERATORS.items():
        counterpart = OPERATORS[operator.counterpart]
        assert counterpart.counterpart == value
        assert not OPERATORS[operator.positive].negated
        if operator.negated or counterpart.negated:
            assert counterpart.negated is not operator.negated
            assert operator.positive == counterpart.positive
        else:
            assert operator.positive == value


def test_no_two_operators_share_a_label():
    """A duplicated label is indistinguishable in the dropdown.

    This is what a negated form of an ordered comparison produced: ``not_gte`` and ``lt``
    both read "is less than", so the author saw the same option twice.
    """
    labels = [str(operator.label) for operator in OPERATORS.values()]
    assert len(labels) == len(set(labels)), sorted(labels)


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
    # Inline import: this test inspects the module object itself for an absent attribute,
    # which needs the module bound to a name rather than its members imported.
    import springfield.cms.routing.signals as module

    assert not hasattr(module, "Signal")
    assert RoutingSignal.__name__ == "RoutingSignal"
