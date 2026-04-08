# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from unittest.mock import patch

from django.test import TestCase, override_settings

import pytest
from django_jinja.backend import Jinja2

from lib.l10n_utils import get_translations_native_names
from springfield.base.templatetags import helpers

jinja_env = Jinja2.get_default()
SEND_TO_DEVICE_MESSAGE_SETS = {
    "default": {
        "email": {
            "android": "download-firefox-android",
            "ios": "download-firefox-ios",
            "all": "download-firefox-mobile",
        }
    }
}


def render(s, context={}):
    t = jinja_env.from_string(s)
    return t.render(context)


class HelpersTests(TestCase):
    def test_urlencode_with_unicode(self):
        template = '<a href="?var={{ key|urlencode }}">'
        context = {"key": "?& /()"}
        assert render(template, context) == '<a href="?var=%3F%26+%2F%28%29">'
        # non-ascii
        context = {"key": "\xe4"}
        assert render(template, context) == '<a href="?var=%C3%A4">'

    def test_mailtoencode_with_unicode(self):
        template = '<a href="?var={{ key|mailtoencode }}">'
        context = {"key": "?& /()"}
        assert render(template, context) == '<a href="?var=%3F%26%20/%28%29">'
        # non-ascii
        context = {"key": "\xe4"}
        assert render(template, context) == '<a href="?var=%C3%A4">'


@override_settings(LANG_GROUPS={"en": ["en-US", "en-GB"]})
def test_switch():
    with patch.object(helpers, "waffle") as waffle:
        ret = helpers.switch({"LANG": "de"}, "dude", ["fr", "de"])

    assert ret is waffle.switch.return_value
    waffle.switch.assert_called_with("dude")

    with patch.object(helpers, "waffle") as waffle:
        assert not helpers.switch({"LANG": "de"}, "dude", ["fr", "en"])

    waffle.switch.assert_not_called()

    with patch.object(helpers, "waffle") as waffle:
        ret = helpers.switch({"LANG": "de"}, "dude")

    assert ret is waffle.switch.return_value
    waffle.switch.assert_called_with("dude")

    with patch.object(helpers, "waffle") as waffle:
        ret = helpers.switch({"LANG": "en-GB"}, "dude", ["de", "en"])

    assert ret is waffle.switch.return_value
    waffle.switch.assert_called_with("dude")


@override_settings(FALLBACK_LOCALES={})
@pytest.mark.parametrize(
    "translations_locales, cms_locales, django_locales, expected",
    (
        (
            ["en-US", "fr", "sco"],
            ["de", "pt-BR"],
            ["ja-JP", "zh-CN"],
            ["de", "pt-BR", "ja-JP", "zh-CN"],
        ),
        (
            # Just use defaults
            ["en-US", "fr", "sco"],
            [],
            [],
            ["en-US", "fr", "sco"],
        ),
        (
            # Don't use CMS + Django Fallback
            ["en-US", "fr", "sco"],
            ["en-US", "de"],
            [],
            ["en-US", "fr", "sco"],
        ),
        (
            # Don't use CMS + Django Fallback
            ["en-US", "fr", "sco"],
            [],
            ["en-US", "de"],
            ["en-US", "fr", "sco"],
        ),
    ),
)
def test_get_locale_options(rf, translations_locales, cms_locales, django_locales, expected):
    native_translations = get_translations_native_names(translations_locales)
    native_expected = get_translations_native_names(expected)
    request = rf.get("/dummy/path/")

    if cms_locales is not None:
        request._locales_available_via_cms = cms_locales

    if django_locales is not None:
        request._locales_for_django_fallback_view = django_locales

    assert native_expected == helpers.get_locale_options(
        request=request,
        translations=native_translations,
    )


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX", "es-CL": "es-MX", "pt-PT": "pt-BR"})
def test_get_locale_options_adds_alias_locales_for_fluent_pages(rf):
    """Alias locales are added when their fallback canonical locale is in translations.

    For pure Fluent pages, translations only reflects FTL-active locales (e.g. es-MX,
    pt-BR) and does not include alias locales (es-AR, es-CL, pt-PT). This function
    expands the available set so that hreflang and the language switcher include
    alias locales pointing to their own URLs.
    """
    # Simulate a Fluent page that has es-MX and pt-BR — but not es-AR, es-CL, or pt-PT.
    translations_locales = ["en-US", "es-MX", "pt-BR"]
    native_translations = get_translations_native_names(translations_locales)
    request = rf.get("/dummy/path/")

    result = helpers.get_locale_options(request=request, translations=native_translations)

    # es-AR and es-CL should be added (their fallback es-MX is present).
    assert "es-AR" in result
    assert "es-CL" in result
    # pt-PT should be added (its fallback pt-BR is present).
    assert "pt-PT" in result
    # Original locales must still be present.
    assert "en-US" in result
    assert "es-MX" in result
    assert "pt-BR" in result


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX", "es-CL": "es-MX"})
def test_get_locale_options_does_not_add_alias_when_canonical_absent(rf):
    """Alias locales are NOT added when their fallback canonical locale is absent."""
    # es-MX is not in translations — es-AR and es-CL should not be added.
    translations_locales = ["en-US", "fr"]
    native_translations = get_translations_native_names(translations_locales)
    request = rf.get("/dummy/path/")

    result = helpers.get_locale_options(request=request, translations=native_translations)

    # es-AR and es-CL should NOT be added, since their fallback (es-MX) is NOT present.
    assert "es-AR" not in result
    assert "es-CL" not in result
    # The translations_locales should be in the results.
    assert "en-US" in result
    assert "fr" in result


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_get_locale_options_does_not_double_add_alias_already_present(rf):
    """Alias locales are not duplicated when already present (e.g. from CMS path)."""
    # Simulate CMS page where get_locales_for_cms_page() already added es-AR.
    translations_locales = ["en-US", "es-MX", "es-AR"]
    native_translations = get_translations_native_names(translations_locales)
    request = rf.get("/dummy/path/")

    result = helpers.get_locale_options(request=request, translations=native_translations)

    assert len(result) == len(translations_locales)
    for key in translations_locales:
        assert list(result).count(key) == 1  # no duplicate
