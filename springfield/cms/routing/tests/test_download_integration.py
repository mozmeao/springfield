# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Routing adoption for DownloadPage."""

from types import SimpleNamespace

import pytest
from wagtail.models import Site

from springfield.cms.routing.models import RoutingRule
from springfield.cms.tests.factories import DownloadIndexPageFactory, DownloadPageFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def download():
    site = Site.objects.get(is_default_site=True)
    index = DownloadIndexPageFactory(parent=site.root_page, slug="download")
    android = DownloadPageFactory(parent=index, slug="android", platform="android")
    variant = DownloadPageFactory(parent=android, slug="china", platform="android")
    return SimpleNamespace(index=index, android=android, variant=variant)


def test_only_the_android_page_under_the_index_is_canonical(download):
    windows = DownloadPageFactory(parent=download.index, slug="windows", platform="windows")
    assert download.android.is_routing_canonical() is True
    assert download.variant.is_routing_canonical() is False
    assert windows.is_routing_canonical() is False


def test_a_nested_download_page_is_a_valid_target(download):
    RoutingRule(page=download.android, target=download.variant, match_all=True).full_clean()  # does not raise
