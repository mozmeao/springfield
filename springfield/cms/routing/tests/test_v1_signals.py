# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the concrete v1 routing signals (C2)."""

from django.utils.functional import Promise

import pytest

# Importing populates the framework-wide singleton registry (idempotent — the app's
# ready() already imports it at startup).
from springfield.cms.routing import v1_signals  # noqa: F401
from springfield.cms.routing.signals import Source, ValueType, registry

# The v1 registry snapshot, transcribed from spec §4.2 / the design brief signal set.
EXPECTED_SIGNALS = {
    "country": (Source.CDN_GEO, ValueType.STRING),
    "platform": (Source.USER_AGENT, ValueType.ENUM),
    "firefox_version": (Source.USER_AGENT, ValueType.VERSION),
    "is_firefox": (Source.USER_AGENT, ValueType.BOOLEAN),
    "is_default_browser": (Source.UITOUR, ValueType.BOOLEAN),
    "profile_age": (Source.UITOUR, ValueType.INTEGER),
    "fxa_signed_in": (Source.UITOUR, ValueType.BOOLEAN),
    "ai_controls": (Source.UITOUR, ValueType.ENUM),
    "utm_source": (Source.URL, ValueType.STRING),
    "utm_medium": (Source.URL, ValueType.STRING),
    "utm_campaign": (Source.URL, ValueType.STRING),
    "oldversion": (Source.URL, ValueType.VERSION),
    "locale": (Source.URL, ValueType.STRING),
}


def test_registry_snapshot_lists_expected_signals():
    assert set(registry.names()) == set(EXPECTED_SIGNALS)


@pytest.mark.parametrize("name,expected", EXPECTED_SIGNALS.items())
def test_each_signal_has_expected_source_and_value_type(name, expected):
    signal = registry.get(name)
    source, value_type = expected
    assert signal.source is source
    assert signal.value_type is value_type
    # Value type is always one of the §4.3 types.
    assert isinstance(signal.value_type, ValueType)


def test_every_source_is_represented():
    # Every §4.2 source (all four live in v1) has at least one signal.
    assert {signal.source for signal in registry} == set(Source)


def test_uitour_signals_carry_a_browser_state_key():
    for signal in registry:
        if signal.source is Source.UITOUR:
            assert signal.browser_state_key, f"{signal.name} needs a UITour key"
        elif signal.source in (Source.CDN_GEO, Source.URL):
            assert signal.browser_state_key is None


# ---------------------------------------------------------------------------
# L10N wrapping (cross-cutting §0.3 / spec §9.2).
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
# Operator sets follow value type (spec §4.3).
# ---------------------------------------------------------------------------


def test_version_signal_advertises_version_operators_only():
    version = registry.get("firefox_version")
    assert set(version.operator_values) == {
        "equals",
        "not_equals",
        "lt",
        "not_lt",
        "lte",
        "not_lte",
        "gt",
        "not_gt",
        "gte",
        "not_gte",
    }
    # Set-membership / equality-only operators are not offered for versions.
    assert not version.allows_operator("in")
    assert not version.allows_operator("is")


# ---------------------------------------------------------------------------
# Signal-value honesty (spec §4.4) — the two required notes.
# ---------------------------------------------------------------------------


def test_is_firefox_notes_cross_platform_coverage():
    # Editors should know it matches Firefox everywhere, not just desktop.
    description = str(registry.get("is_firefox").description)
    assert "iOS" in description
    assert "Android" in description


# ---------------------------------------------------------------------------
# oldversion + locale (plan P1-2): URL-derived, replacing a dedicated lapsed_user.
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
