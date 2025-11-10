# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Test the way Wagtail pages are handled by lib.l10n_utils.render

# The pytest fixtures used to run these tests are defined in springfield/cms/tests/conftest.py

from django.conf import settings
from django.test import override_settings

import pytest
from wagtail.coreutils import get_content_languages
from wagtail.models import Locale, Page, Site

from lib import l10n_utils
from springfield.base.i18n import normalize_language
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

pytestmark = [
    pytest.mark.django_db,
]


def test_locale_redirect_logic_is_skipped_for_cms_page(
    minimal_site,
    mocker,
    rf,
):
    "Confirm that CMS pages with the lang code in the path get served fine"

    mocker.patch("lib.l10n_utils.redirect_to_locale")
    mocker.patch("lib.l10n_utils.redirect_to_best_locale")

    page = Page.objects.last().specific

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test-page/"
    request = rf.get(_relative_url)

    resp = page.serve(request)
    assert "Test Page" in resp.text

    l10n_utils.redirect_to_locale.assert_not_called()
    l10n_utils.redirect_to_best_locale.assert_not_called()


def test_locale_redirect_will_work_for_cms_pages(
    minimal_site,
    mocker,
    rf,
):
    """Confirm that CMS pages with the lang code in the path get
    redirected before being served fine"""

    redirect_to_locale_spy = mocker.spy(l10n_utils, "redirect_to_locale")
    redirect_to_best_locale_spy = mocker.spy(l10n_utils, "redirect_to_best_locale")

    page = Page.objects.last().specific

    assert page.url_path == "/test-page/"  # i.e., no lang code
    request = rf.get(page.url_path)

    resp = page.serve(request)

    assert resp.headers["location"] == "/en-US/test-page/"
    assert redirect_to_locale_spy.call_count == 1
    assert redirect_to_best_locale_spy.call_count == 0


def test_locale_redirect_will_work_for_cms_pages__default_locale_not_available(
    minimal_site,
    mocker,
    rf,
):
    redirect_to_locale_spy = mocker.spy(l10n_utils, "redirect_to_locale")
    redirect_to_best_locale_spy = mocker.spy(l10n_utils, "redirect_to_best_locale")

    page = Page.objects.last().specific
    fr_locale = Locale.objects.get(language_code="fr")

    assert settings.LANGUAGE_CODE != fr_locale.language_code

    page.locale = fr_locale
    page.save()

    assert page.url_path == "/test-page/"  # i.e., no lang code
    request = rf.get(page.url_path)

    resp = page.serve(request)

    assert resp.headers["location"] == "/fr/test-page/"  # NB not en-US
    assert redirect_to_locale_spy.call_count == 1
    assert redirect_to_best_locale_spy.call_count == 1


@pytest.mark.parametrize("serving_method", ("serve", "serve_preview"))
def test_locales_are_drawn_from_page_translations(minimal_site, rf, serving_method):
    assert Locale.objects.count() == 2  # en-US and fr
    fr_locale = Locale.objects.get(language_code="fr")

    page = Page.objects.last().specific
    fr_page = page.copy_for_translation(fr_locale)
    fr_page.title = "FR test page"
    rev = fr_page.save_revision()
    fr_page.publish(rev)
    assert fr_page.locale.language_code == "fr"

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test-page/"
    request = rf.get(_relative_url)

    resp = getattr(page, serving_method)(request, mode_name="irrelevant")
    page_content = resp.text
    assert "Test Page" in page_content
    assert '<option lang="en-US" value="en-US" selected>English</option>' in page_content
    assert '<option lang="fr" value="fr">Français</option>' in resp.text
    assert '<option lang="en-GB" value="en-US">English (British) </option>' not in page_content


