# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Routing signal vocabulary and registry container.

A **signal** is a named, typed fact about the user or their browser that a routing
rule condition can test. This module defines the signal *mechanism* — value types,
the operator set each value type permits, the ``RoutingSignal`` metadata class, the
flat source list, and the registry container that signals register into. It has no
page or database dependency; the concrete v1 signals are registered separately.

Naming note: the metadata class is ``RoutingSignal``, deliberately never
bare ``Signal`` — bare ``Signal`` collides with ``django.dispatch.Signal`` and is
overloaded here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from django.utils.translation import gettext_lazy as _


class RoutingSignalError(ValueError):
    """Raised for invalid signal definitions or registry misuse."""


class ValueType(str, Enum):
    """The value type of a signal.

    A signal's value type fixes the operator set a condition may use against it and
    drives the dynamic admin help text.
    """

    ENUM = "enum"
    STRING = "string"
    BOOLEAN = "boolean"
    VERSION = "version"
    INTEGER = "integer"


class Source(str, Enum):
    """The flat source list, four live in v1.

    Each source's reading approach is folded into its description rather than split
    into a parallel taxonomy. All reading happens on the client.
    """

    CDN_GEO = "cdn_geo"
    USER_AGENT = "user_agent"
    UITOUR = "uitour"
    URL = "url"


SOURCE_LABELS: dict[Source, object] = {
    Source.CDN_GEO: _("CDN geo header"),
    Source.USER_AGENT: _("User-Agent"),
    Source.UITOUR: _("UITour"),
    Source.URL: _("URL"),
}


@dataclass(frozen=True)
class Operator:
    """A match operator.

    Negation is always the operator's *paired form* — it is never a separate rule
    type. Each operator names its ``counterpart`` (the flipped form) so the client
    evaluator can compute the positive result and flip it for negated operators.
    """

    value: str
    label: object  # gettext_lazy proxy
    negated: bool
    counterpart: str  # the value of the paired (flipped) operator

    @property
    def positive(self) -> str:
        """The value of the positive (non-negated) form of this operator."""
        return self.counterpart if self.negated else self.value


def _make_operator_pair(positive_value, positive_label, negated_value, negated_label):
    positive = Operator(value=positive_value, label=positive_label, negated=False, counterpart=negated_value)
    negated = Operator(value=negated_value, label=negated_label, negated=True, counterpart=positive_value)
    return positive, negated


# Operator definitions, as positive/negated pairs.
_IS, _IS_NOT = _make_operator_pair("is", _("is"), "is_not", _("is not"))
_IN, _NOT_IN = _make_operator_pair("in", _("in"), "not_in", _("not in"))
_EQUALS, _NOT_EQUALS = _make_operator_pair("equals", _("equals"), "not_equals", _("does not equal"))
_LT, _NOT_LT = _make_operator_pair("lt", _("is less than"), "not_lt", _("is not less than"))
_LTE, _NOT_LTE = _make_operator_pair("lte", _("is at most"), "not_lte", _("is more than"))
_GT, _NOT_GT = _make_operator_pair("gt", _("is greater than"), "not_gt", _("is not greater than"))
_GTE, _NOT_GTE = _make_operator_pair("gte", _("is at least"), "not_gte", _("is less than"))


# Registry of every operator, keyed by its stable string value.
OPERATORS: dict[str, Operator] = {
    op.value: op
    for op in (
        _IS,
        _IS_NOT,
        _IN,
        _NOT_IN,
        _EQUALS,
        _NOT_EQUALS,
        _LT,
        _NOT_LT,
        _LTE,
        _NOT_LTE,
        _GT,
        _NOT_GT,
        _GTE,
        _NOT_GTE,
    )
}


# Value type -> the operators a condition may use against a signal of that type.
# This mapping is the sole source of truth for which operators each value type
# permits, and is exercised verbatim in the dynamic help text and the reference page.
VALUE_TYPE_OPERATORS: dict[ValueType, tuple[str, ...]] = {
    ValueType.ENUM: ("is", "is_not", "in", "not_in"),
    ValueType.STRING: ("is", "is_not", "in", "not_in"),
    ValueType.BOOLEAN: ("is", "is_not"),
    ValueType.VERSION: ("equals", "not_equals", "lt", "not_lt", "lte", "not_lte", "gt", "not_gt", "gte", "not_gte"),
    ValueType.INTEGER: ("equals", "not_equals", "lt", "not_lt", "lte", "not_lte", "gt", "not_gt", "gte", "not_gte"),
}


@dataclass(frozen=True)
class EnumValue:
    """One member of an enum signal's closed value set.

    Every enum value carries its own localizable label.
    """

    value: str
    label: object  # gettext_lazy proxy

    def __post_init__(self):
        if not self.label:
            raise RoutingSignalError(f"Enum value {self.value!r} requires a label")


@dataclass(frozen=True)
class RoutingSignal:
    """Metadata for one signal.

    Describes a named, typed fact a rule condition can test. This is metadata only:
    the actual reading of a value happens client-side, never here.
    """

    name: str
    description: object  # gettext_lazy proxy
    source: Source
    value_type: ValueType
    enum_values: tuple[EnumValue, ...] = field(default=())
    browser_state_key: str | None = None

    def __post_init__(self):
        if not isinstance(self.source, Source):
            raise RoutingSignalError(f"Signal {self.name!r} has an unknown source {self.source!r}")
        if not isinstance(self.value_type, ValueType):
            raise RoutingSignalError(f"Signal {self.name!r} has an unknown value type {self.value_type!r}")
        if self.value_type is ValueType.ENUM:
            if not self.enum_values:
                raise RoutingSignalError(f"Enum signal {self.name!r} requires at least one enum value")
        elif self.enum_values:
            raise RoutingSignalError(f"Non-enum signal {self.name!r} must not define enum values")

    @property
    def operators(self) -> tuple[Operator, ...]:
        """The operators legal for this signal's value type."""
        return tuple(OPERATORS[value] for value in VALUE_TYPE_OPERATORS[self.value_type])

    @property
    def operator_values(self) -> tuple[str, ...]:
        """The stable string values of the legal operators."""
        return VALUE_TYPE_OPERATORS[self.value_type]

    def allows_operator(self, operator_value: str) -> bool:
        """Whether ``operator_value`` is legal for this signal's value type."""
        return operator_value in VALUE_TYPE_OPERATORS[self.value_type]


class RoutingSignalRegistry:
    """The single source of truth for signal metadata.

    Signals register into a single instance. Registration is name-unique: two
    signals sharing a name is a programming error and raises.
    """

    def __init__(self):
        self._signals: dict[str, RoutingSignal] = {}

    def register(self, signal: RoutingSignal) -> RoutingSignal:
        if not isinstance(signal, RoutingSignal):
            raise RoutingSignalError(f"Can only register RoutingSignal instances, got {signal!r}")
        if signal.name in self._signals:
            raise RoutingSignalError(f"A signal named {signal.name!r} is already registered")
        self._signals[signal.name] = signal
        return signal

    def get(self, name: str) -> RoutingSignal:
        return self._signals[name]

    def all(self) -> tuple[RoutingSignal, ...]:
        return tuple(self._signals.values())

    def names(self) -> tuple[str, ...]:
        return tuple(self._signals.keys())

    def __contains__(self, name: object) -> bool:
        return name in self._signals

    def __iter__(self):
        return iter(self._signals.values())

    def __len__(self) -> int:
        return len(self._signals)


# The framework-wide registry instance. Populated with the v1 signals separately.
registry = RoutingSignalRegistry()
