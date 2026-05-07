# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for the channel-aware WNP redirect behaviour.

When a user requests /LOCALE/whatsnew/VERSION/ and there is no version-specific
CMS WNP, we check for a channel-specific CMS WNP and 302 to it:
  - Nightly (a1 suffix)  → /LOCALE/whatsnew/nightly/?version=VERSION
  - Developer (a2 suffix) → /LOCALE/whatsnew/developer/?version=VERSION
  - Beta (b/beta suffix) → /LOCALE/whatsnew/beta/?version=VERSION
  - Release              → /LOCALE/whatsnew/general/?version=VERSION

If no channel-specific CMS WNP exists for the locale (or its CMS fallback
locale), the static evergreen page is rendered instead.
"""

from django.test import override_settings

import pytest
from wagtail.models import Locale, Site

from springfield.cms.models import SimpleRichTextPage
from springfield.cms.tests.factories import (
    BetaWhatsNewPage2026Factory,
    DeveloperWhatsNewPage2026Factory,
    GeneralWhatsNewPage2026Factory,
    NightlyWhatsNewPage2026Factory,
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


@pytest.fixture
def nightly_wnp(wnp_index_page):
    """A live Nightly WNP (slug='nightly') under the whatsnew index in en-US."""
    page = NightlyWhatsNewPage2026Factory(parent=wnp_index_page)
    page.save_revision().publish()
    return page


@pytest.fixture
def developer_wnp(wnp_index_page):
    """A live Developer WNP (slug='developer') under the whatsnew index in en-US."""
    page = DeveloperWhatsNewPage2026Factory(parent=wnp_index_page)
    page.save_revision().publish()
    return page


@pytest.fixture
def beta_wnp(wnp_index_page):
    """A live Beta WNP (slug='beta') under the whatsnew index in en-US."""
    page = BetaWhatsNewPage2026Factory(parent=wnp_index_page)
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


# ---------------------------------------------------------------------------
# Channel-specific redirects (nightly, developer, beta)
# ---------------------------------------------------------------------------


def test_nightly_redirects_to_nightly_wnp(nightly_wnp, client):
    """302 to nightly WNP when version ends with a1 and a nightly CMS page exists."""
    response = client.get("/en-US/whatsnew/152.0a1/")
    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/en-US/whatsnew/nightly/")
    assert "version=152.0a1" in location


def test_developer_redirects_to_developer_wnp(developer_wnp, client):
    """302 to developer WNP when version ends with a2 and a developer CMS page exists."""
    response = client.get("/en-US/whatsnew/152.0a2/")
    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/en-US/whatsnew/developer/")
    assert "version=152.0a2" in location


def test_beta_redirects_to_beta_wnp_with_beta_suffix(beta_wnp, client):
    """302 to beta WNP when version ends with 'beta' and a beta CMS page exists."""
    response = client.get("/en-US/whatsnew/152.0beta/")
    assert response.status_code == 302
    location = response["Location"]
    assert location.startswith("/en-US/whatsnew/beta/")
    assert "version=152.0beta" in location


# ---------------------------------------------------------------------------
# Channel-specific fallback to static evergreen pages
# ---------------------------------------------------------------------------


def test_nightly_falls_back_to_static_when_no_nightly_wnp(wnp_index_page, client):
    """When no nightly CMS WNP is published, the static nightly evergreen page renders."""
    response = client.get("/en-US/whatsnew/152.0a1/")
    assert response.status_code == 200
    assert "Location" not in response


def test_developer_falls_back_to_static_when_no_developer_wnp(wnp_index_page, client):
    """When no developer CMS WNP is published, the static developer evergreen page renders."""
    response = client.get("/en-US/whatsnew/152.0a2/")
    assert response.status_code == 200
    assert "Location" not in response


def test_beta_falls_back_to_static_when_no_beta_wnp(wnp_index_page, client):
    """When no beta CMS WNP is published, the static release evergreen page renders."""
    response = client.get("/en-US/whatsnew/152.0beta/")
    assert response.status_code == 200
    assert "Location" not in response


def test_nightly_does_not_redirect_to_general_wnp(general_wnp, client):
    """A nightly version does not redirect to the general WNP even if one exists."""
    response = client.get("/en-US/whatsnew/152.0a1/")
    assert response.status_code == 200
    assert "Location" not in response


def test_developer_does_not_redirect_to_general_wnp(general_wnp, client):
    """A developer version does not redirect to the general WNP even if one exists."""
    response = client.get("/en-US/whatsnew/152.0a2/")
    assert response.status_code == 200
    assert "Location" not in response


def test_beta_does_not_redirect_to_general_wnp(general_wnp, client):
    """A beta version does not redirect to the general WNP even if one exists."""
    response = client.get("/en-US/whatsnew/152.0beta/")
    assert response.status_code == 200
    assert "Location" not in response


# ---------------------------------------------------------------------------
# No redirect loop for channel slugs
# ---------------------------------------------------------------------------


def test_nightly_wnp_url_served_directly_without_loop(nightly_wnp, client):
    """/LOCALE/whatsnew/nightly/ does not match the version URL patterns, so
    WhatsnewView is never called.  Wagtail's catch-all serves the page as 200."""
    response = client.get("/en-US/whatsnew/nightly/")
    assert response.status_code == 200


def test_developer_wnp_url_served_directly_without_loop(developer_wnp, client):
    """/LOCALE/whatsnew/developer/ does not match the version URL patterns."""
    response = client.get("/en-US/whatsnew/developer/")
    assert response.status_code == 200


def test_beta_wnp_url_served_directly_without_loop(beta_wnp, client):
    """/LOCALE/whatsnew/beta/ does not match the version URL patterns."""
    response = client.get("/en-US/whatsnew/beta/")
    assert response.status_code == 200
