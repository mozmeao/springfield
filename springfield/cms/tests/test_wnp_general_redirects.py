# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for the General WNP redirect behaviour (WT-1038).

When a user requests /LOCALE/whatsnew/VERSION/ and there is no version-specific
CMS WNP but a General WNP (slug='general') exists for the locale (or its CMS
fallback locale), we 302 to /LOCALE/whatsnew/general/?version=VERSION.
"""

from django.test import override_settings

import pytest
from wagtail.models import Locale, Site

from springfield.cms.models import SimpleRichTextPage
from springfield.cms.tests.factories import (
    GeneralWhatsNewPage2026Factory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def wnp_index_page(minimal_site):
    """WhatsNewIndexPage as a child of the site root (slug='whatsnew')."""
    root_page = SimpleRichTextPage.objects.first()
    return WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")


@pytest.fixture
def general_wnp(wnp_index_page):
    """A live General WNP (slug='general') under the whatsnew index in en-US."""
    page = GeneralWhatsNewPage2026Factory(parent=wnp_index_page)
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Core redirect behaviour
# ---------------------------------------------------------------------------


def test_redirects_to_general_wnp_when_version_page_missing(general_wnp, client):
    """302 to general WNP when no version-specific CMS page exists for the locale."""
    response = client.get("/en-US/whatsnew/999/")
    assert response.status_code == 302
    assert response["Location"] == "/en-US/whatsnew/general/?version=999"


def test_redirect_includes_version_param(general_wnp, client):
    """Redirect URL must include the incoming version as ?version=."""
    response = client.get("/en-US/whatsnew/151/")
    assert response.status_code == 302
    assert "version=151" in response["Location"]


def test_redirect_preserves_existing_querystring(general_wnp, client):
    """Existing querystring params are carried through alongside ?version=."""
    response = client.get("/en-US/whatsnew/151/?utm_source=foo&utm_campaign=bar")
    assert response.status_code == 302
    location = response["Location"]
    assert "version=151" in location
    assert "utm_source=foo" in location
    assert "utm_campaign=bar" in location


# ---------------------------------------------------------------------------
# No-redirect cases
# ---------------------------------------------------------------------------


def test_no_redirect_when_no_general_wnp_exists(wnp_index_page, client):
    """When no General WNP is published, the static evergreen page is rendered (200)."""
    response = client.get("/en-US/whatsnew/999/")
    assert response.status_code == 200


def test_no_redirect_for_non_cms_non_alias_locale(general_wnp, client):
    """A locale outside WAGTAIL_CONTENT_LANGUAGES and FALLBACK_LOCALES gets
    the static evergreen page — no General WNP redirect."""
    # zh-TW is not a CMS locale and has no FALLBACK_LOCALES entry pointing at one
    with override_settings(FALLBACK_LOCALES={}):
        response = client.get("/zh-TW/whatsnew/151/")
    assert response.status_code == 200


def test_version_specific_cms_page_served_directly(general_wnp, wnp_index_page, client):
    """When a live version-specific CMS WNP exists, prefer_cms serves it — no redirect."""
    version_page = WhatsNewPage2026Factory(parent=wnp_index_page, slug="151", version="151")
    version_page.save_revision().publish()
    response = client.get("/en-US/whatsnew/151/")
    assert response.status_code == 200
    assert "Location" not in response


# ---------------------------------------------------------------------------
# No redirect loop
# ---------------------------------------------------------------------------


def test_general_wnp_url_served_directly_without_loop(general_wnp, client):
    """/LOCALE/whatsnew/general/ does not match the 3-digit regex, so WhatsnewView
    is never called.  Wagtail's catch-all finds and serves the page as 200."""
    response = client.get("/en-US/whatsnew/general/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# CMS locale with a fallback (en-GB → en-US)
# ---------------------------------------------------------------------------


def test_cms_locale_with_fallback_redirects_when_only_fallback_has_general_wnp(
    general_wnp,
    wnp_index_page,
    client,
):
    """
    en-GB is a CMS locale AND has a fallback to en-US in FALLBACK_LOCALES.
    If en-GB has no General WNP but en-US does, we should still redirect to
    /en-GB/whatsnew/general/ so CMSLocaleFallbackMiddleware can transparently
    serve the en-US content at that URL.
    """
    with override_settings(
        FALLBACK_LOCALES={"en-GB": "en-US"},
        WAGTAIL_CONTENT_LANGUAGES=[("en-US", "English (US)"), ("en-GB", "English (GB)")],
    ):
        # general_wnp fixture publishes the General WNP in en-US only
        response = client.get("/en-GB/whatsnew/151/")

    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/en-GB/whatsnew/general/")
    assert "version=151" in location


# ---------------------------------------------------------------------------
# Alias locale redirect
# ---------------------------------------------------------------------------


def test_alias_locale_redirects_to_alias_url_when_fallback_has_general_wnp(
    tiny_localized_site,
    client,
):
    """
    pt-PT is an alias for pt-BR.  When pt-BR has a General WNP and there is no
    version-specific WNP for pt-PT, we redirect to /pt-PT/whatsnew/general/ —
    not /pt-BR/whatsnew/general/.  Wagtail's existing alias-locale machinery then
    transparently serves the pt-BR content.
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page
    pt_br_locale = Locale.objects.get(language_code="pt-BR")

    en_us_index = WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew")
    en_us_index.save()

    pt_br_index = en_us_index.copy_for_translation(pt_br_locale)
    pt_br_index.save_revision().publish()

    en_us_general = GeneralWhatsNewPage2026Factory(parent=en_us_index)
    en_us_general.save_revision().publish()

    pt_br_general = en_us_general.copy_for_translation(pt_br_locale)
    pt_br_general.save_revision().publish()

    with override_settings(
        FALLBACK_LOCALES={"pt-PT": "pt-BR"},
        WAGTAIL_CONTENT_LANGUAGES=[("en-US", "English (US)"), ("pt-BR", "Portuguese (Brazil)")],
    ):
        response = client.get("/pt-PT/whatsnew/151/")

    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/pt-PT/whatsnew/general/")
    assert "version=151" in location
