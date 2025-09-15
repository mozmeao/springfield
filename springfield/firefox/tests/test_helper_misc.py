# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# coding: utf-8

import os.path
from datetime import datetime
from unittest.mock import patch

from django.conf import settings
from django.test.client import RequestFactory
from django.test.utils import override_settings

import pytest
from bs4 import BeautifulSoup
from django_jinja.backend import Jinja2
from markupsafe import Markup

from springfield.base.templatetags.helpers import static
from springfield.base.tests import TestCase
from springfield.firefox.templatetags import misc

TEST_FILES_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")
TEST_L10N_MEDIA_PATH = os.path.join(TEST_FILES_ROOT, "media", "%s", "l10n")

TEST_FXA_ENDPOINT = "https://accounts.firefox.com/"

TEST_VPN_ENDPOINT = "https://vpn.mozilla.org/"
TEST_VPN_PRODUCT_ID = "prod_FvnsFHIfezy3ZI"
TEST_VPN_SUBSCRIPTION_URL = "https://accounts.firefox.com/"

TEST_VPN_PLAN_ID_MATRIX = {
    "chf": {
        "de": {
            "12-month": {"id": "price_1J5JssJNcmPzuWtR616BH4aU", "price": "CHF 5.99", "total": "CHF 71.88", "saving": 45},
            "6-month": {"id": "price_1J5JtWJNcmPzuWtRMd2siphH", "price": "CHF 7.99", "total": "CHF 47.94", "saving": 27},
            "monthly": {"id": "price_1J5Ju3JNcmPzuWtR3GpNYSWj", "price": "CHF 10.99", "total": None, "saving": None},
        },
        "fr": {
            "12-month": {"id": "price_1J5JunJNcmPzuWtRo9dLxn6M", "price": "CHF 5.99", "total": "CHF 71.88", "saving": 45},
            "6-month": {"id": "price_1J5JvLJNcmPzuWtRayB4d7Ij", "price": "CHF 7.99", "total": "CHF 47.94", "saving": 27},
            "monthly": {"id": "price_1J5JvjJNcmPzuWtR3wwy1dcR", "price": "CHF 10.99", "total": None, "saving": None},
        },
        "it": {
            "12-month": {"id": "price_1J5JwWJNcmPzuWtRgrx5fjOc", "price": "CHF 5.99", "total": "CHF 71.88", "saving": 45},
            "6-month": {"id": "price_1J5JwvJNcmPzuWtRH2HuhWM5", "price": "CHF 7.99", "total": "CHF 47.94", "saving": 27},
            "monthly": {"id": "price_1J5JxGJNcmPzuWtRrp5e1SUB", "price": "CHF 10.99", "total": None, "saving": None},
        },
    },
    "euro": {
        "de": {
            "12-month": {"id": "price_1IgwblJNcmPzuWtRynC7dqQa", "price": "4,99 €", "total": "59,88 €", "saving": 50},
            "6-month": {"id": "price_1IgwaHJNcmPzuWtRuUfSR4l7", "price": "6,99 €", "total": "41,94 €", "saving": 30},
            "monthly": {"id": "price_1IgwZVJNcmPzuWtRg9Wssh2y", "price": "9,99‎ €", "total": None, "saving": None},
        },
        "en": {
            "12-month": {
                "id": "price_1JcdvBJNcmPzuWtROLbEH9d2",
                "price": "4,99 €",
                "total": "59,88 €",
                "saving": 50,
            },
            "6-month": {
                "id": "price_1Jcdu8JNcmPzuWtRK6u5TUoZ",
                "price": "6,99 €",
                "total": "41,94 €",
                "saving": 30,
            },
            "monthly": {
                "id": "price_1JcdsSJNcmPzuWtRGF9Y5TMJ",
                "price": "9,99‎ €",
                "total": None,
                "saving": None,
            },
        },
        "es": {
            "12-month": {"id": "price_1J5JCdJNcmPzuWtRrvQMFLlP", "price": "4,99 €", "total": "59,88 €", "saving": 50},
            "6-month": {"id": "price_1J5JDFJNcmPzuWtRrC4IeXTs", "price": "6,99 €", "total": "41,94 €", "saving": 30},
            "monthly": {"id": "price_1J5JDgJNcmPzuWtRqQtIbktk", "price": "9,99‎ €", "total": None, "saving": None},
        },
        "fr": {
            "12-month": {"id": "price_1IgnlcJNcmPzuWtRjrNa39W4", "price": "4,99 €", "total": "59,88 €", "saving": 50},
            "6-month": {"id": "price_1IgoxGJNcmPzuWtRG7l48EoV", "price": "6,99 €", "total": "41,94 €", "saving": 30},
            "monthly": {"id": "price_1IgowHJNcmPzuWtRzD7SgAYb", "price": "9,99‎ €", "total": None, "saving": None},
        },
        "it": {
            "12-month": {"id": "price_1J4owvJNcmPzuWtRomVhWQFq", "price": "4,99 €", "total": "59,88 €", "saving": 50},
            "6-month": {"id": "price_1J5J7eJNcmPzuWtRKdQi4Tkk", "price": "6,99 €", "total": "41,94 €", "saving": 30},
            "monthly": {"id": "price_1J5J6iJNcmPzuWtRK5zfoguV", "price": "9,99‎ €", "total": None, "saving": None},
        },
        "nl": {
            "12-month": {"id": "price_1J5JRGJNcmPzuWtRXwXA84cm", "price": "4,99 €", "total": "59,88 €", "saving": 50},
            "6-month": {"id": "price_1J5JRmJNcmPzuWtRyFGj0tkN", "price": "6,99 €", "total": "41,94 €", "saving": 30},
            "monthly": {"id": "price_1J5JSkJNcmPzuWtR54LPH2zi", "price": "9,99‎ €", "total": None, "saving": None},
        },
    },
    "usd": {
        "en": {
            "12-month": {"id": "price_1Iw85dJNcmPzuWtRyhMDdtM7", "price": "US$4.99", "total": "US$59.88", "saving": 50},
            "6-month": {"id": "price_1Iw87cJNcmPzuWtRefuyqsOd", "price": "US$7.99", "total": "US$47.94", "saving": 20},
            "monthly": {"id": "price_1Iw7qSJNcmPzuWtRMUZpOwLm", "price": "US$9.99", "total": None, "saving": None},
        }
    },
}

TEST_VPN_VARIABLE_PRICING = {
    "AT": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["de"],
    },
    "BE": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["nl"],
        "de": TEST_VPN_PLAN_ID_MATRIX["euro"]["de"],
        "fr": TEST_VPN_PLAN_ID_MATRIX["euro"]["fr"],
    },
    "CH": {
        "default": TEST_VPN_PLAN_ID_MATRIX["chf"]["de"],
        "fr": TEST_VPN_PLAN_ID_MATRIX["chf"]["fr"],
        "it": TEST_VPN_PLAN_ID_MATRIX["chf"]["it"],
    },
    "DE": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["de"],
    },
    "ES": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["es"],
    },
    "FR": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["fr"],
    },
    "IE": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["en"],
    },
    "IT": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["it"],
    },
    "NL": {
        "default": TEST_VPN_PLAN_ID_MATRIX["euro"]["nl"],
    },
    "US": {
        "default": TEST_VPN_PLAN_ID_MATRIX["usd"]["en"],
    },
}

jinja_env = Jinja2.get_default()


# Where should this function go?
def render(s, context=None):
    t = jinja_env.from_string(s)
    return t.render(context or {})


def test_convert_to_high_res():
    assert misc.convert_to_high_res("/media/img/the.dude.png") == "/media/img/the.dude-high-res.png"
    assert misc.convert_to_high_res("/media/thats-a-bummer-man.jpg") == "/media/thats-a-bummer-man-high-res.jpg"