@override_settings(
    WAGTAIL_I18N_ENABLED=True,
    LANGUAGES=[
        ("en-US", "English (US)"),
        ("en-GB", "English (GB)"),
        ("es-ES", "Spanish (Spain)"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
    ],
    WAGTAIL_CONTENT_LANGUAGES=[
        ("en-US", "English (US)"),
        ("en-GB", "English (GB)"),
        ("es-ES", "Spanish (Spain)"),
        ("es", "Spanish"),
        ("fr", "French"),
        ("de", "German"),
    ],
    LANGUAGE_URL_MAP_WITH_FALLBACKS={
        "en-US": "en-US",
        "en-GB": "en-GB",
        "es-ES": "es-ES",
        "es": "es",
        "fr": "fr",
        "de": "de",
        "en": "en-US",
    },
)
def test_mixed_case_locale_serves_correct_page(client):
    """
    Test that pages with mixed-case locale codes (e.g., en-GB) are served correctly.

    This test verifies that the SpringfieldLocale.get_active() implementation
    properly normalizes lowercase language codes from Django (e.g., 'en-gb') to
    mixed-case codes (e.g., 'en-GB') so that Wagtail finds the correct locale
    and serves the correct page translation.

    Without the fix, requesting /en-GB/test-page/ would serve the en-US page
    (fallback) instead of the en-GB page because Django's translation.get_language()
    returns lowercase 'en-gb', which doesn't match the Locale record 'en-GB'.
    """
    # Clear the cache for get_content_languages() so it picks up our override
    get_content_languages.cache_clear()

    # Test that normalize_language works correctly with our overrides
    normalized_en_gb = normalize_language("en-gb")
    assert normalized_en_gb == "en-GB", f"normalize_language should return 'en-GB' but got '{normalized_en_gb}'"

    # Set up locales - similar to tiny_localized_site fixture
    en_us_locale = Locale.objects.get(language_code="en-US")
    en_gb_locale = LocaleFactory(language_code="en-GB")
    es_es_locale = LocaleFactory(language_code="es-ES")

    assert en_gb_locale.language_code == "en-GB"
    assert es_es_locale.language_code == "es-ES"

    # Get the site - has en-US root, but we'll create translated roots.
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    # Translate the root to create locale-specific page trees.
    en_gb_root = en_us_root.copy_for_translation(en_gb_locale)
    # Publish the translated root so Wagtail uses it.
    rev = en_gb_root.save_revision()
    en_gb_root.publish(rev)

    es_es_root = en_us_root.copy_for_translation(es_es_locale)
    # Publish the translated root so Wagtail uses it.
    rev = es_es_root.save_revision()
    es_es_root.publish(rev)

    # Create pages in each tree.
    en_us_page = SimpleRichTextPageFactory(
        title="Test Page US Version",
        slug="test-page",
        parent=en_us_root,
        locale=en_us_locale,
        content="This is the US English version UNIQUE_US_MARKER",
    )

    # Create en-GB translation.
    en_gb_page = en_us_page.copy_for_translation(en_gb_locale)
    en_gb_page.title = "Test Page GB Version"
    en_gb_page.content = "This is the British English version UNIQUE_GB_MARKER"
    en_gb_page.save()
    rev = en_gb_page.save_revision()
    en_gb_page.publish(rev)

    # Verify the structure - same slug but different url_path (separate trees like production)
    assert en_gb_page.slug == en_us_page.slug == "test-page"
    assert en_us_page.url_path != en_gb_page.url_path
    assert "/home/" in en_us_page.url_path
    assert "/home-en-GB/" in en_gb_page.url_path or "/home-" in en_gb_page.url_path

    # Make a request to the en-GB URL
    response = client.get(en_gb_page.url)

    # Verify we got a successful response
    assert response.status_code == 200

    html_content = response.content.decode()
    # Check for GB-specific content (unique marker that only exists in en-GB page)
    assert "UNIQUE_GB_MARKER" in html_content, "en-GB page content not found - en-US page was served instead"
    assert "Test Page GB Version" in html_content, "en-GB title not found"
    # Verify we're NOT getting the en-US page content (would indicate the bug)
    assert "UNIQUE_US_MARKER" not in html_content, "Found en-US content when requesting en-GB URL"
    assert "Test Page US Version" not in html_content, "Found en-US title when requesting en-GB URL"

    # Create es-ES translation with distinctive content.
    # The es-ES page should have SAME url_path but a different locale.
    es_es_page = en_us_page.copy_for_translation(es_es_locale)
    es_es_page.title = "Página de prueba ES"
    es_es_page.content = "Esta es la versión en español UNIQUE_ES_MARKER"
    es_es_page.save()
    rev = es_es_page.save_revision()
    es_es_page.publish(rev)

    assert es_es_page.locale.language_code == "es-ES"
    assert es_es_page.slug == "test-page"

    # Test the es-ES page.
    response = client.get(es_es_page.url)
    assert response.status_code == 200

    html_content = response.content.decode()
    # Verify ES-specific content is served (not the en-US fallback)
    assert "UNIQUE_ES_MARKER" in html_content, "es-ES page content not found - en-US page was served instead"
    assert "Página de prueba ES" in html_content, "es-ES title not found"
    # Verify we're NOT getting the en-US page content
    assert "UNIQUE_US_MARKER" not in html_content, "Found en-US content when requesting es-ES URL"
    assert "Test Page US Version" not in html_content, "Found en-US title when requesting es-ES URL"
