# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.conf import settings
from django.test import TestCase as DjangoTestCase
from django.test.client import RequestFactory

import pytest
from waffle.testutils import override_switch

from springfield.base import views
from springfield.base.tests import TestCase
from springfield.base.views import GeoTemplateView

geo_template_view = GeoTemplateView.as_view(
    geo_template_names={
        "DE": "firefox-klar.html",
        "GB": "firefox-focus.html",
    },
    template_name="firefox-mobile.html",
)


class TestGeoTemplateView(DjangoTestCase):
    def get_template(self, country):
        with patch("springfield.firefox.views.l10n_utils.render") as render_mock:
            with patch("springfield.base.views.get_country_from_request") as geo_mock:
                geo_mock.return_value = country
                rf = RequestFactory()
                req = rf.get("/")
                geo_template_view(req)
                return render_mock.call_args[0][1][0]

    def test_country_template(self):
        template = self.get_template("DE")
        assert template == "firefox-klar.html"

    def test_default_template(self):
        template = self.get_template("US")
        assert template == "firefox-mobile.html"

    def test_no_country(self):
        template = self.get_template(None)
        assert template == "firefox-mobile.html"


@pytest.mark.django_db
def test_csrf_view_is_custom_one():
    assert settings.CSRF_FAILURE_VIEW == "springfield.base.views.csrf_failure"


class TestRobots(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = views.Robots()

    @override_switch("ROBOTS_FORCE_DISALLOW_ALL", active=False)
    def test_production_disallow_all_is_false(self):
        self.view.request = self.rf.get("/", HTTP_HOST="www.firefox.com")
        self.assertFalse(self.view.get_context_data()["disallow_all"])

    @override_switch("ROBOTS_FORCE_DISALLOW_ALL", active=True)
    def test_production_disallow_all_is_false_unless_switch_is_on(self):
        self.view.request = self.rf.get("/", HTTP_HOST="www.firefox.com")
        self.assertTrue(self.view.get_context_data()["disallow_all"])

    @override_switch("ROBOTS_FORCE_DISALLOW_ALL", active=True)
    def test_non_production_disallow_all_is_always_true__switch_set(self):
        self.view.request = self.rf.get("/", HTTP_HOST="www.springfield.moz.works")
        self.assertTrue(self.view.get_context_data()["disallow_all"])

    @override_switch("ROBOTS_FORCE_DISALLOW_ALL", active=False)
    def test_non_production_disallow_all_is_always_true__switch_not_set(self):
        self.view.request = self.rf.get("/", HTTP_HOST="www.springfield.moz.works")
        self.assertTrue(self.view.get_context_data()["disallow_all"])

    def test_robots_no_redirect(self):
        response = self.client.get("/robots.txt", headers={"host": "www.firefox.com"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data["disallow_all"])
        self.assertEqual(response.get("Content-Type"), "text/plain")


class TestSecurityDotTxt(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = views.SecurityDotTxt()

    def test_no_redirect(self):
        response = self.client.get("/.well-known/security.txt", headers={"host": "www.mozilla.org"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/plain")
        self.assertContains(response, "security@mozilla.org")