@patch("springfield.firefox.templatetags.misc._l10n_media_exists")
@patch("django.conf.settings.LANGUAGE_CODE", "en-US")
class TestImgL10n(TestCase):
    rf = RequestFactory()

    def _render(self, locale, url):
        req = self.rf.get("/")
        req.locale = locale
        return render(f"{{{{ l10n_img('{url}') }}}}", {"request": req})

    def test_works_for_default_lang(self, media_exists_mock):
        """Should output correct path for default lang always."""
        media_exists_mock.return_value = True
        assert self._render("en-US", "dino/head.png") == static("img/l10n/en-US/dino/head.png")
        assert self._render("en-US", "img/dino/head.png") == static("img/l10n/en-US/dino/head.png")

        assert self._render("en-US", "dino/does-not-exist.png") == static("img/l10n/en-US/dino/does-not-exist.png")

    def test_works_for_other_lang(self, media_exists_mock):
        """Should use the request lang if file exists."""
        media_exists_mock.return_value = True
        assert self._render("de", "dino/head.png") == static("img/l10n/de/dino/head.png")
        assert self._render("de", "img/dino/head.png") == static("img/l10n/de/dino/head.png")

    def test_defaults_when_lang_file_missing(self, media_exists_mock):
        """Should use default lang when file doesn't exist for lang."""
        media_exists_mock.return_value = False
        assert self._render("is", "dino/head.png") == static("img/l10n/en-US/dino/head.png")

    def test_latam_spanishes_fallback_to_european_spanish(self, media_exists_mock):
        """Should use es-ES image when file doesn't exist for lang."""
        media_exists_mock.side_effect = [False, True]
        assert self._render("es-AR", "dino/head.png") == static("img/l10n/es-ES/dino/head.png")

        media_exists_mock.reset_mock()
        media_exists_mock.side_effect = [False, True]
        assert self._render("es-CL", "dino/head.png") == static("img/l10n/es-ES/dino/head.png")

        media_exists_mock.reset_mock()
        media_exists_mock.side_effect = [False, True]
        assert self._render("es-MX", "dino/head.png") == static("img/l10n/es-ES/dino/head.png")

        media_exists_mock.reset_mock()
        media_exists_mock.side_effect = [False, True]
        assert self._render("es", "dino/head.png") == static("img/l10n/es-ES/dino/head.png")

    def test_file_not_checked_for_default_lang(self, media_exists_mock):
        """
        Should not check filesystem for default lang, but should for others.
        """
        assert self._render("en-US", "dino/does-not-exist.png") == static("img/l10n/en-US/dino/does-not-exist.png")
        assert not media_exists_mock.called

        self._render("is", "dino/does-not-exist.png")
        media_exists_mock.assert_called_once_with("img", "is", "dino/does-not-exist.png")


@override_settings(DEBUG=False)
@patch("springfield.firefox.templatetags.misc._l10n_media_exists")
class TestL10nCSS(TestCase):
    rf = RequestFactory()
    static_url_dev = "/static/"
    cdn_url = "//springfield.cdn.mozilla.net"
    static_url_prod = cdn_url + static_url_dev
    markup = '<link rel="stylesheet" media="screen,projection,tv" href="%scss/l10n/%s/intl.css">'

    def _render(self, locale):
        req = self.rf.get("/")
        req.locale = locale
        return render("{{ l10n_css() }}", {"request": req})

    @override_settings(DEV=True)
    @patch("django.contrib.staticfiles.storage.staticfiles_storage.base_url", static_url_dev)
    def test_dev_when_css_file_exists(self, media_exists_mock):
        """Should output a path to the CSS file if exists."""
        media_exists_mock.return_value = True
        assert self._render("de") == self.markup % (self.static_url_dev, "de")
        assert self._render("es-ES") == self.markup % (self.static_url_dev, "es-ES")

    @override_settings(DEV=True)
    def test_dev_when_css_file_missing(self, media_exists_mock):
        """Should output nothing if the CSS file is missing."""
        media_exists_mock.return_value = False
        assert self._render("en-US") == ""
        assert self._render("fr") == ""

    @override_settings(DEV=False)
    @patch("django.contrib.staticfiles.storage.staticfiles_storage.base_url", static_url_prod)
    def test_prod_when_css_file_exists(self, media_exists_mock):
        """Should output a path to the CSS file if exists."""
        media_exists_mock.return_value = True
        assert self._render("de") == self.markup % (self.static_url_prod, "de")
        assert self._render("es-ES") == self.markup % (self.static_url_prod, "es-ES")

    @override_settings(DEV=False)
    def test_prod_when_css_file_missing(self, media_exists_mock):
        """Should output nothing if the CSS file is missing."""
        media_exists_mock.return_value = False
        assert self._render("en-US") == ""
        assert self._render("fr") == ""


class TestDonateUrl(TestCase):
    rf = RequestFactory()

    def _render(self, location=""):
        req = self.rf.get("/")
        return render(f"{{{{ donate_url(location='{location}') }}}}", {"request": req})

    def test_donate_url_with_location_param(self):
        """Should include location parameter when supplied"""
        assert self._render(location="moco-donate-footer") == ("https://foundation.mozilla.org/?form=moco-donate-footer")

    def test_donate_url_no_params(self):
        """Should link to /donate/ when no location parameter is supplied"""
        assert self._render() == ("https://foundation.mozilla.org/donate/")


class TestMozillaInstagramUrl(TestCase):
    rf = RequestFactory()

    def _render(self, locale):
        req = self.rf.get("/")
        req.locale = locale
        return render("{{ mozilla_instagram_url() }}", {"request": req})

    def test_mozilla_instagram_url_no_locale(self):
        """No locale, fallback to default account"""
        assert self._render("") == "https://www.instagram.com/mozilla/"

    def test_mozilla_instagram_url_english(self):
        """en-US locale, default account"""
        assert self._render("en-US") == "https://www.instagram.com/mozilla/"

    def test_mozilla_instagram_url_german(self):
        """de locale, a local account"""
        assert self._render("de") == "https://www.instagram.com/mozilla_deutschland/"

    def test_mozilla_instagram_url_other_locale(self):
        """No account for locale, fallback to default account"""
        assert self._render("es-AR") == "https://www.instagram.com/mozilla/"


