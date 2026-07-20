# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import partial
from unittest.mock import patch

from django.http.response import HttpResponse
from django.test import RequestFactory

import pytest

import springfield.firefox.redirects as redirects_module
from springfield.firefox.redirects import mobile_app, validate_param_value
from springfield.redirects.middleware import RedirectsMiddleware
from springfield.redirects.util import get_resolver, redirect


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
    """Return middleware built from the redirects module's refresh_redirects."""
    return RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(redirects_module.refresh_redirects))


@pytest.mark.parametrize(
    "source, destination",
    (
        ("/browsers/desktop/windows/", "/download/windows/"),
        ("/browsers/desktop/mac/", "/download/mac/"),
        ("/browsers/desktop/linux/", "/download/linux/"),
        ("/browsers/mobile/android/", "/download/android/"),
        ("/browsers/mobile/ios/", "/download/ios/"),
        ("/browsers/desktop/chromebook/", "/download/chromebook/"),
        ("/browsers/mobile/", "/mobile/"),
        ("/browsers/mobile/get-app/", "/mobile/"),
        ("/browsers/mobile/focus/", "/mobile/focus/"),
        ("/browsers/unsupported-systems/", "/download/unsupported-systems/"),
    ),
)
def test_refresh_redirect_destinations(source, destination):
    rf = RequestFactory()
    middleware = _get_refresh_middleware()
    resp = middleware.process_request(rf.get(source))
    assert resp.status_code == 301
    assert resp["location"] == destination


@pytest.mark.parametrize(
    "source, destination",
    (
        ("/browsers/desktop/windows/?utm_source=foo", "/download/windows/?utm_source=foo"),
        ("/browsers/desktop/mac/?utm_source=foo&utm_medium=bar", "/download/mac/?utm_source=foo&utm_medium=bar"),
    ),
)
def test_refresh_redirect_preserves_query_strings(source, destination):
    rf = RequestFactory()
    middleware = _get_refresh_middleware()
    resp = middleware.process_request(rf.get(source))
    assert resp.status_code == 301
    assert resp["location"] == destination


@pytest.mark.parametrize(
    "locale",
    ("en-US", "de", "fr"),
)
def test_refresh_redirect_locale_handling(locale):
    rf = RequestFactory()
    middleware = _get_refresh_middleware()
    resp = middleware.process_request(rf.get(f"/{locale}/browsers/desktop/windows/"))
    assert resp.status_code == 301
    assert resp["location"] == f"/{locale}/download/windows/"


