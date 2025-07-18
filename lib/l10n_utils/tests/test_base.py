# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from unittest.mock import ANY, Mock, call, patch

from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

import pytest
from django_jinja.backend import Jinja2
from markus.testing import MetricsMock

from lib import l10n_utils
from springfield.base.i18n import get_best_language, split_path_and_normalize_language

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")
TEMPLATE_DIRS = (os.path.join(ROOT, "templates"),)
jinja_env = Jinja2.get_default()


@patch.object(jinja_env.env.loader, "searchpath", TEMPLATE_DIRS)
@override_settings(
    ROOT=ROOT,
    DEV=False,
    ROOT_URLCONF="lib.l10n_utils.tests.test_files.urls",
)
class TestRender(TestCase):
    def _test(self, path, template, locale, accept_lang, status, destination=None, active_locales=None, add_active_locales=None):
        request = RequestFactory().get(path)
        if accept_lang:
            request.META["HTTP_ACCEPT_LANGUAGE"] = accept_lang

        locale_from_path, _subpath, _lang_code_changed = split_path_and_normalize_language(request.path)
        assert not _lang_code_changed, "Did not expect lang code to change"

        request.locale = locale_from_path or get_best_language(accept_lang)

        ctx = {}
        if active_locales:
            ctx["active_locales"] = active_locales

        if add_active_locales:
            ctx["add_active_locales"] = add_active_locales

        with MetricsMock() as mm:
            response = l10n_utils.render(request, template, ctx)

            if status == 302:
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], destination)
                self.assertEqual(response["Vary"], "Accept-Language")
                mm.assert_incr_once("locale.redirect", tags=[f"from_locale:{locale_from_path or 'none'}", f"to_locale:{destination.split('/')[1]}"])

            elif status == 404:
                self.assertEqual(response.status_code, 404)
                mm.assert_not_incr("locale.redirect")
            else:
                self.assertEqual(response.status_code, 200)
                mm.assert_not_incr("locale.redirect")
                if path == "/":
                    self.assertEqual(response["Vary"], "Accept-Language")

    def test_no_accept_language_header(self):
        template = "firefox/download.html"
        locales = ["en-US", "en-GB", "fr", "es-ES"]

        # Test no accept language header and locale-less root path returns 200.
        # This is a special case where we render the 404-locale.html template at /
        self._test("/", template, "", "", 200, active_locales=locales)

        # Test no accept language header and locale-less path returns 302.
        self._test("/download/", template, "", "", 302, "/en-US/download/", active_locales=locales)

        # Test that a locale+path and no accept language header returns 200 as long as the locales are supported.
        self._test("/en-US", template, "", "", 302, "/en-US/", active_locales=locales)
        self._test("/en-US/", template, "", "", 200, active_locales=locales)
        self._test("/en-US/download/", template, "", "", 200, active_locales=locales)
        self._test("/en-GB/download/", template, "", "", 200, active_locales=locales)
        self._test("/fr/download/", template, "", "", 200, active_locales=locales)
        self._test("/es-ES/download/", template, "", "", 200, active_locales=locales)
        self._test("/de/download/", template, "", "", 302, "/en-US/download/", active_locales=locales)

        # Test that a path in the `SUPPORTED_NONLOCALES` doesn't 404.
        self._test("/robots.txt", template, "", "", 200, active_locales=locales)
        self._test("/all-urls-global.xml", template, "", "", 200, active_locales=locales)

        # Test that a path in the `SUPPORTED_LOCALE_IGNORE` works both with and without locale in the path.
        self._test("/all-urls.xml", template, "", "", 200, active_locales=locales)
        self._test("/en-US/all-urls.xml", template, "", "", 200, active_locales=locales)
        self._test("/fr/all-urls.xml", template, "", "", 200, active_locales=locales)

    def test_with_accept_language_header(self):
        template = "firefox/download.html"
        locales = ["en-US", "en-GB", "fr", "es-ES"]

        # Test with accept language header and locale-less root path returns 302.
        self._test("/", template, "", "en-us", 302, "/en-US/", active_locales=locales)
        # Test with accept language header of unsupported locale and locale-less root path returns 302.
        self._test("/", template, "", "ach", 302, "/en-US/", active_locales=locales)
        # Test with accept language header and locale-less path returns 302.
        self._test("/download/", template, "", "en-us", 302, "/en-US/download/", active_locales=locales)
        # Test with accept language header of unsupported locale and locale-less path returns 302.
        self._test("/download/", template, "", "ach", 302, "/en-US/download/", active_locales=locales)

    def test_firefox(self):
        path = "/download/"
        template = "firefox/download.html"
        locales = ["en-US", "en-GB", "fr", "es-ES"]

        # No locale changes needed when we're given a valid locale
        self._test(path, template, "en-US", "en-us,en;q=0.5", 302, "/en-US/download/", active_locales=locales)

        # en-GB is activated on /download/
        self._test(path, template, "en-GB", "en-gb,en;q=0.5", 302, "/en-GB/download/", active_locales=locales)

        # fr-FR should be treated as fr
        self._test(path, template, "fr-FR", "fr-fr", 302, "/fr/download/", active_locales=locales)

        # Should fallback to the user's second preferred language
        self._test(path, template, "zu", "zu,fr;q=0.7,en;q=0.3", 302, "/fr/download/", active_locales=locales)

        # Should fallback to one of the site's fallback languages
        self._test(path, template, "es-CL", "es-CL,es;q=0.7,en;q=0.3", 302, "/es-ES/download/", active_locales=locales)

        # Should use the user's base language (en-CA -> en) if no exact matches
        self._test(path, template, "en-CA", "en-CA,fr", 302, "/en-US/download/", active_locales=locales)

    def test_add_active_locales(self):
        # expect same results as above, but with locales from `add_active_locales`
        path = "/download/"
        template = "firefox/download.html"
        locales = ["en-US", "en-GB", "fr", "es-ES"]

        # No locale changes needed when we're given a valid locale
        self._test(path, template, "en-US", "en-us,en;q=0.5", 302, "/en-US/download/", add_active_locales=locales)

        # en-GB is activated on /firefox/download/
        self._test(path, template, "en-GB", "en-gb,en;q=0.5", 302, "/en-GB/download/", add_active_locales=locales)

        # fr-FR should be treated as fr
        self._test(path, template, "fr-FR", "fr-fr", 302, "/fr/download/", add_active_locales=locales)

        # Should fallback to the user's second preferred language
        self._test(path, template, "zu", "zu,fr;q=0.7,en;q=0.3", 302, "/fr/download/", add_active_locales=locales)

        # Should fallback to one of the site's fallback languages
        self._test(path, template, "es-CL", "es-CL,es;q=0.7,en;q=0.3", 302, "/es-ES/download/", add_active_locales=locales)

    def test_ftl_files_unmodified(self):
        """A list passed to the ftl_files parameter should not be modified in place"""
        ftl_files = ["dude", "walter"]
        path = "/download/"
        template = "firefox/download.html"
        req = RequestFactory().get(path)
        l10n_utils.render(req, template, ftl_files=ftl_files)
        assert ftl_files == ["dude", "walter"]

    @patch.object(l10n_utils, "django_render")
    @patch.object(l10n_utils, "ftl_active_locales")
    def test_activation_files(self, fal_mock, dr_mock):
        ftl_files = ["dude", "walter"]
        path = "/download/"
        template = "firefox/download.html"
        activation_files = ftl_files + [template]
        req = RequestFactory().get(path)
        l10n_utils.render(req, template, activation_files=activation_files)
        fal_mock.assert_has_calls(
            [
                call("dude"),
                call("walter"),
            ],
            any_order=True,
        )


