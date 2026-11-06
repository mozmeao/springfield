# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for settings"""

from importlib import reload
from unittest import mock

from django.conf import settings
from django.test import override_settings

import pytest

from springfield.settings.base import _get_media_cdn_hostname_for_storage_backend, _normalize_gtm_server_url, lazy_langs


@override_settings(DEV=False, PROD_LANGUAGES=("de", "fr", "nb-NO", "ja", "ja-JP-mac", "en-US", "en-GB"))
def test_lang_groups():
    # should not contain 'nb' and 'ja' group should contain 'ja'
    assert dict(settings.LANG_GROUPS) == {
        "ja": ["ja-JP-mac", "ja"],
        "en": ["en-US", "en-GB"],
    }


def test_rq_queue_names_are_test_specific():
    assert settings.RQ_DEFAULT_QUEUE == "test_default"
    assert settings.RQ_IMAGE_RENDITIONS_QUEUE == "test_image_renditions"
    assert settings.RQ_EMAIL_DEFAULT_QUEUE == "test_default"


def test_rq_queues_are_test_specific_when_redis_is_configured():
    # RQ_QUEUES is only populated when REDIS_URL is set, so reload the settings
    # with it set, as if the tests were being run with a local Redis available
    from springfield import settings as springfield_settings
    from springfield.settings import base as base_settings

    try:
        with mock.patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            reload(base_settings)
            reload(springfield_settings)

            assert springfield_settings.TASK_QUEUE_AVAILABLE is True
            assert springfield_settings.RQ_QUEUES == {
                "test_default": {"URL": "redis://redis:6379/0"},
                "test_image_renditions": {"URL": "redis://redis:6379/0"},
            }
            assert springfield_settings.RQ_DEFAULT_QUEUE == "test_default"
            assert springfield_settings.RQ_IMAGE_RENDITIONS_QUEUE == "test_image_renditions"
            assert springfield_settings.RQ_EMAIL_DEFAULT_QUEUE == "test_default"
    finally:
        # Restore the settings modules for any tests that use them later
        reload(base_settings)
        reload(springfield_settings)


@pytest.mark.parametrize(
    "media_url, expected_hostname",
    (
        ("https://www-dev.springfield.moz.works/media/cms/", "https://www-dev.springfield.moz.works"),
        ("https://www-dev.springfield.moz.works/some/future/assets/path/", "https://www-dev.springfield.moz.works"),
        ("https://www.springfield.moz.works/media/cms/", "https://www.springfield.moz.works"),
        ("https://www.firefox.com/media/cms/", "https://www.firefox.com"),
        ("/custom-media/", "/custom-media/"),  # this one is the default, used in local dev
    ),
)
def test_get_media_cdn_hostname(media_url, expected_hostname):
    assert _get_media_cdn_hostname_for_storage_backend(media_url) == expected_hostname


def test_catch_disallowed_redirect_middleware_enabled():
    middleware_path = "springfield.base.middleware.CatchDisallowedRedirect"
    assert middleware_path in settings.MIDDLEWARE


@override_settings(DEV=True)
def test_lazy_langs_skips_db_before_apps_ready(mocker):
    mocker.patch("springfield.settings.base.DEV_LANGUAGES", ["en-US", "de"])
    mocker.patch("springfield.settings.base.apps.ready", False)

    result = lazy_langs()
    assert result == [("en-US", "en-US"), ("de", "de")]


@override_settings(DEV=True)
def test_lazy_langs_uses_product_details_after_apps_ready(mocker):
    mocker.patch("springfield.settings.base.DEV_LANGUAGES", ["en-US", "de"])
    mocker.patch("springfield.settings.base.apps.ready", True)
    product_details = mocker.patch("product_details.product_details")
    product_details.languages = {
        "en-US": {"native": "English (US)"},
        "de": {"native": "Deutsch"},
    }

    result = lazy_langs()
    assert result == [("en-US", "English (US)"), ("de", "Deutsch")]


@pytest.mark.parametrize(
    "raw_url, expected_url",
    (
        ("https://gtm.firefox.com", "https://gtm.firefox.com"),
        ("https://gtm.firefox.com/", "https://gtm.firefox.com"),
        # A scheme-less value would resolve page-relative in the browser.
        ("gtm.firefox.com", "https://gtm.firefox.com"),
        ("gtm.firefox.com/", "https://gtm.firefox.com"),
        # Protocol-relative is not a valid CSP source expression.
        ("//gtm.firefox.com", "https://gtm.firefox.com"),
        # http:// would be mixed content on our https pages.
        ("http://gtm.firefox.com", "https://gtm.firefox.com"),
        ("http://gtm.firefox.com/", "https://gtm.firefox.com"),
        ("", ""),  # unset, which disables server-side GTM
        # A scheme with no host is treated as unset rather than becoming garbage.
        ("https://", ""),
        ("//", ""),
    ),
)
def test_normalize_gtm_server_url(raw_url, expected_url):
    assert _normalize_gtm_server_url(raw_url) == expected_url
