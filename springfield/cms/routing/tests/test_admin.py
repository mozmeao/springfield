# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the admin signal payload feeding the dynamic condition help."""

from django.conf import settings
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
# Request-time value lists for locale / country string signals.
# ---------------------------------------------------------------------------


def test_payload_attaches_value_lists_for_locale_and_country():
    payload = build_signal_payload()
    assert "US" in payload["country"]["values"]
    assert "en-US" in payload["locale"]["values"]
    # These use the values-oriented lead-in, not the generic STRING operators hint.
    assert payload["country"]["hint"] == str(VALUE_LIST_HINT)
    assert payload["locale"]["hint"] == str(VALUE_LIST_HINT)


def test_browser_language_accepts_languages_we_do_not_serve():
    # The signal exists to reveal visitors whose language we DON'T publish in — a Norwegian
    # served English, say. Restricting it to served languages would leave it unable to say
    # anything `locale` doesn't already say. Validated against CLDR instead.
    values = set(build_signal_payload()["browser_language"]["values"])
    served = {code.split("-")[0] for code, _label in settings.LANGUAGES}

    # Real languages Springfield publishes nothing in, all of which browsers can report.
    assert {"mt", "yo", "dz", "no"} <= values
    # ...and our own base languages are still in there, including any CLDR lacks.
    assert served <= values
    assert len(values) > len(served)


def test_browser_language_still_rejects_typos():
    values = set(build_signal_payload()["browser_language"]["values"])
    # A closed set beats a shape check here: "xx" is well-formed but not a language.
    for typo in ("english", "en_US", "en-au", "xx", "e", "123", ""):
        assert typo not in values


def test_browser_language_shows_served_languages_as_examples():
    # 600-odd CLDR codes would be noise as guidance, so the help shows what we publish in
    # while validation stays permissive.
    entry = build_signal_payload()["browser_language"]
    served = sorted({code.split("-")[0] for code, _label in settings.LANGUAGES})

    assert entry["exampleValues"] == served
    assert len(entry["values"]) > len(entry["exampleValues"])
    # The lead-in must not imply the shown list is exhaustive.
    assert "include" in entry["hint"]


def test_closed_set_signals_carry_no_example_list():
    # locale/country show their real values; only browser_language needs the distinction.
    payload = build_signal_payload()
    assert payload["locale"]["exampleValues"] == []
    assert payload["country"]["exampleValues"] == []


def test_locale_values_are_every_served_locale_not_just_cms_content_languages():
    # The signal reads the *visitor's* page locale, so the offerable set is every locale
    # the site serves — not WAGTAIL_CONTENT_LANGUAGES, which is the far smaller set of
    # locales CMS content is translated into. Using the latter would tell authors that
    # dozens of perfectly targetable locales are invalid.
    values = build_signal_payload()["locale"]["values"]
    served = {code for code, _label in settings.LANGUAGES}
    cms_content = {code for code, _label in settings.WAGTAIL_CONTENT_LANGUAGES}

    assert set(values) == served
    assert len(served) > len(cms_content)
    # A locale the site serves but has no CMS content for must still be offerable.
    outside_cms = sorted(served - cms_content)
    assert outside_cms and outside_cms[0] in values


def test_free_text_url_signal_carries_no_value_list():
    # utm_* are genuinely free text — no known option set, so no values list.
    assert build_signal_payload()["utm_source"]["values"] == []


# ---------------------------------------------------------------------------
# The payload is the only source of truth and carries no raw English.
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
# Signals reference rows are generated straight from the registry.
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
    # source_key drives the per-source badge class; is_uitour drives the delay note.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert rows["platform"]["source_key"] == "user_agent"
    assert rows["country"]["source_key"] == "cdn_geo"
    assert rows["is_default_browser"]["is_uitour"] is True
    assert rows["utm_source"]["is_uitour"] is False


def test_reference_rows_carry_value_lists_for_known_set_string_signals():
    # locale/country expose their value lists (shown collapsed); free text has none.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert "US" in rows["country"]["values"]
    assert "en-US" in rows["locale"]["values"]
    assert rows["utm_source"]["values"] == []  # genuinely free text


def test_reference_rows_carry_a_value_example_per_type():
    # The Values column shows a "what to type" hint for signals with no fixed set —
    # true/false for booleans, version examples, a number example, "Free text" for strings.
    rows = {row["name"]: row for row in build_signal_reference()}
    assert str(rows["is_firefox"]["value_example"]) == "true or false"
    assert "129" in str(rows["firefox_version"]["value_example"])
    assert "30" in str(rows["profile_age"]["value_example"])
    assert str(rows["utm_source"]["value_example"]) == "Free text"
