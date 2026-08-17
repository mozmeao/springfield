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


def test_get_locale_ja_jp_mac():
    """Should treat ja-JP-mac as ja, which Babel can't parse on its own."""
    assert helpers.get_locale("ja-JP-mac").language == "ja"


def test_l10n_format_list_localizes_separators_and_conjunction():
    """Each locale supplies its own separators and conjunction via CLDR."""
    names = ["Ada Lovelace", "Grace Hopper", "Alan Turing"]
    assert helpers.l10n_format_list({"LANG": "en-US"}, names) == "Ada Lovelace, Grace Hopper, and Alan Turing"
    assert helpers.l10n_format_list({"LANG": "es-ES"}, names) == "Ada Lovelace, Grace Hopper y Alan Turing"
    assert helpers.l10n_format_list({"LANG": "de"}, names) == "Ada Lovelace, Grace Hopper und Alan Turing"
    # CJK locales use an ideographic comma and drop the spaces entirely.
    assert helpers.l10n_format_list({"LANG": "zh-CN"}, names) == "Ada Lovelace、Grace Hopper和Alan Turing"


def test_l10n_format_list_handles_short_lists():
    assert helpers.l10n_format_list({"LANG": "en-US"}, ["Ada Lovelace", "Grace Hopper"]) == "Ada Lovelace and Grace Hopper"
    assert helpers.l10n_format_list({"LANG": "en-US"}, ["Ada Lovelace"]) == "Ada Lovelace"
    assert helpers.l10n_format_list({"LANG": "en-US"}, []) == ""


def test_l10n_format_list_unknown_locale_falls_back_to_default():
    assert helpers.l10n_format_list({"LANG": "not-a-lang"}, ["Ada Lovelace", "Alan Turing"]) == "Ada Lovelace and Alan Turing"


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
