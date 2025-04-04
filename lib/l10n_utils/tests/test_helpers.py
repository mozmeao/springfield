# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from unittest.mock import patch

from babel.core import Locale, UnknownLocaleError

from lib.l10n_utils.templatetags import helpers
from springfield.base.tests import TestCase


def test_get_locale():
    """Test that the get_locale() helper works."""
    assert helpers.get_locale("pt-BR").language == "pt"
    assert helpers.get_locale("not-a-lang").language == "en"


def test_get_locale_hsb():
    """Should treat hsb and dsb as de."""
    # bug 1130285
    assert helpers.get_locale("dsb").language == "de"
    assert helpers.get_locale("hsb").language == "de"


class TestCurrentLocale(TestCase):
    @patch("lib.l10n_utils.templatetags.helpers.Locale")
    def test_unknown_locale(self, Locale):
        """
        If Locale.parse raises an UnknownLocaleError, return the en-US
        locale object.
        """
        Locale.parse.side_effect = UnknownLocaleError("foo")
        assert helpers.current_locale() == Locale.return_value
        Locale.assert_called_with("en", "US")

    @patch("lib.l10n_utils.templatetags.helpers.Locale")
    def test_value_error(self, Locale):
        """
        If Locale.parse raises a ValueError, return the en-US locale
        object.
        """
        Locale.parse.side_effect = ValueError
        assert helpers.current_locale() == Locale.return_value
        Locale.assert_called_with("en", "US")

    @patch("lib.l10n_utils.templatetags.helpers.get_language")
    @patch("lib.l10n_utils.templatetags.helpers.Locale")
    def test_success(self, Locale, get_language):
        assert helpers.current_locale() == Locale.parse.return_value
        Locale.parse.assert_called_with(get_language.return_value, sep="-")


class TestL10nFormat(TestCase):
    @patch("lib.l10n_utils.templatetags.helpers.format_date")
    def test_format_date(self, format_date):
        ctx = {"LANG": "de"}
        locale = Locale("de")
        assert helpers.l10n_format_date(ctx, "somedate", format="long") == format_date.return_value
        format_date.assert_called_with("somedate", locale=locale, format="long")

    @patch("lib.l10n_utils.templatetags.helpers.format_date")
    def test_format_date_hyphenated_locale(self, format_date):
        ctx = {"LANG": "en-US"}
        locale = Locale("en", "US")
        assert helpers.l10n_format_date(ctx, "somedate", format="long") == format_date.return_value
        format_date.assert_called_with("somedate", locale=locale, format="long")

    @patch("lib.l10n_utils.templatetags.helpers.format_number")
    def test_format_number(self, format_number):
        ctx = {"LANG": "de"}
        locale = Locale("de")
        assert helpers.l10n_format_number(ctx, 10000) == format_number.return_value
        format_number.assert_called_with(10000, locale=locale)

    @patch("lib.l10n_utils.templatetags.helpers.format_number")
    def test_format_number_hyphenated_locale(self, format_number):
        ctx = {"LANG": "pt-BR"}
        locale = Locale("pt", "BR")
        assert helpers.l10n_format_number(ctx, 10000) == format_number.return_value
        format_number.assert_called_with(10000, locale=locale)