@pytest.mark.parametrize(
    "source, dest",
    (
        ("/ai/", "/smart-window/?view=waitlist"),  # no locale; middleware will later add the most appropriate locale
        ("/en-US/ai/", "/en-US/smart-window/?view=waitlist"),  # with locale
        ("/fr/ai/", "/fr/smart-window/?view=waitlist"),  # non-default locale
        ("/en-GB/ai/?foo=bar", "/en-GB/smart-window/?view=waitlist"),  # incoming query strings are disregarded because `merge_query` is False
    ),
)
def test_ai_redirect_to_smart_window_waitlist(client, source, dest):
    resp = client.get(source, follow=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == dest


@pytest.mark.parametrize(
    "accept_language",
    ("en-US", "de", "fr", "es-MX", "ja"),
)
@pytest.mark.parametrize(
    "source",
    ("/school/", "/school"),
)
def test_school_redirect_always_lands_on_en_us(client, source, accept_language):
    resp = client.get(source, headers={"accept-language": accept_language}, follow=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/en-US/landing/school/"


@pytest.mark.parametrize(
    "source",
    ("/school/?utm_source=test&utm_campaign=school", "/school?utm_source=test&utm_campaign=school"),
)
def test_school_redirect_preserves_query_string(client, source):
    resp = client.get(source, follow=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/en-US/landing/school/?utm_source=test&utm_campaign=school"


# -- Offsite redirect / locale / query string isolation tests --

EXPECTED_REDIRECT_QS = "?redirect_source=test"
_TEST_EXT_HOST = "https://www.example.com"
_TEST_EXT_BASE = f"{_TEST_EXT_HOST}/{{_locale}}"

_test_offsite_redirect = partial(
    redirect,
    query={"redirect_source": "test"},
    merge_query=True,
    permanent=False,
)

_test_offsite_patterns = (
    _test_offsite_redirect(r"^firefox/new/$", f"{_TEST_EXT_BASE}/"),
    _test_offsite_redirect(r"^firefox/installer-help/$", f"{_TEST_EXT_BASE}/download/installer-help/"),
    _test_offsite_redirect(r"^firefox/set-as-default/$", f"{_TEST_EXT_BASE}/landing/set-as-default/"),
    _test_offsite_redirect(r"^firefox/browsers/incognito-browser/$", f"{_TEST_EXT_BASE}/more/incognito-browser/"),
)


def _get_offsite_middleware():
    return RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(_test_offsite_patterns))


@pytest.mark.parametrize(
    "path, expected_dest",
    (
        ("/en-US/firefox/new/?hello=world", f"{_TEST_EXT_HOST}/en-US/{EXPECTED_REDIRECT_QS}&hello=world"),
        ("/en-US/firefox/new/", f"{_TEST_EXT_HOST}/en-US/{EXPECTED_REDIRECT_QS}"),
        (
            "/en-US/firefox/installer-help/?bar=baz&bam=bam",
            f"{_TEST_EXT_HOST}/en-US/download/installer-help/{EXPECTED_REDIRECT_QS}&bar=baz&bam=bam",
        ),
        ("/en-US/firefox/installer-help/", f"{_TEST_EXT_HOST}/en-US/download/installer-help/{EXPECTED_REDIRECT_QS}"),
    ),
)
def test_subsequent_redirects_do_not_carry_query_strings_from_earlier_requests(path, expected_dest):
    # Safety check that Django/Springfield isn't caching query strings used in other
    # responses. Both of the parametrized paths above are included with and
    # without extra query strings, which should NOT bleed between requests.
    rf = RequestFactory()
    middleware = _get_offsite_middleware()
    resp = middleware.process_request(rf.get(path))
    assert resp.status_code == 302
    assert resp.headers["Location"] == expected_dest


@pytest.mark.parametrize(
    "path, expected_dest",
    (
        ("/firefox/new/", f"{_TEST_EXT_HOST}/{EXPECTED_REDIRECT_QS}"),
        ("/firefox/set-as-default/", f"{_TEST_EXT_HOST}/landing/set-as-default/{EXPECTED_REDIRECT_QS}"),
        ("/firefox/browsers/incognito-browser/", f"{_TEST_EXT_HOST}/more/incognito-browser/{EXPECTED_REDIRECT_QS}"),
    ),
)
def test_offsite_redirects_still_work_when_locale_not_in_source_path(path, expected_dest):
    # Our redirects kick in before our locale-prepending middleware, so we may
    # find some redirects that don't have a locale when sending the user to an
    # external site. The {_locale} placeholder should be stripped cleanly.
    rf = RequestFactory()
    middleware = _get_offsite_middleware()
    resp = middleware.process_request(rf.get(path))
    assert resp.status_code == 302
    assert resp.headers["Location"] == expected_dest


# -- merge_query=True tests --

_test_merge_query_patterns = (
    redirect(
        r"^merge-query-test/$",
        "/merge-query-dest/",
        query={"test": "true"},
        merge_query=True,
        permanent=False,
    ),
)


def _get_merge_query_middleware():
    return RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(_test_merge_query_patterns))


@pytest.mark.parametrize(
    "source, dest",
    (
        ("/merge-query-test/", "/merge-query-dest/?test=true"),
        ("/merge-query-test/?hello=world", "/merge-query-dest/?test=true&hello=world"),
        ("/merge-query-test/?hello=world&foo=bar", "/merge-query-dest/?test=true&hello=world&foo=bar"),
        ("/en-US/merge-query-test/", "/en-US/merge-query-dest/?test=true"),
        ("/fr/merge-query-test/", "/fr/merge-query-dest/?test=true"),
        ("/en-GB/merge-query-test/?foo=bar", "/en-GB/merge-query-dest/?test=true&foo=bar"),
    ),
)
def test_merge_query_redirect(source, dest):
    # Uses a test-only redirect pattern so coverage doesn't depend on any
    # production redirect that uses merge_query.
    rf = RequestFactory()
    resp = _get_merge_query_middleware().process_request(rf.get(source))
    assert resp.status_code == 302
    assert resp.headers["Location"] == dest


@pytest.mark.parametrize("permanent", (True, False), ids=("301", "302"))
@pytest.mark.parametrize(
    "source, destination",
    (("/mobile/get-app", "/mobile/"),),
)
def test_redirect_destinations(client, source, destination, permanent):
    resp = client.get(source, follow=False)
    assert resp.status_code == 302
    assert resp.headers["Location"] == destination
