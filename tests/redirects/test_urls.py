# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test status codes of key pages and vanity redirects."""

import pytest
import requests

from .base import assert_valid_url
from .map_410 import URLS_410


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_410)
def test_410_url(url, base_url):
    assert_valid_url(url, base_url=base_url, status_code=requests.codes.gone)


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
def test_404_url(base_url):
    assert_valid_url(
        "/en-US/jozxyqk",
        base_url=base_url,
        final_status_code=requests.codes.not_found,
        follow_redirects=True,
    )


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/os/",
    ],
)
def test_301_urls(url, base_url, follow_redirects=False):
    assert_valid_url(url, base_url=base_url, follow_redirects=follow_redirects)


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/android/",
        "/channel/",
        "/desktop/",
        "/developer/",
        # "/browsers/",  # TODO: redirect to add?
        # "/mobile/",    # TODO: redirect to add?
        "/firefox/notes/",
        "/firefox/beta/notes/",
        "/firefox/nightly/notes/",
        "/firefox/android/releasenotes/",
        "/firefox/ios/releasenotes/",
        "/firefox/latest/releasenotes/",
        "/firefox/system-requirements/",
        "/pair/",
    ],
)
def test_302_urls(url, base_url, follow_redirects=False):
    assert_valid_url(url, base_url=base_url, follow_redirects=follow_redirects, status_code=requests.codes.found)
