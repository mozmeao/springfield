# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test redirects from all apps."""

from operator import itemgetter

import pytest

from .base import assert_valid_url
from .map_all_redirects import URLS as REDIRECT_URLS
from .map_locales import URLS as LOCALE_URLS


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize("url", REDIRECT_URLS, ids=itemgetter("url"))
def test_redirect_url(url, base_url):
    url["base_url"] = base_url
    assert_valid_url(**url)


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize("url", LOCALE_URLS)
def test_locale_url(url, base_url):
    url["base_url"] = base_url
    assert_valid_url(**url)