@override_settings(STATIC_URL="/media/")
class TestRespImg(TestCase):
    rf = RequestFactory()

    def _render(self, url, srcset=None, sizes=None, optional_attributes=None):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(f"{{{{ resp_img('{url}', {srcset}, {sizes}, {optional_attributes}) }}}}", {"request": req})

    def _render_l10n(self, url):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(f"{{{{ l10n_img('{url}') }}}}", {"request": req})

    def test_resp_img_no_optional_attributes(self):
        """Should return expected markup without optional attributes"""
        expected = (
            '<img src="/media/img/panda-500.png" '
            'srcset="/media/img/panda-500.png 500w,/media/img/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" alt="">'
        )
        markup = self._render(
            "img/panda-500.png",
            {"img/panda-500.png": "500w", "img/panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
        )
        self.assertEqual(markup, expected)

    def test_resp_img_absolute_urls(self):
        """Should return expected markup when absolute image URLs are passed"""
        expected = (
            '<img src="https://www.example.com/img/panda-500.png" '
            'srcset="https://www.example.com/img/panda-500.png 500w,https://www.example.com/img/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" alt="">'
        )
        markup = self._render(
            "https://www.example.com/img/panda-500.png",
            {"https://www.example.com/img/panda-500.png": "500w", "https://www.example.com/img/panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
        )
        self.assertEqual(markup, expected)

    def test_resp_img_with_optional_attributes(self):
        """Should return expected markup with optional attributes"""
        expected = (
            '<img loading="lazy" src="/media/img/panda-500.png" '
            'srcset="/media/img/panda-500.png 500w,/media/img/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" '
            'alt="Red Panda" class="panda-hero">'
        )
        markup = self._render(
            "img/panda-500.png",
            {"img/panda-500.png": "500w", "img/panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
            {"class": "panda-hero", "alt": "Red Panda", "loading": "lazy"},
        )
        self.assertEqual(markup, expected)

    def test_resp_img_with_l10n(self):
        """Should return expected markup with l10n image path"""
        expected = (
            '<img src="/media/img/l10n/en-US/panda-500.png" '
            'srcset="/media/img/l10n/en-US/panda-500.png 500w,/media/img/l10n/en-US/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" alt="">'
        )
        markup = self._render(
            "panda-500.png",
            {"panda-500.png": "500w", "panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
            {"l10n": True},
        )
        self.assertEqual(markup, expected)

        expected = (
            '<img src="/media/img/l10n/en-US/panda-500.png" '
            'srcset="/media/img/l10n/en-US/panda-500.png 500w,/media/img/l10n/en-US/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" alt="">'
        )
        markup = self._render(
            "img/panda-500.png",
            {"img/panda-500.png": "500w", "img/panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
            {"l10n": True},
        )
        self.assertEqual(markup, expected)

    def test_resp_img_with_l10n_and_optional_attributes(self):
        """Should return expected markup with l10n image path"""
        expected = (
            '<img loading="lazy" src="/media/img/l10n/en-US/panda-500.png" '
            'srcset="/media/img/l10n/en-US/panda-500.png 500w,/media/img/l10n/en-US/panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)" '
            'alt="Red Panda" class="panda-hero">'
        )
        markup = self._render(
            "img/panda-500.png",
            {"img/panda-500.png": "500w", "img/panda-1000.png": "1000w"},
            {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
            {"l10n": True, "class": "panda-hero", "alt": "Red Panda", "loading": "lazy"},
        )
        self.assertEqual(markup, expected)

    def test_resp_img_srcset_without_sizes(self):
        """Should return expected markup when using srcset without sizes"""
        expected = '<img src="/media/img/panda.png" srcset="/media/img/panda-high-res.png 2x" alt="">'
        markup = self._render("img/panda.png", {"img/panda-high-res.png": "2x"})
        self.assertEqual(markup, expected)

    def test_resp_img_without_srcset_or_sizes(self):
        """Should return expected markup when using without srcset or sizes"""
        expected = '<img src="/media/img/panda.png" alt="">'
        markup = self._render("img/panda.png")
        self.assertEqual(markup, expected)


@override_settings(STATIC_URL="/media/")
class TestPicture(TestCase):
    rf = RequestFactory()

    def _render(self, url, sources, optional_attributes=None):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(f"{{{{ picture('{url}', {sources}, {optional_attributes}) }}}}", {"request": req})

    def test_picture_media_srcset_only(self):
        """Should return expected markup when specifying media and srcset"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" srcset="/media/img/panda-mobile.png">'
            '<source media="(min-width: 800px)" srcset="/media/img/panda-desktop.png">'
            '<img src="/media/img/panda-mobile.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/panda-mobile.png",
            [
                {"media": "(max-width: 799px)", "srcset": {"img/panda-mobile.png": "default"}},
                {"media": "(min-width: 800px)", "srcset": {"img/panda-desktop.png": "default"}},
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_absolute_urls(self):
        """Should return expected markup when absolute image urls are passed"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" srcset="https://www.example.com/img/panda-mobile.png">'
            '<source media="(min-width: 800px)" srcset="https://www.example.com/img/panda-desktop.png">'
            '<img src="https://www.example.com/img/panda-mobile.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "https://www.example.com/img/panda-mobile.png",
            [
                {"media": "(max-width: 799px)", "srcset": {"https://www.example.com/img/panda-mobile.png": "default"}},
                {"media": "(min-width: 800px)", "srcset": {"https://www.example.com/img/panda-desktop.png": "default"}},
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_media_multiple_srcset_sizes(self):
        """Should return expected markup when specifying media with multiple srcset and sizes"""
        expected = (
            "<picture>"
            '<source media="(prefers-reduced-motion: reduce)" '
            'srcset="/media/img/sleeping-panda-500.png 500w,/media/img/sleeping-panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)">'
            '<source media="(prefers-reduced-motion: no-preference)" '
            'srcset="/media/img/dancing-panda-500.gif 500w,/media/img/dancing-panda-1000.gif 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)">'
            '<img src="/media/img/dancing-panda-500.gif" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/dancing-panda-500.gif",
            [
                {
                    "media": "(prefers-reduced-motion: reduce)",
                    "srcset": {"img/sleeping-panda-500.png": "500w", "img/sleeping-panda-1000.png": "1000w"},
                    "sizes": {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
                },
                {
                    "media": "(prefers-reduced-motion: no-preference)",
                    "srcset": {"img/dancing-panda-500.gif": "500w", "img/dancing-panda-1000.gif": "1000w"},
                    "sizes": {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
                },
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_type_srcset_only(self):
        """Should return expected markup when specifying type and srcset"""
        expected = '<picture><source type="image/webp" srcset="/media/img/red-panda.webp"><img src="/media/img/red-panda.png" alt=""></picture>'
        markup = self._render("img/red-panda.png", [{"type": "image/webp", "srcset": {"img/red-panda.webp": "default"}}])
        self.assertEqual(markup, expected)

    def test_picture_type_media_srcset(self):
        """Should return expected markup when specifying type, media, and srcset"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" type="image/webp" srcset="/media/img/red-panda.webp">'
            '<source media="(max-width: 799px)" type="image/png" srcset="/media/img/red-panda.png">'
            '<img src="/media/img/red-panda.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/red-panda.png",
            [
                {"media": "(max-width: 799px)", "type": "image/webp", "srcset": {"img/red-panda.webp": "default"}},
                {"media": "(max-width: 799px)", "type": "image/png", "srcset": {"img/red-panda.png": "default"}},
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_type_srcset_sizes(self):
        """Should return expected markup when specifying type, srcset, and sizes"""
        expected = (
            "<picture>"
            '<source type="image/webp" srcset="/media/img/sleeping-panda-500.webp 500w,/media/img/sleeping-panda-1000.webp 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)">'
            '<source type="image/png" srcset="/media/img/sleeping-panda-500.png 500w,/media/img/sleeping-panda-1000.png 1000w" '
            'sizes="(min-width: 1000px) calc(50vw - 200px),calc(100vw - 50px)">'
            '<img src="/media/img/red-panda.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/red-panda.png",
            [
                {
                    "type": "image/webp",
                    "srcset": {"img/sleeping-panda-500.webp": "500w", "img/sleeping-panda-1000.webp": "1000w"},
                    "sizes": {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
                },
                {
                    "type": "image/png",
                    "srcset": {"img/sleeping-panda-500.png": "500w", "img/sleeping-panda-1000.png": "1000w"},
                    "sizes": {"(min-width: 1000px)": "calc(50vw - 200px)", "default": "calc(100vw - 50px)"},
                },
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_l10n_images(self):
        """Should return expected markup when specifying L10n images"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" srcset="/media/img/l10n/en-US/panda-mobile.png">'
            '<source media="(min-width: 800px)" srcset="/media/img/l10n/en-US/panda-desktop.png">'
            '<img src="/media/img/l10n/en-US/panda-mobile.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/panda-mobile.png",
            [
                {"media": "(max-width: 799px)", "srcset": {"img/panda-mobile.png": "default"}},
                {"media": "(min-width: 800px)", "srcset": {"img/panda-desktop.png": "default"}},
            ],
            {"l10n": True},
        )
        self.assertEqual(markup, expected)

    def test_picture_with_optional_height_and_width(self):
        """Should return expected markup with optional attributes"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" srcset="/media/img/panda-mobile.png" width="200" height="100">'
            '<source media="(min-width: 800px)" srcset="/media/img/panda-desktop.png" width="300">'
            '<img src="/media/img/panda-mobile.png" alt="">'
            "</picture>"
        )
        markup = self._render(
            "img/panda-mobile.png",
            [
                {"media": "(max-width: 799px)", "srcset": {"img/panda-mobile.png": "default"}, "width": "200", "height": "100"},
                {"media": "(min-width: 800px)", "srcset": {"img/panda-desktop.png": "default"}, "width": "300"},
            ],
        )
        self.assertEqual(markup, expected)

    def test_picture_with_optional_attributes(self):
        """Should return expected markup with optional attributes"""
        expected = (
            "<picture>"
            '<source media="(max-width: 799px)" srcset="/media/img/panda-mobile.png">'
            '<source media="(min-width: 800px)" srcset="/media/img/panda-desktop.png">'
            '<img loading="lazy" src="/media/img/panda-mobile.png" alt="Red Panda" class="panda-hero">'
            "</picture>"
        )
        markup = self._render(
            "img/panda-mobile.png",
            [
                {"media": "(max-width: 799px)", "srcset": {"img/panda-mobile.png": "default"}},
                {"media": "(min-width: 800px)", "srcset": {"img/panda-desktop.png": "default"}},
            ],
            {"alt": "Red Panda", "loading": "lazy", "class": "panda-hero"},
        )
        self.assertEqual(markup, expected)


class TestAbsoluteURLFilter(TestCase):
    rf = RequestFactory()
    static_url_dev = "/static/"
    static_url_prod = "//springfield.cdn.mozilla.net/static/"
    static_url_full = "https://springfield.cdn.mozilla.net/static/"
    image_path = "img/base/mozilla-256.jpg"
    inline_template = "{{ static('%s')|absolute_url }}" % image_path
    block_template = "{% filter absolute_url %}{% block page_image %}" + "{{ static('%s') }}" % image_path + "{% endblock %}{% endfilter %}"

    def _render(self, template):
        return render(template, {"request": self.rf.get("/")})

    @patch("django.contrib.staticfiles.storage.staticfiles_storage.base_url", static_url_dev)
    def test_image_dev(self):
        """Should return a fully qualified URL including a protocol"""
        expected = settings.CANONICAL_URL + self.static_url_dev + self.image_path
        assert self._render(self.inline_template) == expected
        assert self._render(self.block_template) == expected

    @patch("django.contrib.staticfiles.storage.staticfiles_storage.base_url", static_url_prod)
    def test_image_prod(self):
        """Should return a fully qualified URL including a protocol"""
        expected = "https:" + self.static_url_prod + self.image_path
        assert self._render(self.inline_template) == expected
        assert self._render(self.block_template) == expected

    @override_settings(DEV=False)
    def test_urls(self):
        """Should return a fully qualified URL including a protocol"""
        expected = "https://www.firefox.com/en-US/download/all/"
        assert misc.absolute_url("/en-US/download/all/") == expected
        assert misc.absolute_url("//www.firefox.com/en-US/download/all/") == expected
        assert misc.absolute_url("https://www.firefox.com/en-US/download/all/") == expected


@pytest.mark.parametrize(
    "html, cleaned",
    [
        ("pre <script>alert('oops')</script> post", "pre alert('oops') post"),
        ("pre <script>alert('oops') post", "pre alert('oops') post"),
        ("pre <style>body {background-color: red;}</style> post", "pre body {background-color: red;} post"),
        ("pre <div onclick='foo()'></div> post", "pre  post"),
        ("pre <p>foo &amp; bar</p> post", "pre foo & bar post"),
        ("pre <p>mid</p> post", "pre mid post"),
    ],
)
def test_bleach_tags(html, cleaned):
    s = misc.bleach_tags(html)
    assert s == cleaned, f"{s} != {cleaned}"


def test_attrs():
    context = {"elem": BeautifulSoup("<h1>Test</h1>", "lxml")}
    template = "{% do elem.select('h1')|htmlattr(class='dude', id='abides',) %}{{ elem | safe }}"
    assert render(template, context) == '<html><body><h1 class="dude" id="abides">Test</h1></body></html>'


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello, World!", "hello-world"),
        (" multiple---dash and  space ", "multiple-dash-and-space"),
        ("underscore_in-value", "underscore_in-value"),
        ("spam & eggs", "spam-eggs"),
        ("__strip__underscore-value___", "strip__underscore-value"),
    ],
)
def test_slugify(text, expected):
    template = "{{ '%s' | slugify }}" % text
    assert render(template) == expected


# from jingo


def test_f():
    s = render('{{ "{0} : {z}"|f("a", z="b") }}')
    assert s == "a : b"


def test_f_unicode():
    s = render('{{ "foo {0}"|f(bar) }}', {"bar": "bar\xe9"})
    assert s == "foo bar\xe9"
    s = render("{{ t|f(bar) }}", {"t": "\xe9 {0}", "bar": "baz"})
    assert s == "\xe9 baz"


format_string = "Hello <b>{0}</b>"
format_markup = Markup(format_string)
val_string = "<em>Steve</em>"
val_markup = Markup(val_string)


@pytest.mark.parametrize(
    "f, v",
    [
        (format_string, val_string),
        (format_string, val_markup),
        (format_markup, val_string),
        (format_markup, val_markup),
    ],
)
def test_f_markup(f, v):
    expect = "Hello &lt;b&gt;&lt;em&gt;Steve&lt;/em&gt;&lt;/b&gt;"
    s = render("{{ fmt|f(val) }}", {"fmt": f, "val": v})
    assert expect == s


def test_datetime():
    time = datetime(2009, 12, 25, 10, 11, 12)
    s = render("{{ d|datetime }}", {"d": time})
    assert s == "December 25, 2009"

    s = render('{{ d|datetime("%Y-%m-%d %H:%M:%S") }}', {"d": time})
    assert s == "2009-12-25 10:11:12"

    s = render("{{ None|datetime }}")
    assert s == ""


def test_datetime_unicode():
    fmt = "%Y 年 %m 月 %e 日"
    misc.datetime(datetime.now(), fmt)


def test_ifeq():
    eq_context = {"a": 1, "b": 1}
    neq_context = {"a": 1, "b": 2}

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', eq_context)
    assert s == "<b>something</b>"

    s = render('{{ a|ifeq(b, "<b>something</b>") }}', neq_context)
    assert s == ""


def test_csrf():
    s = render("{{ csrf() }}", {"csrf_token": "fffuuu"})
    csrf = '<input type="hidden" name="csrfmiddlewaretoken" value="fffuuu">'
    assert csrf in s


class TestAppStoreURL(TestCase):
    rf = RequestFactory()

    def _render(self, product, campaign, locale):
        req = self.rf.get("/")
        req.locale = locale
        return render(
            f"{{{{ app_store_url('{product}', '{campaign}') }}}}",
            {"request": req},
        )

    def test_firefox_app_store_url_no_locale(self):
        """No locale, fallback to default URL"""
        assert self._render("firefox", "", "") == "https://apps.apple.com/app/apple-store/id989804926?mz_pr=firefox_mobile"

    def test_firefox_app_store_url_default(self):
        """should fallback to default URL"""
        assert self._render("firefox", "", "ar") == "https://apps.apple.com/app/apple-store/id989804926?mz_pr=firefox_mobile"
        assert self._render("firefox", "", "zu") == "https://apps.apple.com/app/apple-store/id989804926?mz_pr=firefox_mobile"

    def test_firefox_app_store_url_localized(self):
        """should return localized URL"""
        assert self._render("firefox", "", "en-US") == "https://apps.apple.com/us/app/apple-store/id989804926?mz_pr=firefox_mobile"
        assert self._render("firefox", "", "es-ES") == "https://apps.apple.com/es/app/apple-store/id989804926?mz_pr=firefox_mobile"
        assert self._render("firefox", "", "de") == "https://apps.apple.com/de/app/apple-store/id989804926?mz_pr=firefox_mobile"

    def test_firefox_app_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("firefox", "firefox-home", "en-US")
            == "https://apps.apple.com/us/app/apple-store/id989804926?mz_pr=firefox_mobile&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )
        assert (
            self._render("firefox", "firefox-home", "es-ES")
            == "https://apps.apple.com/es/app/apple-store/id989804926?mz_pr=firefox_mobile&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )
        assert (
            self._render("firefox", "firefox-home", "de")
            == "https://apps.apple.com/de/app/apple-store/id989804926?mz_pr=firefox_mobile&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )

    def test_focus_app_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("focus", "firefox-home", "en-US")
            == "https://apps.apple.com/us/app/apple-store/id1055677337?mz_pr=focus&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )
        assert (
            self._render("focus", "firefox-home", "es-ES")
            == "https://apps.apple.com/es/app/apple-store/id1055677337?mz_pr=focus&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )
        assert (
            self._render("focus", "firefox-home", "de")
            == "https://apps.apple.com/de/app/apple-store/id1073435754?mz_pr=focus&amp;pt=373246&amp;ct=firefox-home&amp;mt=8"
        )

    def test_vpn_app_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("vpn", "vpn-landing-page", "en-US")
            == "https://apps.apple.com/us/app/apple-store/id1489407738?mz_pr=vpn&amp;pt=373246&amp;ct=vpn-landing-page&amp;mt=8"
        )
        assert (
            self._render("vpn", "vpn-landing-page", "es-ES")
            == "https://apps.apple.com/es/app/apple-store/id1489407738?mz_pr=vpn&amp;pt=373246&amp;ct=vpn-landing-page&amp;mt=8"
        )
        assert (
            self._render("vpn", "vpn-landing-page", "de")
            == "https://apps.apple.com/de/app/apple-store/id1489407738?mz_pr=vpn&amp;pt=373246&amp;ct=vpn-landing-page&amp;mt=8"
        )


class TestPlayStoreURL(TestCase):
    rf = RequestFactory()

    def _render(self, product, campaign, locale):
        req = self.rf.get("/")
        req.locale = locale
        return render(
            f"{{{{ play_store_url('{product}', '{campaign}') }}}}",
            {"request": req},
        )

    def test_firefox_play_store_url_no_locale(self):
        """No locale, fallback to default URL"""
        assert self._render("firefox", "", "") == "https://play.google.com/store/apps/details?id=org.mozilla.firefox"

    def test_firefox_play_store_url_localized(self):
        """should return localized URL"""
        assert self._render("firefox", "", "en-US") == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;hl=en"
        assert self._render("firefox", "", "es-ES") == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;hl=es"
        assert self._render("firefox", "", "de") == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;hl=de"

    def test_firefox_play_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("firefox", "firefox-home", "en-US")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=en"
        )
        assert (
            self._render("firefox", "firefox-home", "es-ES")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=es"
        )
        assert (
            self._render("firefox", "firefox-home", "de")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=de"
        )

    def test_focus_play_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("focus", "firefox-home", "en-US")
            == "https://play.google.com/store/apps/details?id=org.mozilla.focus&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=en"
        )
        assert (
            self._render("focus", "firefox-home", "es-ES")
            == "https://play.google.com/store/apps/details?id=org.mozilla.focus&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=es"
        )
        assert (
            self._render("focus", "firefox-home", "de")
            == "https://play.google.com/store/apps/details?id=org.mozilla.klar&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-home&amp;hl=de"
        )

    def test_vpn_play_store_url_localized_campaign(self):
        """should return localized URL with additional campaign parameters"""
        assert (
            self._render("vpn", "vpn-landing-page", "en-US")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox.vpn&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dvpn-landing-page&amp;hl=en"
        )
        assert (
            self._render("vpn", "vpn-landing-page", "es-ES")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox.vpn&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dvpn-landing-page&amp;hl=es"
        )
        assert (
            self._render("vpn", "vpn-landing-page", "de")
            == "https://play.google.com/store/apps/details?id=org.mozilla.firefox.vpn&amp;referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dvpn-landing-page&amp;hl=de"
        )


class TestMSStoreURL(TestCase):
    rf = RequestFactory()

    def _render(self, product, mode="mini", campaign=None, handler=None):
        req = self.rf.get("/")
        campaign_param = f"'{campaign}'" if campaign is not None else campaign
        handler_param = f"'{handler}'" if handler is not None else handler
        return render(
            f"{{{{ ms_store_url('{product}', '{mode}', {campaign_param}, {handler_param}) }}}}",
            {"request": req},
        )

    def test_firefox_release_ms_store_url(self):
        """should return a MS Store URL for Firefox release channel"""
        assert self._render(product="firefox") == "https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=mini&amp;mz_cn=release"

    def test_firefox_beta_ms_store_url(self):
        """should return a MS Store URL for Firefox Beta channel"""
        assert self._render(product="firefox_beta") == "https://apps.microsoft.com/detail/9nzw26frndln?mode=mini&amp;mz_cn=beta"

    def test_firefox_ms_store_url_launch_mode(self):
        """should return a MS Store URL including different launch mode parameters"""
        assert self._render(product="firefox", mode="full") == "https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=full&amp;mz_cn=release"
        assert self._render(product="firefox", mode="direct") == "https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=direct&amp;mz_cn=release"

    def test_firefox_ms_store_url_campaign(self):
        """should return a MS Store URL including campaign parameters"""
        assert (
            self._render(product="firefox", campaign="test-firefox-home")
            == "https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=mini&amp;cid=test-firefox-home&amp;mz_cn=release"
        )

    def test_firefox_ms_store_url_protocol_handler(self):
        """should return a MS Store URL including campaign parameters"""
        assert (
            self._render(product="firefox", campaign="test-firefox-home", handler="ms-windows-store")
            == "ms-windows-store://pdp/?productid=9nzvdkpmr9rd&amp;mode=mini&amp;cid=test-firefox-home&amp;mz_cn=release"
        )
        assert (
            self._render(product="firefox_beta", campaign="test-firefox-home", handler="ms-windows-store")
            == "ms-windows-store://pdp/?productid=9nzw26frndln&amp;mode=mini&amp;cid=test-firefox-home&amp;mz_cn=beta"
        )

    def test_firefox_unknown_product_ms_store_url(self):
        """should return a MS Store URL with unrecognized channel for unknown product"""
        assert self._render(product="unknown_product") == "https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=mini&amp;mz_cn=unrecognized"


class TestLangShort(TestCase):
    rf = RequestFactory()

    def _render(self, locale, domain=None):
        req = self.rf.get("/")
        req.locale = locale

        return render("{{ lang_short() }}", {"request": req})

    def test_shortened_locales(self):
        """should return a shortened locale code"""
        assert self._render("en-US") == "en"
        assert self._render("es-ES") == "es"
        assert self._render("de") == "de"


class TestNativeLanguageName(TestCase):
    rf = RequestFactory()

    def _render(self, locale, domain=None):
        req = self.rf.get("/")
        req.locale = locale

        return render("{{ native_language_name() }}", {"request": req})

    def test_native_language_names(self):
        """should return a native language name"""
        assert self._render("en-US") == "English (US)"
        assert self._render("de") == "Deutsch"
        assert self._render("tr") == "Türkçe"

    def test_unknown_locale_code(self):
        """should return locale code if unknown"""
        assert self._render("aaa") == "aaa"


@override_settings(FXA_ENDPOINT=TEST_FXA_ENDPOINT)
@override_settings(RELAY_PRODUCT_URL="https://relay.firefox.com/")
class TestRelayFxAButton(TestCase):
    rf = RequestFactory()

    def _render(
        self,
        entrypoint,
        button_text,
        class_name=None,
        is_button_class=True,
        include_metrics=True,
        optional_parameters=None,
        optional_attributes=None,
    ):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(
            "{{{{ relay_fxa_button('{0}', '{1}', '{2}', {3}, {4}, {5}, {6}) }}}}".format(
                entrypoint, button_text, class_name, is_button_class, include_metrics, optional_parameters, optional_attributes
            ),
            {"request": req},
        )

    def test_relay_fxa_button(self):
        """Should return expected markup"""
        markup = self._render(
            entrypoint="mozilla.org-whatsnew",
            button_text="Sign In to Relay",
            class_name="relay-main-cta-button",
            is_button_class=True,
            include_metrics=True,
            optional_parameters={"utm_campaign": "whatsnew96"},
            optional_attributes={"data-cta-text": "Sign In to Relay", "data-cta-type": "fxa-relay", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://relay.firefox.com/accounts/fxa/login/?process=login&entrypoint=mozilla.org-whatsnew&form_type=button'
            '&utm_source=mozilla.org-whatsnew&utm_medium=referral&utm_campaign=whatsnew96" data-action="https://accounts.firefox.com/" '
            'class="js-fxa-cta-link js-fxa-product-button mzp-c-button mzp-t-product relay-main-cta-button" '
            'data-cta-text="Sign In to Relay" data-cta-type="fxa-relay" data-cta-position="primary">Sign In to Relay</a>'
        )
        self.assertEqual(markup, expected)


@override_settings(FXA_ENDPOINT=TEST_FXA_ENDPOINT)
class TestMonitorFxAButton(TestCase):
    rf = RequestFactory()

    def _render(
        self,
        entrypoint,
        button_text,
        class_name=None,
        is_button_class=False,
        include_metrics=True,
        optional_parameters=None,
        optional_attributes=None,
    ):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(
            "{{{{ monitor_fxa_button('{0}', '{1}', '{2}', {3}, {4}, {5}, {6}) }}}}".format(
                entrypoint, button_text, class_name, is_button_class, include_metrics, optional_parameters, optional_attributes
            ),
            {"request": req},
        )

    def test_monitor_fxa_button(self):
        """Should return expected markup"""
        markup = self._render(
            entrypoint="mozilla.org-firefox-accounts",
            button_text="Sign In to Monitor",
            class_name="monitor-main-cta-button",
            is_button_class=False,
            include_metrics=True,
            optional_parameters={"utm_campaign": "skyline"},
            optional_attributes={"data-cta-text": "Sign In to Monitor", "data-cta-type": "fxa-monitor", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://monitor.mozilla.org/user/dashboard?entrypoint=mozilla.org-firefox-accounts&form_type=button'
            '&utm_source=mozilla.org-firefox-accounts&utm_medium=referral&utm_campaign=skyline" '
            'data-action="https://accounts.firefox.com/" class="js-fxa-cta-link js-fxa-product-button '
            'monitor-main-cta-button" data-cta-text="Sign In to Monitor" data-cta-type="fxa-monitor" '
            'data-cta-position="primary">Sign In to Monitor</a>'
        )
        self.assertEqual(markup, expected)


@override_settings(FXA_ENDPOINT=TEST_FXA_ENDPOINT)
class TestFxAButton(TestCase):
    rf = RequestFactory()

    def _render(
        self,
        entrypoint,
        button_text,
        action="signup",
        class_name=None,
        is_button_class=True,
        include_metrics=True,
        optional_parameters=None,
        optional_attributes=None,
    ):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(
            "{{{{ fxa_button('{0}', '{1}', '{2}', '{3}', {4}, {5}, {6}, {7}) }}}}".format(
                entrypoint, button_text, action, class_name, is_button_class, include_metrics, optional_parameters, optional_attributes
            ),
            {"request": req},
        )

    def test_fxa_button_signup(self):
        """Should return expected markup"""
        markup = self._render(
            entrypoint="mozilla.org-firefox-whatsnew73",
            button_text="Sign Up",
            action="signup",
            class_name="fxa-main-cta-button",
            is_button_class=True,
            include_metrics=True,
            optional_parameters={"utm_campaign": "whatsnew73"},
            optional_attributes={"data-cta-text": "Sign Up", "data-cta-type": "fxa-sync", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/signup?entrypoint=mozilla.org-firefox-whatsnew73&form_type=button'
            '&utm_source=mozilla.org-firefox-whatsnew73&utm_medium=referral&utm_campaign=whatsnew73" '
            'data-action="https://accounts.firefox.com/" class="js-fxa-cta-link js-fxa-product-button mzp-c-button mzp-t-product '
            'fxa-main-cta-button" data-cta-text="Sign Up" data-cta-type="fxa-sync" data-cta-position="primary">Sign Up</a>'
        )
        self.assertEqual(markup, expected)

    def test_fxa_button_signin(self):
        """Should return expected markup"""
        markup = self._render(
            entrypoint="mozilla.org-firefox-whatsnew73",
            button_text="Sign In",
            action="signin",
            class_name="fxa-main-cta-button",
            is_button_class=True,
            include_metrics=True,
            optional_parameters={"utm_campaign": "whatsnew73"},
            optional_attributes={"data-cta-text": "Sign In", "data-cta-type": "fxa-sync", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/signin?entrypoint=mozilla.org-firefox-whatsnew73&form_type=button'
            '&utm_source=mozilla.org-firefox-whatsnew73&utm_medium=referral&utm_campaign=whatsnew73" '
            'data-action="https://accounts.firefox.com/" class="js-fxa-cta-link js-fxa-product-button mzp-c-button mzp-t-product '
            'fxa-main-cta-button" data-cta-text="Sign In" data-cta-type="fxa-sync" data-cta-position="primary">Sign In</a>'
        )
        self.assertEqual(markup, expected)

    def test_fxa_button_email(self):
        """Should return expected markup"""
        markup = self._render(
            entrypoint="mozilla.org-firefox-whatsnew73",
            button_text="Sign Up",
            action="email",
            class_name="fxa-main-cta-button",
            is_button_class=True,
            include_metrics=True,
            optional_parameters={"utm_campaign": "whatsnew73"},
            optional_attributes={"data-cta-text": "Sign Up", "data-cta-type": "fxa-sync", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/?action=email&entrypoint=mozilla.org-firefox-whatsnew73&form_type=button'
            '&utm_source=mozilla.org-firefox-whatsnew73&utm_medium=referral&utm_campaign=whatsnew73" '
            'data-action="https://accounts.firefox.com/" class="js-fxa-cta-link js-fxa-product-button mzp-c-button mzp-t-product '
            'fxa-main-cta-button" data-cta-text="Sign Up" data-cta-type="fxa-sync" data-cta-position="primary">Sign Up</a>'
        )
        self.assertEqual(markup, expected)


@override_settings(FXA_ENDPOINT=TEST_FXA_ENDPOINT)
class TestFxALinkFragment(TestCase):
    rf = RequestFactory()

    def _render(self, entrypoint, action="signup", optional_parameters=None):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(f"{{{{ fxa_link_fragment('{entrypoint}', '{action}', {optional_parameters}) }}}}", {"request": req})

    def test_fxa_button_signup(self):
        """Should return expected markup"""
        markup = self._render(entrypoint="mozilla.org-firefox-whatsnew73", action="signup", optional_parameters={"utm_campaign": "whatsnew73"})
        expected = (
            'href="https://accounts.firefox.com/signup?entrypoint=mozilla.org-firefox-whatsnew73&form_type=button'
            '&utm_source=mozilla.org-firefox-whatsnew73&utm_medium=referral&utm_campaign=whatsnew73"'
        )
        self.assertEqual(markup, expected)

    def test_fxa_button_email(self):
        """Should return expected markup"""
        markup = self._render(entrypoint="mozilla.org-firefox-whatsnew73", action="email", optional_parameters={"utm_campaign": "whatsnew73"})
        expected = (
            'href="https://accounts.firefox.com/?action=email&entrypoint=mozilla.org-firefox-whatsnew73&form_type=button'
            '&utm_source=mozilla.org-firefox-whatsnew73&utm_medium=referral&utm_campaign=whatsnew73"'
        )
        self.assertEqual(markup, expected)


@pytest.mark.parametrize(
    "country_code, expected",
    [
        ("AT", "True"),  # Austria
        ("BE", "True"),  # Belgium
        ("BG", "True"),  # Bulgaria
        ("HR", "True"),  # Croatia
        ("CY", "True"),  # Republic of Cyprus
        ("CZ", "True"),  # Czech Republic
        ("DK", "True"),  # Denmark
        ("EE", "True"),  # Estonia
        ("FI", "True"),  # Finland
        ("FR", "True"),  # France
        ("DE", "True"),  # Germany
        ("GR", "True"),  # Greece
        ("HU", "True"),  # Hungary
        ("IE", "True"),  # Ireland
        ("IS", "True"),  # Iceland
        ("IT", "True"),  # Italy
        ("LV", "True"),  # Latvia
        ("LI", "True"),  # Liechtenstein
        ("LT", "True"),  # Lithuania
        ("LU", "True"),  # Luxembourg
        ("MT", "True"),  # Malta
        ("NL", "True"),  # Netherlands
        ("NO", "True"),  # Norway
        ("PL", "True"),  # Poland
        ("PT", "True"),  # Portugal
        ("RO", "True"),  # Romania
        ("SK", "True"),  # Slovakia
        ("SI", "True"),  # Slovenia
        ("ES", "True"),  # Spain
        ("SE", "True"),  # Sweden
        ("CH", "True"),  # Switzerland
        ("GB", "True"),  # United Kingdom
        ("US", "False"),  # United States
        ("CA", "False"),  # Canada
    ],
)
def test_needs_data_consent(country_code, expected):
    template = "{{ needs_data_consent('%s') }}" % country_code
    assert render(template) == expected

@override_settings(
    FXA_ENDPOINT=TEST_FXA_ENDPOINT,
    VPN_PRODUCT_ID=TEST_VPN_PRODUCT_ID,
    VPN_SUBSCRIPTION_URL=TEST_VPN_SUBSCRIPTION_URL,
    VPN_VARIABLE_PRICING=TEST_VPN_VARIABLE_PRICING,
)
class TestVPNSubscribeLink(TestCase):
    rf = RequestFactory()

    def _render(
        self,
        entrypoint="www.mozilla.org-vpn-product-page",
        link_text="Get Mozilla VPN",
        plan="12-month",
        class_name="mzp-c-button",
        country_code=None,
        lang=None,
        optional_parameters=None,
        optional_attributes=None,
    ):
        req = self.rf.get("/")
        req.locale = "en-US"
        return render(
            f"""{{{{ vpn_subscribe_link('{entrypoint}', '{link_text}', '{plan}', '{class_name}', '{country_code}',
                                        '{lang}', {optional_parameters}, {optional_attributes}) }}}}""",
            {"request": req},
        )

    def test_vpn_subscribe_link_variable_12_month(self):
        """Should return expected markup for variable 12-month plan link"""
        markup = self._render(
            plan="12-month",
            country_code="US",
            lang="en-US",
            optional_parameters={"utm_campaign": "vpn-product-page"},
            optional_attributes={"data-cta-text": "Get Mozilla VPN monthly", "data-cta-type": "fxa-vpn", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/subscriptions/products/prod_FvnsFHIfezy3ZI?plan=price_1Iw85dJNcmPzuWtRyhMDdtM7'
            "&entrypoint=www.mozilla.org-vpn-product-page&form_type=button&utm_source=www.mozilla.org-vpn-product-page"
            '&utm_medium=referral&utm_campaign=vpn-product-page&data_cta_position=primary" data-action="https://accounts.firefox.com/" '
            'class="js-vpn-cta-link js-fxa-product-button mzp-c-button" data-cta-text="Get Mozilla VPN monthly" data-cta-type="fxa-vpn" '
            'data-cta-position="primary">Get Mozilla VPN</a>'
        )
        self.assertEqual(markup, expected)

    def test_vpn_subscribe_link_variable_6_month(self):
        """Should return expected markup for variable 6-month plan link"""
        markup = self._render(
            plan="6-month",
            country_code="US",
            lang="en-US",
            optional_parameters={"utm_campaign": "vpn-product-page"},
            optional_attributes={"data-cta-text": "Get Mozilla VPN monthly", "data-cta-type": "fxa-vpn", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/subscriptions/products/prod_FvnsFHIfezy3ZI?plan=price_1Iw87cJNcmPzuWtRefuyqsOd'
            "&entrypoint=www.mozilla.org-vpn-product-page&form_type=button&utm_source=www.mozilla.org-vpn-product-page"
            '&utm_medium=referral&utm_campaign=vpn-product-page&data_cta_position=primary" data-action="https://accounts.firefox.com/" '
            'class="js-vpn-cta-link js-fxa-product-button mzp-c-button" data-cta-text="Get Mozilla VPN monthly" data-cta-type="fxa-vpn" '
            'data-cta-position="primary">Get Mozilla VPN</a>'
        )
        self.assertEqual(markup, expected)

    def test_vpn_subscribe_link_variable_monthly(self):
        """Should return expected markup for variable monthly plan link"""
        markup = self._render(
            plan="monthly",
            country_code="US",
            lang="en-US",
            optional_parameters={"utm_campaign": "vpn-product-page"},
            optional_attributes={"data-cta-text": "Get Mozilla VPN monthly", "data-cta-type": "fxa-vpn", "data-cta-position": "primary"},
        )
        expected = (
            '<a href="https://accounts.firefox.com/subscriptions/products/prod_FvnsFHIfezy3ZI?plan=price_1Iw7qSJNcmPzuWtRMUZpOwLm'
            "&entrypoint=www.mozilla.org-vpn-product-page&form_type=button&utm_source=www.mozilla.org-vpn-product-page"
            '&utm_medium=referral&utm_campaign=vpn-product-page&data_cta_position=primary" data-action="https://accounts.firefox.com/" '
            'class="js-vpn-cta-link js-fxa-product-button mzp-c-button" data-cta-text="Get Mozilla VPN monthly" data-cta-type="fxa-vpn" '
            'data-cta-position="primary">Get Mozilla VPN</a>'
        )
        self.assertEqual(markup, expected)

    def test_vpn_subscribe_link_variable_12_month_us_en(self):
        """Should contain expected 12-month plan ID (US / en-US)"""
        markup = self._render(
            plan="12-month",
            country_code="US",
            lang="en-US",
        )
        self.assertIn("?plan=price_1Iw85dJNcmPzuWtRyhMDdtM7", markup)

    def test_vpn_subscribe_link_variable_6_month_us_en(self):
        """Should contain expected 6-month plan ID (US / en-US)"""
        markup = self._render(
            plan="6-month",
            country_code="US",
            lang="en-US",
        )
        self.assertIn("?plan=price_1Iw87cJNcmPzuWtRefuyqsOd", markup)

    def test_vpn_subscribe_link_variable_monthly_us_en(self):
        """Should contain expected monthly plan ID (US / en-US)"""
        markup = self._render(
            plan="monthly",
            country_code="US",
            lang="en-US",
        )
        self.assertIn("?plan=price_1Iw7qSJNcmPzuWtRMUZpOwLm", markup)

    def test_vpn_subscribe_link_variable_12_month_ca_en(self):
        """Should contain expected 12-month plan ID (CA / en-CA)"""
        markup = self._render(
            plan="12-month",
            country_code="CA",
            lang="en-CA",
        )
        self.assertIn("?plan=price_1Iw85dJNcmPzuWtRyhMDdtM7", markup)

    def test_vpn_subscribe_link_variable_6_month_ca_en(self):
        """Should contain expected 6-month plan ID (CA / en-CA)"""
        markup = self._render(
            plan="6-month",
            country_code="CA",
            lang="en-CA",
        )
        self.assertIn("?plan=price_1Iw87cJNcmPzuWtRefuyqsOd", markup)

    def test_vpn_subscribe_link_variable_monthly_ca_en(self):
        """Should contain expected monthly plan ID in (CA / en-CA)"""
        markup = self._render(
            plan="monthly",
            country_code="CA",
            lang="en-CA",
        )
        self.assertIn("?plan=price_1Iw7qSJNcmPzuWtRMUZpOwLm", markup)

    def test_vpn_subscribe_link_variable_12_month_gb_en(self):
        """Should contain expected 12-month plan ID (GB / en-GB)"""
        markup = self._render(
            plan="12-month",
            country_code="GB",
            lang="en-GB",
        )
        self.assertIn("?plan=price_1Iw85dJNcmPzuWtRyhMDdtM7", markup)

    def test_vpn_subscribe_link_variable_6_month_gb_en(self):
        """Should contain expected 6-month plan ID (GB / en-GB)"""
        markup = self._render(
            plan="6-month",
            country_code="GB",
            lang="en-GB",
        )
        self.assertIn("?plan=price_1Iw87cJNcmPzuWtRefuyqsOd", markup)

    def test_vpn_subscribe_link_variable_monthly_gb_en(self):
        """Should contain expected monthly plan ID (GB / en-GB)"""
        markup = self._render(
            plan="monthly",
            country_code="GB",
            lang="en-GB",
        )
        self.assertIn("?plan=price_1Iw7qSJNcmPzuWtRMUZpOwLm", markup)

    def test_vpn_subscribe_link_variable_12_month_at_de(self):
        """Should contain expected 12-month plan ID (AT / de)"""
        markup = self._render(
            plan="12-month",
            country_code="AT",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwblJNcmPzuWtRynC7dqQa", markup)

    def test_vpn_subscribe_link_variable_6_month_at_de(self):
        """Should contain expected 6-month plan ID (AT / de)"""
        markup = self._render(
            plan="6-month",
            country_code="AT",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwaHJNcmPzuWtRuUfSR4l7", markup)

    def test_vpn_subscribe_link_variable_monthly_at_de(self):
        """Should contain expected monthly plan ID (AT / de)"""
        markup = self._render(
            plan="monthly",
            country_code="AT",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwZVJNcmPzuWtRg9Wssh2y", markup)

    def test_vpn_subscribe_link_variable_12_month_be_nl(self):
        """Should contain expected 12-month plan ID (BE / nl)"""
        markup = self._render(
            plan="12-month",
            country_code="BE",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JRGJNcmPzuWtRXwXA84cm", markup)

    def test_vpn_subscribe_link_variable_6_month_be_nl(self):
        """Should contain expected 6-month plan ID (BE / nl)"""
        markup = self._render(
            plan="6-month",
            country_code="BE",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JRmJNcmPzuWtRyFGj0tkN", markup)

    def test_vpn_subscribe_link_variable_monthly_be_nl(self):
        """Should contain expected monthly plan ID (BE / nl)"""
        markup = self._render(
            plan="monthly",
            country_code="BE",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JSkJNcmPzuWtR54LPH2zi", markup)

    def test_vpn_subscribe_link_variable_12_month_be_de(self):
        """Should contain expected 12-month plan ID (BE / de)"""
        markup = self._render(
            plan="12-month",
            country_code="BE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwblJNcmPzuWtRynC7dqQa", markup)

    def test_vpn_subscribe_link_variable_6_month_be_de(self):
        """Should contain expected 6-month plan ID (BE / de)"""
        markup = self._render(
            plan="6-month",
            country_code="BE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwaHJNcmPzuWtRuUfSR4l7", markup)

    def test_vpn_subscribe_link_variable_monthly_be_de(self):
        """Should contain expected monthly plan ID (BE / de)"""
        markup = self._render(
            plan="monthly",
            country_code="BE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwZVJNcmPzuWtRg9Wssh2y", markup)

    def test_vpn_subscribe_link_variable_12_month_be_fr(self):
        """Should contain expected 12-month plan ID (BE / fr)"""
        markup = self._render(
            plan="12-month",
            country_code="BE",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgnlcJNcmPzuWtRjrNa39W4", markup)

    def test_vpn_subscribe_link_variable_6_month_be_fr(self):
        """Should contain expected 6-month plan ID (BE / fr)"""
        markup = self._render(
            plan="6-month",
            country_code="BE",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgoxGJNcmPzuWtRG7l48EoV", markup)

    def test_vpn_subscribe_link_variable_monthly_be_fr(self):
        """Should contain expected monthly plan ID (BE / fr)"""
        markup = self._render(
            plan="monthly",
            country_code="BE",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgowHJNcmPzuWtRzD7SgAYb", markup)

    def test_vpn_default_language_selection_be_en(self):
        """Should should select default language if no match is found (BE / en)"""
        markup = self._render(
            plan="monthly",
            country_code="BE",
            lang="en-US",
        )
        self.assertIn("?plan=price_1J5JSkJNcmPzuWtR54LPH2zi", markup)

    def test_vpn_subscribe_link_variable_12_month_ch_de(self):
        """Should contain expected 12-month plan ID (CH / de)"""
        markup = self._render(
            plan="12-month",
            country_code="CH",
            lang="de",
        )
        self.assertIn("?plan=price_1J5JssJNcmPzuWtR616BH4aU", markup)

    def test_vpn_subscribe_link_variable_6_month_ch_de(self):
        """Should contain expected 6-month plan ID (CH / de)"""
        markup = self._render(
            plan="6-month",
            country_code="CH",
            lang="de",
        )
        self.assertIn("?plan=price_1J5JtWJNcmPzuWtRMd2siphH", markup)

    def test_vpn_subscribe_link_variable_monthly_ch_de(self):
        """Should contain expected monthly plan ID (CH / de)"""
        markup = self._render(
            plan="monthly",
            country_code="CH",
            lang="de",
        )
        self.assertIn("?plan=price_1J5Ju3JNcmPzuWtR3GpNYSWj", markup)

    def test_vpn_subscribe_link_variable_12_month_ch_fr(self):
        """Should contain expected 12-month plan ID (CH / fr)"""
        markup = self._render(
            plan="12-month",
            country_code="CH",
            lang="fr",
        )
        self.assertIn("?plan=price_1J5JunJNcmPzuWtRo9dLxn6M", markup)

    def test_vpn_subscribe_link_variable_6_month_ch_fr(self):
        """Should contain expected 6-month plan ID (CH / fr)"""
        markup = self._render(
            plan="6-month",
            country_code="CH",
            lang="fr",
        )
        self.assertIn("?plan=price_1J5JvLJNcmPzuWtRayB4d7Ij", markup)

    def test_vpn_subscribe_link_variable_monthly_ch_fr(self):
        """Should contain expected monthly plan ID (CH / fr)"""
        markup = self._render(
            plan="monthly",
            country_code="CH",
            lang="fr",
        )
        self.assertIn("?plan=price_1J5JvjJNcmPzuWtR3wwy1dcR", markup)

    def test_vpn_subscribe_link_variable_12_month_ch_it(self):
        """Should contain expected 12-month plan ID (CH / it)"""
        markup = self._render(
            plan="12-month",
            country_code="CH",
            lang="it",
        )
        self.assertIn("?plan=price_1J5JwWJNcmPzuWtRgrx5fjOc", markup)

    def test_vpn_subscribe_link_variable_6_month_ch_it(self):
        """Should contain expected 6-month plan ID (CH / it)"""
        markup = self._render(
            plan="6-month",
            country_code="CH",
            lang="it",
        )
        self.assertIn("?plan=price_1J5JwvJNcmPzuWtRH2HuhWM5", markup)

    def test_vpn_subscribe_link_variable_monthly_ch_it(self):
        """Should contain expected monthly plan ID (CH / it)"""
        markup = self._render(
            plan="monthly",
            country_code="CH",
            lang="it",
        )
        self.assertIn("?plan=price_1J5JxGJNcmPzuWtRrp5e1SUB", markup)

    def test_vpn_default_language_selection_ch_en(self):
        """Should should select default language if no match is found (CH / en)"""
        markup = self._render(
            plan="monthly",
            country_code="CH",
            lang="en-US",
        )
        self.assertIn("?plan=price_1J5Ju3JNcmPzuWtR3GpNYSWj", markup)

    def test_vpn_subscribe_link_variable_12_month_de_de(self):
        """Should contain expected 12-month plan ID (DE / de)"""
        markup = self._render(
            plan="12-month",
            country_code="DE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwblJNcmPzuWtRynC7dqQa", markup)

    def test_vpn_subscribe_link_variable_6_month_de_de(self):
        """Should contain expected 6-month plan ID (DE / de)"""
        markup = self._render(
            plan="6-month",
            country_code="DE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwaHJNcmPzuWtRuUfSR4l7", markup)

    def test_vpn_subscribe_link_variable_monthly_de_de(self):
        """Should contain expected monthly plan ID (DE / de)"""
        markup = self._render(
            plan="monthly",
            country_code="DE",
            lang="de",
        )
        self.assertIn("?plan=price_1IgwZVJNcmPzuWtRg9Wssh2y", markup)

    def test_vpn_subscribe_link_variable_12_month_fr_fr(self):
        """Should contain expected 12-month plan ID (FR / fr)"""
        markup = self._render(
            plan="12-month",
            country_code="FR",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgnlcJNcmPzuWtRjrNa39W4", markup)

    def test_vpn_subscribe_link_variable_6_month_fr_fr(self):
        """Should contain expected 6-month plan ID (FR / fr)"""
        markup = self._render(
            plan="6-month",
            country_code="FR",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgoxGJNcmPzuWtRG7l48EoV", markup)

    def test_vpn_subscribe_link_variable_monthly_fr_fr(self):
        """Should contain expected monthly plan ID (FR / fr)"""
        markup = self._render(
            plan="monthly",
            country_code="FR",
            lang="fr",
        )
        self.assertIn("?plan=price_1IgowHJNcmPzuWtRzD7SgAYb", markup)

    def test_vpn_subscribe_link_variable_12_month_es_es(self):
        """Should contain expected 12-month plan ID (ES / es-ES)"""
        markup = self._render(
            plan="12-month",
            country_code="ES",
            lang="es-ES",
        )
        self.assertIn("?plan=price_1J5JCdJNcmPzuWtRrvQMFLlP", markup)

    def test_vpn_subscribe_link_variable_6_month_es_es(self):
        """Should contain expected 6-month plan ID (ES / es-ES)"""
        markup = self._render(
            plan="6-month",
            country_code="ES",
            lang="es-ES",
        )
        self.assertIn("?plan=price_1J5JDFJNcmPzuWtRrC4IeXTs", markup)

    def test_vpn_subscribe_link_variable_monthly_es_es(self):
        """Should contain expected monthly plan ID (ES / es-ES)"""
        markup = self._render(
            plan="monthly",
            country_code="ES",
            lang="es-ES",
        )
        self.assertIn("?plan=price_1J5JDgJNcmPzuWtRqQtIbktk", markup)

    def test_vpn_subscribe_link_variable_12_month_it_it(self):
        """Should contain expected 12-month plan ID (IT / it)"""
        markup = self._render(
            plan="12-month",
            country_code="IT",
            lang="it",
        )
        self.assertIn("?plan=price_1J4owvJNcmPzuWtRomVhWQFq", markup)

    def test_vpn_subscribe_link_variable_6_month_it_it(self):
        """Should contain expected 6-month plan ID (IT / it)"""
        markup = self._render(
            plan="6-month",
            country_code="IT",
            lang="it",
        )
        self.assertIn("?plan=price_1J5J7eJNcmPzuWtRKdQi4Tkk", markup)

    def test_vpn_subscribe_link_variable_monthly_it_it(self):
        """Should contain expected monthly plan ID (IT / it)"""
        markup = self._render(
            plan="monthly",
            country_code="IT",
            lang="it",
        )
        self.assertIn("?plan=price_1J5J6iJNcmPzuWtRK5zfoguV", markup)

    def test_vpn_subscribe_link_variable_12_month_ie_en(self):
        """Should contain expected 12-month plan ID (IE / en-US)"""
        markup = self._render(
            plan="12-month",
            country_code="IE",
            lang="en-US",
        )
        self.assertIn("?plan=price_1JcdvBJNcmPzuWtROLbEH9d2", markup)

    def test_vpn_subscribe_link_variable_6_month_ie_en(self):
        """Should contain expected 6-month plan ID (IE / en-US)"""
        markup = self._render(
            plan="6-month",
            country_code="IE",
            lang="en-US",
        )
        self.assertIn("?plan=price_1Jcdu8JNcmPzuWtRK6u5TUoZ", markup)

    def test_vpn_subscribe_link_variable_monthly_ie_en(self):
        """Should contain expected monthly plan ID (IE / en-US)"""
        markup = self._render(
            plan="monthly",
            country_code="IE",
            lang="en-US",
        )
        self.assertIn("?plan=price_1JcdsSJNcmPzuWtRGF9Y5TMJ", markup)

    def test_vpn_subscribe_link_variable_12_month_nl_nl(self):
        """Should contain expected 12-month plan ID (NL / nl)"""
        markup = self._render(
            plan="12-month",
            country_code="NL",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JRGJNcmPzuWtRXwXA84cm", markup)

    def test_vpn_subscribe_link_variable_6_month_nl_nl(self):
        """Should contain expected 16-month plan ID (NL / nl)"""
        markup = self._render(
            plan="6-month",
            country_code="NL",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JRmJNcmPzuWtRyFGj0tkN", markup)

    def test_vpn_subscribe_link_variable_monthly_nl_nl(self):
        """Should contain expected monthly plan ID (NL / nl)"""
        markup = self._render(
            plan="monthly",
            country_code="NL",
            lang="nl",
        )
        self.assertIn("?plan=price_1J5JSkJNcmPzuWtR54LPH2zi", markup)


class TestVPNProductReferralLink(TestCase):
    rf = RequestFactory()

    def _render(self, referral_id, page_anchor, link_text, class_name, optional_attributes):
        with self.activate_locale("en-US"):
            req = self.rf.get("/")
            req.locale = "en-US"
            return render(
                f"{{{{ vpn_product_referral_link('{referral_id}', '{page_anchor}', '{link_text}', '{class_name}', {optional_attributes}) }}}}",
                {"request": req},
            )

    def test_vpn_product_referral_link(self):
        """Should return expected markup"""
        markup = self._render(
            referral_id="navigation",
            page_anchor="#pricing",
            link_text="Get Mozilla VPN",
            class_name="mzp-t-secondary mzp-t-md",
            optional_attributes={"data-cta-text": "Get Mozilla VPN", "data-cta-type": "button"},
        )
        expected = (
            '<a href="/en-US/products/vpn/#pricing" class="mzp-c-button mzp-t-product '
            'js-fxa-product-referral-link mzp-t-secondary mzp-t-md" data-referral-id="navigation" '
            'data-cta-text="Get Mozilla VPN" data-cta-type="button">Get Mozilla VPN</a>'
        )
        self.assertEqual(markup, expected)
