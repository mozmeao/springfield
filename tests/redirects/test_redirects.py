# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test redirects from all apps."""

import importlib
from operator import itemgetter

from django.test import override_settings
from django.urls import clear_url_caches

import pytest

import springfield.firefox.redirects as firefox_redirects_module
import springfield.firefox.urls as firefox_urls_module
import springfield.urls as root_urls_module
from springfield.redirects import util as redirects_util

from .base import assert_valid_url
from .map_all_redirects import URLS as REDIRECT_URLS
from .map_locales import URLS as LOCALE_URLS


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize("url", REDIRECT_URLS, ids=itemgetter("url"))
def test_redirect_url(url, base_url):
    original_patterns = list(redirects_util.redirectpatterns)
    with override_settings(ENABLE_CMS_REFRESH_REDIRECTS=True):
        importlib.reload(firefox_redirects_module)
        importlib.reload(firefox_urls_module)
        importlib.reload(root_urls_module)
        redirects_util.redirectpatterns.clear()
        redirects_util.register(firefox_redirects_module.redirectpatterns)
        clear_url_caches()
        url["base_url"] = base_url
        assert_valid_url(**url)

    redirects_util.redirectpatterns.clear()
    redirects_util.redirectpatterns.extend(original_patterns)
    importlib.reload(firefox_redirects_module)
    importlib.reload(firefox_urls_module)
    importlib.reload(root_urls_module)
    clear_url_caches()


@pytest.mark.headless
@pytest.mark.nondestructive
@pytest.mark.django_db
@pytest.mark.parametrize("url", LOCALE_URLS)
def test_locale_url(url, base_url):
    url["base_url"] = base_url
    assert_valid_url(**url)
