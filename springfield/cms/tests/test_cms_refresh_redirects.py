# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for the ENABLE_CMS_REFRESH_REDIRECTS URL patterns.

These patterns (in springfield/firefox/urls.py) wrap download platform views
with prefer_cms so that a published CMS DownloadPage takes precedence over
the legacy Django/template view for the same URL.
"""

import importlib

from django.test import override_settings
from django.urls import clear_url_caches

import pytest

import springfield.firefox.urls as firefox_urls_module
import springfield.urls as root_urls_module
from springfield.cms.models import SimpleRichTextPage
from springfield.cms.tests.factories import DownloadIndexPageFactory, DownloadPageFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def cms_refresh_redirects_enabled():
    """Enable ENABLE_CMS_REFRESH_REDIRECTS and reload the URL conf to pick up the new patterns."""
    with override_settings(ENABLE_CMS_REFRESH_REDIRECTS=True):
        importlib.reload(firefox_urls_module)
        importlib.reload(root_urls_module)
        clear_url_caches()
        yield
    # Restore original URL patterns (setting is False again outside override_settings)
    importlib.reload(firefox_urls_module)
    importlib.reload(root_urls_module)
    clear_url_caches()


@pytest.fixture
def download_index_page(minimal_site):
    """Create a DownloadIndexPage as a child of the site root with slug 'download'.

    This matches the URL hierarchy expected by the download platform URLs:
    /download/android/, /download/ios/, etc.
    """
    root_page = SimpleRichTextPage.objects.first()
    return DownloadIndexPageFactory(parent=root_page, slug="download")


PLATFORM_PARAMS = pytest.mark.parametrize(
    "platform,url_path,slug",
    [
        ("android", "/en-US/download/android/", "android"),
        ("ios", "/en-US/download/ios/", "ios"),
        ("chromebook", "/en-US/download/chromebook/", "chromebook"),
        ("linux", "/en-US/download/linux/", "linux"),
        ("mac", "/en-US/download/mac/", "mac"),
        ("windows", "/en-US/download/windows/", "windows"),
    ],
)


@PLATFORM_PARAMS
def test_cms_content_served_when_download_page_exists(platform, url_path, slug, cms_refresh_redirects_enabled, download_index_page, client):
    """When a live CMS DownloadPage exists for the requested locale, it is served
    instead of the legacy Django view."""
    download_page = DownloadPageFactory(
        parent=download_index_page,
        slug=slug,
        platform=platform,
    )
    download_page.save_revision()
    download_page.publish(download_page.latest_revision)

    resp = client.get(url_path, follow=True)

    assert resp.status_code == 200
    assert resp.wsgi_request.is_cms_page is True


@PLATFORM_PARAMS
def test_django_view_served_when_no_cms_page_for_locale(platform, url_path, slug, cms_refresh_redirects_enabled, download_index_page, client):
    """When no CMS DownloadPage exists for the requested locale, the legacy
    Django view/template is served as a fallback."""
    # Create an en-US DownloadPage but no French translation
    download_page = DownloadPageFactory(
        parent=download_index_page,
        slug=slug,
        platform=platform,
    )
    download_page.save_revision()
    download_page.publish(download_page.latest_revision)

    # French locale has no DownloadPage, so prefer_cms falls back to the Django view.
    # The fr locale exists because minimal_site creates it via LocaleFactory.
    fr_url_path = url_path.replace("/en-US/", "/fr/", 1)
    resp = client.get(fr_url_path, follow=True)

    assert resp.status_code == 200
    assert resp.wsgi_request.is_cms_page is False