class TestGetAcceptLanguages(TestCase):
    def _test(self, accept_lang, list):
        request = RequestFactory().get("/")
        request.META["HTTP_ACCEPT_LANGUAGE"] = accept_lang
        self.assertEqual(l10n_utils.get_accept_languages(request), list)

    def test_valid_lang_codes(self):
        """
        Should return a list of valid lang codes
        """
        self._test("fr-FR", ["fr-fr"])
        self._test("en-us,en;q=0.5", ["en-us", "en"])
        self._test("pt-pt,fr;q=0.8,it-it;q=0.5,de;q=0.3", ["pt-pt", "fr", "it-it", "de"])
        self._test("ja-JP-mac,ja-JP;q=0.7,ja;q=0.3", ["ja-jp-mac", "ja-jp", "ja"])
        self._test("foo,bar;q=0.5", ["foo", "bar"])
        # Verify the return lang codes are ordered by rank.
        self._test("de;q=0.5,en-us", ["en-us", "de"])

    def test_invalid_lang_codes(self):
        """
        Should return a list of valid lang codes or an empty list
        """
        self._test("", [])
        self._test("en_us,en*;q=0.5", [])
        self._test("Chinese,zh-cn;q=0.5", ["chinese", "zh-cn"])


@patch.object(l10n_utils, "render")
class TestL10nTemplateView(TestCase):
    def setUp(self):
        self.req = RequestFactory().get("/")

    def test_post(self, render_mock):
        view = l10n_utils.L10nTemplateView.as_view(template_name="post.html", ftl_files="dude")
        resp = view(RequestFactory().post("/"))
        self.assertEqual(resp.status_code, 405)

    def test_ftl_files(self, render_mock):
        view = l10n_utils.L10nTemplateView.as_view(template_name="dude.html", ftl_files="dude")
        view(self.req)
        render_mock.assert_called_with(self.req, ["dude.html"], ANY, ftl_files="dude", activation_files=None)

    def test_ftl_files_map(self, render_mock):
        view = l10n_utils.L10nTemplateView.as_view(template_name="dude.html", ftl_files_map={"dude.html": "dude"})
        view(self.req)
        render_mock.assert_called_with(self.req, ["dude.html"], ANY, ftl_files="dude", activation_files=None)
        # no match means no FTL files
        view = l10n_utils.L10nTemplateView.as_view(template_name="dude.html", ftl_files_map={"donny.html": "donny"})
        view(self.req)
        render_mock.assert_called_with(self.req, ["dude.html"], ANY, ftl_files=None, activation_files=None)

    @patch.object(l10n_utils, "ftl_file_is_active")
    def test_old_template_name(self, is_active_mock, render_mock):
        is_active_mock.return_value = True
        view = l10n_utils.L10nTemplateView.as_view(
            template_name="dude.html", old_template_name="old_dude.html", ftl_files_map={"dude.html": "dude", "old_dude.html": "old_dude"}
        )
        view(self.req)
        render_mock.assert_called_with(self.req, ["dude.html"], ANY, ftl_files="dude", activation_files=None)
        # when not active should use old template
        is_active_mock.return_value = False
        view = l10n_utils.L10nTemplateView.as_view(
            template_name="dude.html", old_template_name="old_dude.html", ftl_files_map={"dude.html": "dude", "old_dude.html": "old_dude"}
        )
        view(self.req)
        render_mock.assert_called_with(self.req, ["old_dude.html"], ANY, ftl_files="old_dude", activation_files=None)

    def test_ftl_activations(self, render_mock):
        view = l10n_utils.L10nTemplateView.as_view(template_name="dude.html", ftl_files="dude", activation_files=["dude", "donny"])
        view(self.req)
        render_mock.assert_called_with(self.req, ["dude.html"], ANY, ftl_files="dude", activation_files=["dude", "donny"])


