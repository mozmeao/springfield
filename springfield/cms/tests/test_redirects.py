# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory

import pytest

from springfield.cms.redirects import prefer_cms_redirect
from springfield.redirects.middleware import RedirectsMiddleware
from springfield.redirects.util import get_resolver


def _get_middleware(patterns):
    return RedirectsMiddleware(get_response=HttpResponse, resolver=get_resolver(patterns))


def _get_patterns():
    return [prefer_cms_redirect(r"^browsers/desktop/windows/$", "/download/windows/")]


@pytest.mark.parametrize("locale", ("de", "fr", "en-US"))
@patch("springfield.cms.redirects._cms_page_exists", return_value=True)
def test_page_exists_redirects(mock_exists, locale):
    """When a CMS page exists at the destination, the redirect should fire."""
    rf = RequestFactory()
    middleware = _get_middleware(_get_patterns())
    resp = middleware.process_request(rf.get(f"/{locale}/browsers/desktop/windows/"))
    assert resp is not None
    assert resp.status_code == 301
    assert resp["Location"] == f"/{locale}/download/windows/"


@pytest.mark.parametrize("locale", ("sv-SE", "ko", "th"))
@patch("springfield.cms.redirects._cms_page_exists", return_value=False)
def test_page_missing_passes_through(mock_exists, locale):
    """When no CMS page exists at the destination, the request should pass through."""
    rf = RequestFactory()
    middleware = _get_middleware(_get_patterns())
    resp = middleware.process_request(rf.get(f"/{locale}/browsers/desktop/windows/"))
    assert resp is None


@patch("springfield.cms.redirects._cms_page_exists", return_value=True)
def test_no_locale_prefix_redirects(mock_exists):
    """Requests without a locale prefix should use the default locale and redirect."""
    rf = RequestFactory()
    middleware = _get_middleware(_get_patterns())
    resp = middleware.process_request(rf.get("/browsers/desktop/windows/"))
    assert resp is not None
    assert resp.status_code == 301
    assert resp["Location"] == "/download/windows/"
    mock_exists.assert_called_with("en-US", "/download/windows/")


@patch("springfield.cms.redirects._cms_page_exists", return_value=True)
def test_query_strings_preserved(mock_exists):
    """Query strings should be preserved on redirect."""
    rf = RequestFactory()
    middleware = _get_middleware(_get_patterns())
    resp = middleware.process_request(rf.get("/de/browsers/desktop/windows/?utm_source=foo"))
    assert resp is not None
    assert resp.status_code == 301
    assert resp["Location"] == "/de/download/windows/?utm_source=foo"
