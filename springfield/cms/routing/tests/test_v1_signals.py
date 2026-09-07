# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the concrete v1 routing signals."""

from django.utils.functional import Promise

import pytest

# Importing populates the framework-wide singleton registry (idempotent — the app's
# ready() already imports it at startup).
from springfield.cms.routing import v1_signals  # noqa: F401
from springfield.cms.routing.signals import Source, ValueType, registry

# The v1 registry snapshot of the expected signal set.
EXPECTED_SIGNALS = {
    "country": (Source.CDN_GEO, ValueType.STRING),
    "platform": (Source.USER_AGENT, ValueType.ENUM),
    "firefox_version": (Source.USER_AGENT, ValueType.VERSION),
    "is_firefox": (Source.USER_AGENT, ValueType.BOOLEAN),
    "is_default_browser": (Source.UITOUR, ValueType.BOOLEAN),
    "profile_age_weeks": (Source.UITOUR, ValueType.INTEGER),
    "fxa_signed_in": (Source.UITOUR, ValueType.BOOLEAN),
    "days_since_last_session": (Source.UITOUR, ValueType.INTEGER),
    "profile_reset_weeks_ago": (Source.UITOUR, ValueType.INTEGER),
    "ai_controls": (Source.UITOUR, ValueType.ENUM),
    "utm_source": (Source.URL, ValueType.STRING),
    "utm_medium": (Source.URL, ValueType.STRING),
    "utm_campaign": (Source.URL, ValueType.STRING),
    "oldversion": (Source.URL, ValueType.VERSION),
    "locale": (Source.URL, ValueType.STRING),
    "language": (Source.URL, ValueType.STRING),
    "browser_language": (Source.USER_AGENT, ValueType.STRING),
    "browser_name": (Source.USER_AGENT, ValueType.ENUM),
}


def test_registry_snapshot_lists_expected_signals():
    assert set(registry.names()) == set(EXPECTED_SIGNALS)


@pytest.mark.parametrize("name,expected", EXPECTED_SIGNALS.items())
def test_each_signal_has_expected_source_and_value_type(name, expected):
    signal = registry.get(name)
    source, value_type = expected
    assert signal.source is source
    assert signal.value_type is value_type
    # Value type is always one of the value types.
    assert isinstance(signal.value_type, ValueType)


def test_every_source_is_represented():
    # Every source (all four live in v1) has at least one signal.
    assert {signal.source for signal in registry} == set(Source)


def test_uitour_signals_carry_a_browser_state_key():
    for signal in registry:
        if signal.source is Source.UITOUR:
            assert signal.browser_state_key, f"{signal.name} needs a UITour key"
        elif signal.source in (Source.CDN_GEO, Source.URL):
            assert signal.browser_state_key is None


# ---------------------------------------------------------------------------
# L10N wrapping.
# ---------------------------------------------------------------------------


def test_all_descriptions_are_lazy_translated():
    for signal in registry:
        assert isinstance(signal.description, Promise), f"{signal.name} description not lazy"


def test_enum_signal_labels_are_wrapped_for_l10n():
    enum_signals = [s for s in registry if s.value_type is ValueType.ENUM]
    assert enum_signals  # sanity: there are enum signals to check
    for signal in enum_signals:
        assert signal.enum_values
        for enum_value in signal.enum_values:
            assert isinstance(enum_value.label, Promise), f"{signal.name}:{enum_value.value} label not lazy"


# ---------------------------------------------------------------------------
# Operator sets follow value type.
# ---------------------------------------------------------------------------


def test_version_signal_advertises_version_operators_only():
    version = registry.get("firefox_version")
    assert set(version.operator_values) == {"equals", "not_equals", "lt", "lte", "gt", "gte"}
    # Set-membership / equality-only operators are not offered for versions.
    assert not version.allows_operator("in")
    assert not version.allows_operator("is")


# ---------------------------------------------------------------------------
# Signal-value honesty — the two required notes.
# ---------------------------------------------------------------------------


def test_is_firefox_notes_cross_platform_coverage():
    # Editors should know it matches Firefox everywhere, not just desktop.
    description = str(registry.get("is_firefox").description)
    assert "iOS" in description
    assert "Android" in description


def test_fxa_signed_in_reads_the_fxa_key_not_the_deprecated_sync_key():
    # `sync.setup` only reports that Sync is configured, which UITour.sys.mjs itself marks
    # deprecated; `fxa.setup` is the account's actual signed-in state.
    fxa_signed_in = registry.get("fxa_signed_in")
    assert fxa_signed_in.browser_state_key == "fxa"


def test_days_since_last_session_notes_it_measures_since_the_browser_closed():
    # The sharpest trap in this signal: it's days since Firefox last quit, not days since
    # the visitor was last active. A long-running session that never restarts reads as
    # lapsed until it does.
    description = str(registry.get("days_since_last_session").description)
    assert "closed" in description


# ---------------------------------------------------------------------------
# oldversion + locale: URL-derived, replacing a dedicated lapsed_user.
# ---------------------------------------------------------------------------


def test_lapsed_user_signal_is_not_introduced():
    # Lapsing is expressed via oldversion + version operators, not a bespoke signal.
    assert "lapsed_user" not in registry.names()


def test_oldversion_is_a_url_version_signal_using_version_operators():
    oldversion = registry.get("oldversion")
    assert oldversion.source is Source.URL
    assert oldversion.value_type is ValueType.VERSION
    # Version-aware operators only — not equality/set-membership.
    assert oldversion.allows_operator("lte")
    assert not oldversion.allows_operator("is")
    assert not oldversion.allows_operator("in")


def test_locale_is_a_url_string_signal_using_membership_operators():
    locale = registry.get("locale")
    assert locale.source is Source.URL
    assert locale.value_type is ValueType.STRING
    assert locale.allows_operator("is")
    assert locale.allows_operator("in")


def test_language_is_the_region_free_companion_to_locale():
    language = registry.get("language")
    assert language.source is Source.URL
    assert language.value_type is ValueType.STRING
    assert language.allows_operator("is")
    assert language.allows_operator("in")


def test_browser_language_is_read_from_the_user_agent_not_the_url():
    # Deliberately NOT a URL signal: it reflects what the browser prefers, which the
    # served page's locale cannot tell you once content fell back to another language.
    browser_language = registry.get("browser_language")
    assert browser_language.source is Source.USER_AGENT
    assert browser_language.value_type is ValueType.STRING


def test_locale_and_language_descriptions_point_authors_at_each_other():
    # The pair is only useful if an author can tell which one they want.
    assert "language" in str(registry.get("locale").description)
    assert "en-US" in str(registry.get("language").description)


def test_browser_name_is_read_from_the_user_agent_not_uitour():
    # UA sniffing, not UITour: it must work off Firefox too, to identify the browsers it
    # names.
    browser_name = registry.get("browser_name")
    assert browser_name.source is Source.USER_AGENT
    assert browser_name.value_type is ValueType.ENUM
    assert {value.value for value in browser_name.enum_values} == {
        "firefox",
        "chrome",
        "edge",
        "opera",
        "safari",
        "brave",
        "other",
    }