@pytest.mark.parametrize(
    "translations, accept_languages, expected",
    (
        # Anything with a 'en-US' translation and 'en' root accept languages, goes to 'en-US'.
        (["en-US"], ["en-US"], "en-US"),
        (["en-US"], ["en-CA"], "en-US"),
        (["en-US"], ["en"], "en-US"),
        (["en-US", "de"], ["en-GB"], "en-US"),
        # Anything with a 'en-US' translation and unsupported translations, returns 'en-US'.
        (["en-US"], ["zu"], "en-US"),
        (["en-US"], ["fr"], "en-US"),
        (["en-US", "de"], ["fr"], "en-US"),
        # The user's prioritized accept language should be chosen first.
        (["en-US", "de"], ["de", "en-US"], "de"),
        (["en-US", "de", "fr"], ["fr", "de"], "fr"),
        (["en-US", "de", "fr"], ["en-CA", "fr", "de"], "en-US"),
        # A request for only inactive translations should return default.
        (["am", "an", "en-US"], ["mk", "gu-IN"], "en-US"),
        # "am" is not a valid language in the list of PROD_LANGUAGES
        (["am", "an"], ["mk", "gu-IN"], "an"),
    ),
)
@patch.object(
    l10n_utils,
    "language_url_map_with_fallbacks",
    Mock(return_value={"an": "an", "de": "de", "en": "en-US", "en-us": "en-US", "fr": "fr"}),
)
def test_get_best_translation(translations, accept_languages, expected):
    assert l10n_utils.get_best_translation(translations, accept_languages) == expected


@pytest.mark.parametrize(
    "translations, accept_languages, expected",
    (
        # Anything with a 'en-US' translation and 'en' root accept languages, goes to 'en-US'.
        (["en-US"], ["en-US"], "en-US"),
        (["en-US"], ["en-CA"], "en-US"),
        (["en-US"], ["en"], "en-US"),
        (["en-US", "de"], ["en-GB"], "en-US"),
        # Anything with a 'en-US' translation and unsupported translations, returns `None`.
        (["en-US"], ["zu"], None),
        (["en-US"], ["fr"], None),
        (["en-US", "de"], ["fr"], None),
        # The user's prioritized accept language should be chosen first.
        (["en-US", "de"], ["de", "en-US"], "de"),
        (["en-US", "de", "fr"], ["fr", "de"], "fr"),
        (["en-US", "de", "fr"], ["en-CA", "fr", "de"], "en-US"),
        # A request for only inactive translations should return `None`.
        (["am", "an", "en-US"], ["mk", "gu-IN"], None),
        # "am" is not a valid language in the list of PROD_LANGUAGES
        (["am", "an"], ["mk", "gu-IN"], None),
    ),
)
@patch.object(
    l10n_utils,
    "language_url_map_with_fallbacks",
    Mock(return_value={"an": "an", "de": "de", "en": "en-US", "en-us": "en-US", "fr": "fr"}),
)
def test_get_best_translation__strict(translations, accept_languages, expected):
    # Strict is used for the root path, to return the list of localized home pages for bots.
    assert l10n_utils.get_best_translation(translations, accept_languages, strict=True) == expected
