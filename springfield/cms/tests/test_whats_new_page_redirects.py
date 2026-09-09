# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Tests for the channel-aware WNP redirect behaviour.

When a user requests /LOCALE/whatsnew/VERSION/ and there is no version-specific
CMS WNP, we check for a channel-specific CMS WNP and 302 to it:
  - Nightly (a1 suffix)   → /LOCALE/whatsnew/nightly/?version=VERSION
  - Developer (a2 suffix) → /LOCALE/whatsnew/developer/?version=VERSION
  - Beta (beta suffix)    → /LOCALE/whatsnew/beta/?version=VERSION
  - Release               → /LOCALE/whatsnew/general/?version=VERSION

If no channel-specific CMS WNP exists for the locale (or its CMS fallback
locale), the static evergreen page is rendered instead.
"""

from django.test import override_settings
from django.utils import translation

import pytest
from wagtail.models import Locale, Site
from wagtail_localize.fields import get_translatable_fields

from springfield.cms.models import SimpleRichTextPage, WhatsNewPage2026
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
# Core redirect behavior
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


# ---------------------------------------------------------------------------
# What's New Index page redirects
# ---------------------------------------------------------------------------


def test_whats_new_version_cannot_be_overridden_per_locale():
    """The version identifies the Firefox release, so translators must not be able to
    override it in the translation editor."""
    version_field = next(field for field in get_translatable_fields(WhatsNewPage2026) if field.field_name == "version")

    assert version_field.is_synchronized(WhatsNewPage2026)
    assert not version_field.is_overridable(WhatsNewPage2026)


def test_whats_new_index_page_redirects_to_latest_whats_new(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    v123_page = WhatsNewPage2026Factory(parent=index_page, slug="123", version="123")
    v123_page.save()
    v124_page = WhatsNewPage2026Factory(parent=index_page, slug="124", version="124")
    v124_page.save()

    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v124_page.url)

    v125_page = WhatsNewPage2026Factory(parent=index_page, slug="125", version="125")
    v125_page.save()

    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v125_page.url)


def test_whats_new_index_page_excludes_general_page_from_latest_redirect(
    minimal_site,
    rf,
):
    """General WNP (version='general') must not be treated as the 'latest' version.
    The index page should redirect to the highest numeric version."""
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew-2")

    v150_page = WhatsNewPage2026Factory(parent=index_page, slug="150", version="150")
    v150_page.save()

    general_page = GeneralWhatsNewPage2026Factory(parent=index_page)
    general_page.save()
    # Multiple general pages exist simultaneously when new content is being experimented with.
    general_page_2 = GeneralWhatsNewPage2026Factory(parent=index_page, slug="general-2")
    general_page_2.save()

    _relative_url = index_page.relative_url(minimal_site)
    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v150_page.url)


def test_whats_new_index_page_redirects_to_home_if_no_children(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    request = rf.get(_relative_url)

    # No WhatsNewPage exists yet, so should redirect to the locale home page
    with translation.override("en-US"):
        response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"] == "/en-US/"


def test_whats_new_index_page_redirects_to_locale_appropriate_child(
    tiny_localized_site,
    rf,
):
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page

    pt_br_locale = Locale.objects.get(language_code="pt-BR")
    pt_br_root_page = en_us_root_page.get_translation(pt_br_locale)

    assert pt_br_root_page

    en_us_index_page = WhatsNewIndexPageFactory(parent=en_us_root_page, slug="whatsnew")
    en_us_index_page.save()

    pt_br_index_page = en_us_index_page.copy_for_translation(pt_br_locale)
    pt_br_index_page.title = "O que há de novo no Firefox"
    pt_br_index_page.save()
    pt_br_index_page.save_revision().publish()

    _en_us_relative_url = en_us_index_page.relative_url(tiny_localized_site)
    assert _en_us_relative_url == "/en-US/whatsnew/"

    _pt_br_relative_url = pt_br_index_page.relative_url(tiny_localized_site)
    assert _pt_br_relative_url == "/pt-BR/whatsnew/"

    en_us_v123_page = WhatsNewPage2026Factory(parent=en_us_index_page, slug="123", version="123")
    en_us_v123_page.save()
    en_us_v124_page = WhatsNewPage2026Factory(parent=en_us_index_page, slug="124", version="124")
    en_us_v124_page.save()

    pt_br_v123_page = en_us_v123_page.copy_for_translation(pt_br_locale)
    pt_br_v123_page.title = "O que tem de novo no Firefox 123"
    pt_br_v123_page.save_revision().publish()

    pt_br_v124_page = en_us_v124_page.copy_for_translation(pt_br_locale)
    pt_br_v124_page.title = "O que tem de novo no Firefox 124"
    pt_br_v124_page.save_revision().publish()

    pt_br_index_page.refresh_from_db()

    en_us_request = rf.get(_en_us_relative_url)

    response = en_us_index_page.specific.serve(en_us_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(en_us_v124_page.url)

    pt_br_request = rf.get(_pt_br_relative_url)
    response = pt_br_index_page.specific.serve(pt_br_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(pt_br_v124_page.url)
