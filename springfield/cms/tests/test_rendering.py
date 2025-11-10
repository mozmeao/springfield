# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Test the way Wagtail pages are handled by lib.l10n_utils.render

# The pytest fixtures used to run these tests are defined in springfield/cms/tests/conftest.py

from django.conf import settings

import pytest
from wagtail.models import Locale, Page, Site

from lib import l10n_utils
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


def test_mixed_case_locale_serves_correct_page(client, minimal_site):
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
    # Create en-GB locale (mixed-case country code).
    en_gb_locale = LocaleFactory(language_code="en-GB")
    assert en_gb_locale.language_code == "en-GB"  # Verify mixed-case
    # Create es-ES locale (mixed-case country code).
    es_es_locale = LocaleFactory(language_code="es-ES")
    assert es_es_locale.language_code == "es-ES"  # Verify mixed-case

    # Get the existing en-US page from minimal_site fixture
    en_us_page = Page.objects.filter(locale__language_code="en-US", slug="test-page").first()

    # If no page exists, create one
    if en_us_page is None:
        site = Site.objects.get(is_default_site=True)
        root_page = site.root_page

        en_us_page = SimpleRichTextPageFactory(
            title="Test Page",
            slug="test-page",
            parent=root_page,
            content="This is the US English version",
        )

    en_us_page = en_us_page.specific
    assert en_us_page is not None
    assert en_us_page.locale.language_code == "en-US"

    # Create en-GB translation with distinctive content
    en_gb_page = en_us_page.copy_for_translation(en_gb_locale)
    en_gb_page.title = "Test Page (British)"
    en_gb_page.content = "This is the British English version"
    en_gb_page.save()
    rev = en_gb_page.save_revision()
    en_gb_page.publish(rev)

    assert en_gb_page.locale.language_code == "en-GB"
    assert en_gb_page.id != en_us_page.id
    assert en_gb_page.title == "Test Page (British)"

    # Make a request to the en-GB URL
    # This goes through all middleware and Wagtail's routing
    response = client.get(en_gb_page.url)

    # Verify we got a successful response
    assert response.status_code == 200

    # Verify that the expected language and content are in the HTML.
    html_content = response.content.decode()
    assert 'lang="en-GB"' in html_content, "Expected lang='en-GB' in HTML"
    assert "Test Page (British)" in html_content, (
        f"Expected 'Test Page (British)' in response.\n"
        f"DB page title: {en_gb_page.title}\n"
        f"URL requested: {en_gb_page.url}\n"
        f"Response contains: {html_content[:500]}"
    )
    assert "This is the British English version" in html_content, "Expected en-GB content in response"

    # Create en-GB translation with distinctive content
    es_es_page = en_us_page.copy_for_translation(es_es_locale)
    es_es_page.title = "Página de prueba"
    es_es_page.content = "Esta es la versión en español"
    es_es_page.save()
    rev = es_es_page.save_revision()
    es_es_page.publish(rev)

    assert es_es_page.locale.language_code == "es-ES"

    # GET the es-ES page.
    response = client.get(es_es_page.url)

    # Verify that the expected language and content are in the HTML.
    assert response.status_code == 200
    html_content = response.content.decode()
    assert 'lang="es-ES"' in html_content, "Expected lang='es-ES' in HTML"
    assert "Página de prueba" in html_content, "Expected Spanish title in response"
    assert "Esta es la versión en español" in html_content, "Expected Spanish content in response"
