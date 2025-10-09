# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

import pytest
from wagtail.models import Locale, Page

from springfield.cms.models.pages import SimpleRichTextPage

User = get_user_model()


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_requires_staff_authentication(site_with_en_de_fr_it_homepages):
    """Test that the view requires staff authentication."""
    client = Client()
    url = reverse("cms:translations_list")

    # Test without login
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login

    # Test with non-staff user
    User = get_user_model()
    regular_user = User.objects.create_user(username="regular", email="regular@example.com", password="testpass", is_staff=False)
    client.force_login(regular_user)
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_accessible_by_staff(staff_user, site_with_en_de_fr_it_homepages):
    """Test that staff users can access the view."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    response = client.get(url)
    assert response.status_code == 200
    # Verify that the filter form is included in the context.
    assert "filter_form" in response.context
    assert response.context["filter_form"].__class__.__name__ == "TranslationsFilterForm"


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_no_pages_scenario(staff_user, site_with_en_de_fr_it_homepages):
    """Test view when there are no pages (except root pages)."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    response = client.get(url)
    assert response.status_code == 200
    assert b"No pages found." in response.content
    assert len(response.context["pages_with_translations"]) == 0


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_single_page_no_translations(staff_user, site_with_en_de_fr_it_homepages):
    """Test view with a single page that has no translations."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get locale and home page
    en_locale = Locale.objects.get(language_code="en-US")
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")

    # Create a single page with no translations
    single_page = SimpleRichTextPage(title="Single Page", slug="single-page", locale=en_locale, content="Test content")
    en_home.add_child(instance=single_page)
    single_page.save_revision().publish()

    response = client.get(url)
    assert response.status_code == 200

    # There should be 1 page in the response (the single_page).
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 1
    single_page_data = pages_with_translations[0]
    assert single_page_data is not None
    assert single_page_data["page"] == single_page.page_ptr
    assert len(single_page_data["translations"]) == 0


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_pages_from_different_initial_locales(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test pages that originate from different locales with translations."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get the pages created by the fixture
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    de_page = SimpleRichTextPage.objects.get(locale__language_code="de", slug="german-page")
    fr_page = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="french-page")

    # Get translations
    de_translation = SimpleRichTextPage.objects.get(locale__language_code="de", slug="english-page")
    fr_translation = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="english-page")
    it_translation = SimpleRichTextPage.objects.get(locale__language_code="it", slug="french-page")

    response = client.get(url)
    assert response.status_code == 200

    # There should be 3 pages in the response (not their translations).
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr, de_page.page_ptr, fr_page.page_ptr])

    # Verify the translations in the data are correct.
    for page_data in pages_with_translations:
        translation_urls = [t["view_url"] for t in page_data["translations"]]
        if page_data["page"] == en_page.page_ptr:
            assert set(translation_urls) == set([de_translation.url, fr_translation.url])
        elif page_data["page"] == de_page.page_ptr:
            assert translation_urls == []
        elif page_data["page"] == fr_page.page_ptr:
            assert translation_urls == [it_translation.url]


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_draft_and_published_pages(staff_user, site_with_en_de_fr_it_homepages):
    """Test that both draft and published pages are shown."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get locales and home page
    en_locale = Locale.objects.get(language_code="en-US")
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")

    # Create published page
    published_page = SimpleRichTextPage(title="Published Page", slug="published-page", locale=en_locale, content="Published content")
    en_home.add_child(instance=published_page)
    published_page.save_revision().publish()

    # Create draft page
    draft_page = SimpleRichTextPage(title="Draft Page", slug="draft-page", locale=en_locale, content="Draft content")
    en_home.add_child(instance=draft_page)
    draft_page.save_revision()  # Don't publish

    response = client.get(url)
    assert response.status_code == 200

    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([published_page.page_ptr, draft_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_context_data_structure(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test that the context data has the correct structure."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get the English page created by the fixture
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    # Get the German translation of the English page
    de_translation = SimpleRichTextPage.objects.get(locale__language_code="de", slug="english-page")
    # Get the French translation of the English page
    fr_translation = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="english-page")

    response = client.get(url)
    assert response.status_code == 200

    pages_with_translations = response.context["pages_with_translations"]
    assert isinstance(pages_with_translations, list)

    # Find the English page in the results
    en_page_data = next((p for p in pages_with_translations if p["page"] == en_page.page_ptr), None)
    assert en_page_data is not None

    # Check structure of page data
    assert en_page_data["page"] == en_page.page_ptr
    assert en_page_data["edit_url"] == f"/cms-admin/pages/{en_page.id}/edit/"
    assert en_page_data["view_url"] == en_page.get_url()
    assert "translations" in en_page_data
    assert len(en_page_data["translations"]) == 2  # German and French

    # Check translation structure
    translation_locales = {t["locale"] for t in en_page_data["translations"]}
    assert translation_locales == {"de", "fr"}

    for translation_data in en_page_data["translations"]:
        assert "locale" in translation_data
        assert "edit_url" in translation_data
        assert "view_url" in translation_data
        assert "percent_translated" in translation_data
    expected_en_page_data = {
        "page": en_page.page_ptr,
        "translations": [
            {
                "locale": "de",
                "edit_url": f"/cms-admin/pages/{de_translation.id}/edit/",
                "view_url": de_translation.get_url(),
                "percent_translated": 0,
            },
            {
                "locale": "fr",
                "edit_url": f"/cms-admin/pages/{fr_translation.id}/edit/",
                "view_url": fr_translation.get_url(),
                "percent_translated": 0,
            },
        ],
        "edit_url": f"/cms-admin/pages/{en_page.id}/edit/",
        "view_url": en_page.get_url(),
    }
    assert en_page_data == expected_en_page_data


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_excludes_root_pages(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test that root pages (depth <= 2) are excluded."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    response = client.get(url)
    pages_with_translations = response.context["pages_with_translations"]

    # Check that no root pages are included
    for page_data in pages_with_translations:
        page = page_data["page"]
        assert page.depth > 2, f"Page '{page.title}' with depth {page.depth} should be excluded"


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_original_language_filter(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by a specific original_language."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get the pages created by the fixture
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    de_page = SimpleRichTextPage.objects.get(locale__language_code="de", slug="german-page")
    fr_page = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="french-page")

    # Test: Filter by German
    response = client.get(url, {"original_language": "de"})
    pages_with_translations = response.context["pages_with_translations"]
    # The response should contain only the de_page (not the de_translation of the English page).
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([de_page.page_ptr])

    # Test: Filter by English
    response = client.get(url, {"original_language": "en-US"})
    pages_with_translations = response.context["pages_with_translations"]
    # The response should contain only the en_page.
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])
    # The page data should show the German translation of the en_page.
    page_data = pages_with_translations[0]
    translation_locales = [t["locale"] for t in page_data["translations"]]
    assert len(translation_locales) == 2
    assert "de" in translation_locales
    assert "fr" in translation_locales

    # Test: Filter by invalid language
    # The response should contain no results.
    response = client.get(url, {"original_language": "invalid-code"})
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 0

    # Test: Filter by blank value
    # The response should contain all pages.
    response = client.get(url, {"original_language": ""})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr, de_page.page_ptr, fr_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_exists_in_language_filter(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by exists_in_language (whether a page exists in a particular language)."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get the pages created by the fixture
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    de_page = SimpleRichTextPage.objects.get(locale__language_code="de", slug="german-page")
    fr_page = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="french-page")

    # Test: Filter by exists in English
    # The response should contain en_page, since it is in English. No other
    # page has an English translation
    response = client.get(url, {"exists_in_language": "en-US"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])

    # Test: Filter by exists in German
    # The response should contain:
    #   - de_page, since it is in German
    #   - en_page, since it has a German translation
    response = client.get(url, {"exists_in_language": "de"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([de_page.page_ptr, en_page.page_ptr])

    # Test: Filter by exists in Italian
    # The response should contain:
    #   - fr_page, since it has an Italian translation
    response = client.get(url, {"exists_in_language": "it"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([fr_page.page_ptr])

    # Test: Filter by exists in French
    # The response should contain:
    #   - fr_page, since it is in French
    #   - en_page, since it has a French translation
    response = client.get(url, {"exists_in_language": "fr"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr, fr_page.page_ptr])

    # Test: Filter by invalid language
    # The response should contain no results.
    response = client.get(url, {"exists_in_language": "invalid-code"})
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 0

    # Test: Filter by blank value
    # The response should contain all pages.
    response = client.get(url, {"exists_in_language": ""})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr, de_page.page_ptr, fr_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)  # Disable SSO login for this test
@pytest.mark.django_db
def test_translations_list_view_multiple_filters_together(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test using both original_language and exists_in_language filters together."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Get the pages created by the fixture
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    # de_page = SimpleRichTextPage.objects.get(slug="german-page")
    fr_page = SimpleRichTextPage.objects.get(locale__language_code="fr", slug="french-page")

    # Test: original_language=en-US AND exists_in_language=de
    # The response should contain:
    #   - en_page, since it is originally in English and has a German translation
    response = client.get(url, {"original_language": "en-US", "exists_in_language": "de"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])

    # Test: original_language=de AND exists_in_language=fr
    # The response should contain no results
    response = client.get(url, {"original_language": "de", "exists_in_language": "fr"})
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 0

    # Test: original_language=fr AND exists_in_language=fr
    # The response should contain:
    #   - fr_page, since it is originally in French
    response = client.get(url, {"original_language": "fr", "exists_in_language": "fr"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([fr_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,  # Disable SSO login for this test
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),  # Disable SSO login for this test
    WAGTAIL_CONTENT_LANGUAGES=[  # Define all languages in Wagtail
        ("en-US", "English (US)"),
        ("de", "German"),
        ("fr", "French"),
        ("it", "Italian"),
    ],
)
@pytest.mark.django_db
def test_translations_list_view_exists_in_all_languages_filter(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by 'All languages' option (pages that exist in every configured language)."""
    from springfield.cms.forms import TranslationsFilterForm

    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Currently, no page exists in all languages.
    response = client.get(url, {"exists_in_language": TranslationsFilterForm.ALL_LANGUAGES})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert len(pages_in_response) == 0

    # Translate the en_page to the remaining languages.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    en_page_languages = Page.objects.filter(translation_key=en_page.translation_key).values_list("locale__language_code", flat=True)
    for language_code, language_name in settings.WAGTAIL_CONTENT_LANGUAGES:
        if language_code not in en_page_languages:
            locale, _ = Locale.objects.get_or_create(language_code=language_code)
            translation_page = en_page.copy_for_translation(locale)
            translation_page.title = f"{language_name} Translation"
            translation_page.save_revision().publish()

    # Now, the en_page exists in all languages.
    response = client.get(url, {"exists_in_language": TranslationsFilterForm.ALL_LANGUAGES})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert len(pages_in_response) == 1
    assert set(pages_in_response) == set([en_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,  # Disable SSO login for this test
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),  # Disable SSO login for this test
    WAGTAIL_CONTENT_LANGUAGES=[  # Define all languages in Wagtail
        ("en-US", "English (US)"),
        ("de", "German"),
        ("fr", "French"),
        ("it", "Italian"),
    ],
    WAGTAIL_CORE_LANGUAGES=[  # Set core languages to a subset of WAGTAIL_CONTENT_LANGUAGES
        ("en-US", "English (US)"),
        ("it", "Italian"),
    ],
)
@pytest.mark.django_db
def test_translations_list_view_exists_in_core_languages_filter(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by 'Core languages' option (pages that exist in every configured core language)."""
    from springfield.cms.forms import TranslationsFilterForm

    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Currently, no page exists in all languages.
    response = client.get(url, {"exists_in_language": TranslationsFilterForm.CORE_LANGUAGES})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert len(pages_in_response) == 0

    # Translate the en_page to the remaining core languages.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")
    en_page_languages = Page.objects.filter(translation_key=en_page.translation_key).values_list("locale__language_code", flat=True)
    for language_code, language_name in settings.WAGTAIL_CORE_LANGUAGES:
        if language_code not in en_page_languages:
            locale, _ = Locale.objects.get_or_create(language_code=language_code)
            translation_page = en_page.copy_for_translation(locale)
            translation_page.title = f"{language_name} Translation"
            translation_page.save_revision().publish()

    # Now, the en_page exists in all core languages.
    response = client.get(url, {"exists_in_language": TranslationsFilterForm.CORE_LANGUAGES})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert len(pages_in_response) == 1
    assert set(pages_in_response) == set([en_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_search_by_title(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test search functionality by page title."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    de_original_page = SimpleRichTextPage.objects.get(title="German Original")

    # Search for "German Original" should return the de_original_page.
    response = client.get(url, {"search": "German Original"})
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([de_original_page.page_ptr])

    # Searching for "Original" should return all pages matching "Original".
    response = client.get(url, {"search": "Original"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    expected_pages = SimpleRichTextPage.objects.filter(title__icontains="Original")
    assert set(pages_in_response) == set(page.page_ptr for page in expected_pages)


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_search_by_slug(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test search functionality by page slug."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    en_page = SimpleRichTextPage.objects.get(
        title="English Original",
        slug="english-page",
        locale__language_code="en-US",
    )

    # Search for "english-page" should return the english-page
    response = client.get(url, {"search": "english-page"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_search_with_filters(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test that search works together with filters."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    en_page = SimpleRichTextPage.objects.get(
        title="English Original",
        slug="english-page",
        locale__language_code="en-US",
    )
    fr_page = SimpleRichTextPage.objects.get(
        title="French Original",
        slug="french-page",
        locale__language_code="fr",
    )
    de_page = SimpleRichTextPage.objects.get(
        title="German Original",
        slug="german-page",
        locale__language_code="de",
    )

    # Searching for "page" returns multiple results.
    response = client.get(url, {"search": "page"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr, fr_page.page_ptr, de_page.page_ptr])

    # Searching for "page" and filtering by original language "en-US" returns 1 result.
    response = client.get(url, {"search": "page", "original_language": "en-US"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])

    # Searching for "page" and filtering by original language "en-US" and translation_key returns 1 result.
    response = client.get(
        url,
        {"search": "page", "original_language": "en-US", "translation_key": str(en_page.translation_key)},
    )
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_search_case_insensitive(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test that search is case insensitive."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    en_page = SimpleRichTextPage.objects.get(
        title="English Original",
        slug="english-page",
        locale__language_code="en-US",
    )

    # Search for "ENGLISH" (uppercase) should return the en_page.
    response = client.get(url, {"search": "ENGLISH"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_filter_by_translation_key(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by translation key."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    en_page = SimpleRichTextPage.objects.get(
        title="English Original",
        slug="english-page",
        locale__language_code="en-US",
    )
    de_page = SimpleRichTextPage.objects.get(
        title="German Original",
        slug="german-page",
        locale__language_code="de",
    )

    # Filtering by en_page's translation_key should return only en_page.
    response = client.get(url, {"translation_key": str(en_page.translation_key)})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([en_page.page_ptr])

    # Filtering by de_page's translation_key should return only de_page.
    response = client.get(url, {"translation_key": str(de_page.translation_key)})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    pages_in_response = [p["page"] for p in pages_with_translations]
    assert set(pages_in_response) == set([de_page.page_ptr])


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_filter_by_nonexistent_translation_key(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by a translation key that doesn't exist."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Filtering by a non-existent translation key should return no results.
    response = client.get(url, {"translation_key": str(uuid.uuid4())})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 0


@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
@pytest.mark.django_db
def test_translations_list_view_filter_by_invalid_translation_key(staff_user, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test filtering by an invalid translation key."""
    client = Client()
    client.force_login(staff_user)
    url = reverse("cms:translations_list")

    # Filtering by an invalid translation key should return no results.
    response = client.get(url, {"translation_key": "not-a-uuid"})
    assert response.status_code == 200
    pages_with_translations = response.context["pages_with_translations"]
    assert len(pages_with_translations) == 0
