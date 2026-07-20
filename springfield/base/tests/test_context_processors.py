# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings

import jinja2

from lib.l10n_utils import translation
from springfield.base.context_processors import i18n


class TestContext(TestCase):
    def setUp(self):
        translation.activate("en-US")
        self.factory = RequestFactory()
        translation.activate("en-US")

    def render(self, content, request=None):
        if not request:
            request = self.factory.get("/")
        tpl = jinja2.Template(content)
        return render_to_string(tpl, request=request)

    def test_request(self):
        assert self.render("{{ request.path }}") == "/"

    def test_settings(self):
        assert self.render("{{ settings.LANGUAGE_CODE }}") == "en-US"

    def test_languages(self):
        assert self.render("{{ LANGUAGES[-1][1] }}") == settings.LANGUAGES[-1][1]

    def test_lang_setting(self):
        assert self.render("{{ LANG }}") == "en-US"

    def test_lang_dir(self):
        assert self.render("{{ DIR }}") == "ltr"

    def test_geo_header(self):
        """Country code from request header should work"""
        req = self.factory.get("/", HTTP_CF_IPCOUNTRY="de")
        assert self.render("{{ country_code }}", req) == "DE"

    @override_settings(DEV=False)
    def test_geo_no_header(self):
        """Country code when header absent should be None"""
        req = self.factory.get("/")
        assert self.render("{{ country_code }}", req) == "None"

    def test_geo_param(self):
        """Country code from header should be overridden by query param
        for pre-prod domains."""
        req = self.factory.get("/", data={"geo": "fr"}, HTTP_CF_IPCOUNTRY="de")
        assert self.render("{{ country_code }}", req) == "FR"

        # should use header if at prod domain
        req = self.factory.get("/", data={"geo": "fr"}, HTTP_CF_IPCOUNTRY="de", HTTP_HOST="www.firefox.com")
        assert self.render("{{ country_code }}", req) == "DE"

    @override_settings(DEV=False)
    def test_invalid_geo_param(self):
        req = self.factory.get("/", data={"geo": "france"}, HTTP_CF_IPCOUNTRY="de")
        assert self.render("{{ country_code }}", req) == "DE"

        req = self.factory.get("/", data={"geo": ""}, HTTP_CF_IPCOUNTRY="de")
        assert self.render("{{ country_code }}", req) == "DE"

        req = self.factory.get("/", data={"geo": "france"})
        assert self.render("{{ country_code }}", req) == "None"


class TestI18nContextProcessor(TestCase):
    """Tests for the CANONICAL_LANG addition to the i18n() context processor."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_canonical_lang_equals_lang_for_normal_request(self):
        """On a normal request with no content_locale, CANONICAL_LANG == LANG."""
        translation.activate("en-US")
        request = self.factory.get("/en-US/some/page/")

        ctx = i18n(request)

        assert ctx["CANONICAL_LANG"] == "en-US"
        assert ctx["LANG"] == "en-US"

    def test_canonical_lang_is_content_locale_when_set(self):
        """When the middleware sets request.content_locale, CANONICAL_LANG reflects it.

        Simulates: user visits /es-AR/page/ (alias locale), middleware serves
        es-MX content and sets request.content_locale = 'es-MX'.
        LANG stays as the URL-facing locale (es-AR); CANONICAL_LANG is es-MX.
        """
        translation.activate("es-AR")
        request = self.factory.get("/es-AR/some/page/")
        request.content_locale = "es-MX"

        ctx = i18n(request)

        assert ctx["LANG"] == "es-AR"
        assert ctx["CANONICAL_LANG"] == "es-MX"
