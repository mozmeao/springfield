# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the admin signal payload feeding the dynamic condition help (C11)."""

from django.utils.functional import Promise

from springfield.cms.routing.admin import VALUE_TYPE_HINTS, build_signal_payload
from springfield.cms.routing.signals import ValueType, registry


def test_payload_covers_every_registered_signal():
    assert set(build_signal_payload()) == set(registry.names())


def test_enum_signal_payload_lists_the_enumerated_set():
    platform = build_signal_payload()["platform"]
    assert platform["valueType"] == "enum"
    assert {value["value"] for value in platform["enumValues"]} == {"windows", "osx", "linux", "android", "ios", "other"}
    # Labels are the registry's own (localized) labels, not fresh literals.
    registry_labels = {str(enum_value.label) for enum_value in registry.get("platform").enum_values}
    assert {value["label"] for value in platform["enumValues"]} == registry_labels


def test_version_signal_payload_has_operator_meanings_and_a_hint():
    version = build_signal_payload()["firefox_version"]
    assert version["enumValues"] == []
    operator_values = {operator["value"] for operator in version["operators"]}
    assert {"gte", "lt", "not_gte"} <= operator_values
    assert version["hint"] == str(VALUE_TYPE_HINTS[ValueType.VERSION])


# ---------------------------------------------------------------------------
# The payload is the only source of truth and carries no raw English (spec §9.2).
# ---------------------------------------------------------------------------


def test_value_type_hints_are_lazy_translated():
    # Every hint is a gettext_lazy source, so nothing bypasses localization.
    assert set(VALUE_TYPE_HINTS) == set(ValueType)
    for hint in VALUE_TYPE_HINTS.values():
        assert isinstance(hint, Promise)


def test_operator_labels_trace_to_the_registry():
    payload = build_signal_payload()
    for name, entry in payload.items():
        registry_labels = {operator.value: str(operator.label) for operator in registry.get(name).operators}
        for operator in entry["operators"]:
            assert operator["label"] == registry_labels[operator["value"]]
