# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib
from unittest.mock import patch

from django.http.response import HttpResponse
from django.test import RequestFactory, override_settings

import pytest

import springfield.firefox.redirects as redirects_module
from springfield.firefox.redirects import mobile_app, validate_param_value
from springfield.redirects.middleware import RedirectsMiddleware
from springfield.redirects.util import get_resolver


@pytest.mark.parametrize(
    "test_param, is_valid",
    (
        ("firefox-whatsnew", True),
        ("firefox-welcome-4", True),
        ("firefox-welcome-6", True),
        ("firefox-welcome-17-en", True),
        ("firefox-welcome-17-de", True),
        ("firefox-welcome-17-fr", True),
        ("firefox-browsers-mobile-get-app", True),
        ("firefox-browsers-mobile-focus", True),
        ("mzaonboardingemail-de", True),
        ("mzaonboardingemail-fr", True),
        ("mzaonboardingemail-es", True),
        ("firefox-all", True),
        ("fxshare1", True),
        ("fxshare2", True),
        ("fxshare3", True),
        ("fxshare4", True),
        ("fxshare12", True),
        ("fxshare14", True),
        ("fxshare15", True),
        ("DESKTOP_FEATURE_CALLOUT_SIGNED_INTO_ACCOUNT.treatment_a", True),
        ("DESKTOP_FEATURE_CALLOUT_SIGNED_INTO_ACCOUNT.treatment_b", True),
        ("wnp134-de-a", True),
        ("wnp134-de-b", True),
        ("wnp134-de-c", True),
        ("wnp134-en-ca-a", True),
        ("wnp134-en-ca-b", True),
        ("smi-marvintsp", True),
        ("smi-koschtaaa", True),
        ("smi-bytereview", True),
        ("pocket-test", True),
        ("some<nefarious$thing", False),
        ("ano+h3r=ne", False),
        ("ǖnicode", False),
        ("♪♫♬♭♮♯", False),
        ("", False),
        (None, False),
    ),
)
def test_param_verification(test_param, is_valid):
    if is_valid:
        assert validate_param_value(test_param) == test_param
    else:
        assert validate_param_value(test_param) is None


def test_mobile_app():
    rf = RequestFactory()

    # both args exist and have valid values
    req = rf.get("/firefox/app/?product=focus&campaign=firefox-all")
    with patch("springfield.firefox.redirects.mobile_app_redirector") as mar:
        mobile_app(req)
        mar.assert_called_with(req, "focus", "firefox-all")

    # neither args exist
    req = rf.get("/firefox/app/")
    with patch("springfield.firefox.redirects.mobile_app_redirector") as mar:
        mobile_app(req)
        mar.assert_called_with(req, "firefox", None)

    # both args exist but invalid values
    req = rf.get("/firefox/app/?product=dude&campaign=walter$")
    with patch("springfield.firefox.redirects.mobile_app_redirector") as mar:
        mobile_app(req)
        mar.assert_called_with(req, "firefox", None)

    # other args exist
    req = rf.get("/firefox/app/?bunny=dude&maude=artist")
    with patch("springfield.firefox.redirects.mobile_app_redirector") as mar:
        mobile_app(req)
        mar.assert_called_with(req, "firefox", None)


def _get_refresh_middleware():
    """Reload the redirects module and return middleware built from its refresh_redirects."""
    importlib.reload(redirects_module)
    return RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(redirects_module.refresh_redirects))


@pytest.mark.parametrize("permanent", (True, False), ids=("301", "302"))
@pytest.mark.parametrize(
    "source, destination",
    (
        ("/browsers/desktop/windows/", "/download/windows/"),
        ("/browsers/desktop/mac/", "/download/mac/"),
        ("/browsers/desktop/linux/", "/download/linux/"),
        ("/browsers/mobile/android/", "/download/android/"),
        ("/browsers/mobile/ios/", "/download/ios/"),
        ("/browsers/desktop/chromebook/", "/download/chromebook/"),
    ),
)
def test_refresh_redirect_destinations(source, destination, permanent):
    rf = RequestFactory()
    with override_settings(PERMANENT_CMS_REFRESH_REDIRECTS=permanent):
        middleware = _get_refresh_middleware()
        resp = middleware.process_request(rf.get(source))
    assert resp.status_code == (301 if permanent else 302)
    assert resp["location"] == destination


@pytest.mark.parametrize("permanent", (True, False), ids=("301", "302"))
@pytest.mark.parametrize(
    "source, destination",
    (
        ("/browsers/desktop/windows/?utm_source=foo", "/download/windows/?utm_source=foo"),
        ("/browsers/desktop/mac/?utm_source=foo&utm_medium=bar", "/download/mac/?utm_source=foo&utm_medium=bar"),
    ),
)
def test_refresh_redirect_preserves_querystrings(source, destination, permanent):
    rf = RequestFactory()
    with override_settings(PERMANENT_CMS_REFRESH_REDIRECTS=permanent):
        middleware = _get_refresh_middleware()
        resp = middleware.process_request(rf.get(source))
    assert resp.status_code == (301 if permanent else 302)
    assert resp["location"] == destination


@pytest.mark.parametrize("permanent", (True, False), ids=("301", "302"))
@pytest.mark.parametrize(
    "locale",
    ("en-US", "de", "fr"),
)
def test_refresh_redirect_locale_handling(locale, permanent):
    rf = RequestFactory()
    with override_settings(PERMANENT_CMS_REFRESH_REDIRECTS=permanent):
        middleware = _get_refresh_middleware()
        resp = middleware.process_request(rf.get(f"/{locale}/browsers/desktop/windows/"))
    assert resp.status_code == (301 if permanent else 302)
    assert resp["location"] == f"/{locale}/download/windows/"


def test_refresh_redirects_not_in_redirectpatterns_when_disabled():
    with override_settings(ENABLE_CMS_REFRESH_REDIRECTS=False, PERMANENT_CMS_REFRESH_REDIRECTS=False):
        importlib.reload(redirects_module)
        rf = RequestFactory()
        middleware = RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(redirects_module.redirectpatterns))
        resp = middleware.process_request(rf.get("/browsers/desktop/windows/"))
    assert resp is None
    # Reload to restore original state
    importlib.reload(redirects_module)
