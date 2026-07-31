# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the admin signal payload feeding the dynamic condition help (C11)."""

from django.utils.functional import Promise

from springfield.cms.routing.admin import VALUE_LIST_HINT, VALUE_TYPE_HINTS, build_signal_payload, build_signal_reference
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


def test_payload_carries_description_and_comma_hint():
    # The dynamic help leads with the (short) description and appends a comma-separated
    # hint only for set-membership operators — both delivered per signal in the payload.
    platform = build_signal_payload()["platform"]
    assert "operating system" in platform["description"]
    assert platform["commaHint"]  # non-empty, localized


# ---------------------------------------------------------------------------
# Request-time value lists for locale / country string signals (ED-3, plan P1-2).
# ---------------------------------------------------------------------------


def test_payload_attaches_value_lists_for_locale_and_country():
    payload = build_signal_payload()
    assert "US" in payload["country"]["values"]
    assert "en-US" in payload["locale"]["values"]
    # These use the values-oriented lead-in, not the generic STRING operators hint.
    assert payload["country"]["hint"] == str(VALUE_LIST_HINT)
    assert payload["locale"]["hint"] == str(VALUE_LIST_HINT)


def test_free_text_url_signal_carries_no_value_list():
    # utm_* are genuinely free text — no known option set, so no values list.
    assert build_signal_payload()["utm_source"]["values"] == []


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


# ---------------------------------------------------------------------------
# Signals reference rows are generated straight from the registry (C13, spec §4.5).
# ---------------------------------------------------------------------------


def test_reference_has_one_row_per_registered_signal():
    rows = build_signal_reference()
    assert {row["name"] for row in rows} == set(registry.names())


def test_reference_row_carries_source_type_operators_and_enum():
    rows = {row["name"]: row for row in build_signal_reference()}
    platform = rows["platform"]
    assert str(platform["source"]) == "User-Agent"
    assert platform["value_type"] == "enum"
    assert {str(label) for label in platform["operators"]} >= {"is", "in"}
    assert {value["value"] for value in platform["enum_values"]} == {"windows", "osx", "linux", "android", "ios", "other"}


def test_reference_includes_the_honesty_notes():
    rows = {row["name"]: row for row in build_signal_reference()}
    # is_firefox still warns about the Firefox-for-iOS edge case, in plain language.
    assert "iOS" in str(rows["is_firefox"]["description"])


def test_reference_rows_carry_a_source_key_and_uitour_flag():
    # C27: source_key drives the per-source badge class; is_uitour drives the delay note.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert rows["platform"]["source_key"] == "user_agent"
    assert rows["country"]["source_key"] == "cdn_geo"
    assert rows["is_default_browser"]["is_uitour"] is True
    assert rows["utm_source"]["is_uitour"] is False


def test_reference_rows_carry_value_lists_for_known_set_string_signals():
    # C27: locale/country expose their value lists (shown collapsed); free text has none.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert "US" in rows["country"]["values"]
    assert "en-US" in rows["locale"]["values"]
    assert rows["utm_source"]["values"] == []  # genuinely free text


def test_reference_rows_carry_a_value_example_per_type():
    # C27: the Values column shows a "what to type" hint for signals with no fixed set —
    # true/false for booleans, version examples, a number example, "Free text" for strings.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert str(rows["is_firefox"]["value_example"]) == "true or false"
    assert "129" in str(rows["firefox_version"]["value_example"])
    assert "30" in str(rows["profile_age"]["value_example"])
    assert str(rows["utm_source"]["value_example"]) == "Free text"
