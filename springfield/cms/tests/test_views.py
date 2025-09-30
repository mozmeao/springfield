# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wagtail.models import Locale, Page
from wagtail.test.utils import WagtailTestUtils

from springfield.cms.models.pages import SimpleRichTextPage

User = get_user_model()


# Disable SSO login for tests in this test case
@override_settings(
    USE_SSO_AUTH=False,
    AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
)
class TranslationsListViewTestCase(TestCase, WagtailTestUtils):
    """Test cases for the TranslationsListView."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a staff user for authentication
        self.staff_user = self.create_user(username="testuser", email="test@example.com", password="testpass", is_staff=True)

        # Get or create locales
        self.en_locale, created = Locale.objects.get_or_create(language_code="en-US")
        self.de_locale, created = Locale.objects.get_or_create(language_code="de")
        self.fr_locale, created = Locale.objects.get_or_create(language_code="fr")
        self.it_locale, created = Locale.objects.get_or_create(language_code="it")

        # Set default locale
        if not Locale.objects.filter(language_code="en-US").exists():
            Locale.objects.create(language_code="en-US")

        # # Create root pages for each locale if they don't exist
        # root_page = Page.get_first_root_node()

        # Get the English home page
        self.en_home = Page.objects.get(locale__language_code="en-US", slug="home")

        # Create German home page as a translation of the English home page
        self.de_home = self.en_home.copy_for_translation(self.de_locale)
        self.de_home.title = "German Home"
        self.de_home.save_revision().publish()

        # Create French home page as a translation of the English home page
        self.fr_home = self.en_home.copy_for_translation(self.fr_locale)
        self.fr_home.title = "French Home"
        self.fr_home.save_revision().publish()

        # Create Italian home page as a translation of the English home page
        self.it_home = self.en_home.copy_for_translation(self.it_locale)
        self.it_home.title = "Italian Home"
        self.it_home.save_revision().publish()

        self.url = reverse("cms:translations_list")

    def test_view_requires_staff_authentication(self):
        """Test that the view requires staff authentication."""
        # Test without login
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Test with non-staff user
        regular_user = self.create_user(username="regular", email="regular@example.com", password="testpass", is_staff=False)
        self.client.force_login(regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_view_accessible_by_staff(self):
        """Test that staff users can access the view."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Verify that the filter form is included in the context.
        self.assertIn("filter_form", response.context)
        self.assertEqual(response.context["filter_form"].__class__.__name__, "TranslationsFilterForm")

    def test_no_pages_scenario(self):
        """Test view when there are no pages (except root pages)."""
        self.client.force_login(self.staff_user)

        # Remove all content pages (keep only root pages)
        SimpleRichTextPage.objects.all().delete()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pages found.")
        self.assertEqual(len(response.context["pages_with_translations"]), 0)

    def test_single_page_no_translations(self):
        """Test view with a single page that has no translations."""
        self.client.force_login(self.staff_user)

        # Create a single page with no translations
        single_page = SimpleRichTextPage(title="Single Page", slug="single-page", locale=self.en_locale, content="Test content")
        self.en_home.add_child(instance=single_page)
        single_page.save_revision().publish()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # There should be 1 page in the response (the single_page).
        pages_with_translations = response.context["pages_with_translations"]
        self.assertEqual(len(pages_with_translations), 1)
        single_page_data = pages_with_translations[0]
        self.assertIsNotNone(single_page_data)
        self.assertEqual(single_page_data["page"], single_page.page_ptr)
        self.assertEqual(len(single_page_data["translations"]), 0)

    def test_page_with_multiple_translations(self):
        """Test view with pages that have multiple translations."""
        self.client.force_login(self.staff_user)

        # Create original page
        original_page = SimpleRichTextPage(title="Original Page", slug="original-page", locale=self.en_locale, content="Original content")
        self.en_home.add_child(instance=original_page)
        original_page.save_revision().publish()

        # Create translations
        de_translation = original_page.copy_for_translation(self.de_locale)
        de_translation.title = "German Page"
        de_translation.content = "German content"
        de_translation.save_revision().publish()

        fr_translation = original_page.copy_for_translation(self.fr_locale)
        fr_translation.title = "French Page"
        fr_translation.content = "French content"
        fr_translation.save_revision().publish()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # There should be 1 page in the response (the single_page).
        pages_with_translations = response.context["pages_with_translations"]
        self.assertEqual(len(pages_with_translations), 1)
        original_page_data = pages_with_translations[0]
        self.assertIsNotNone(original_page_data)
        # There should be 2 translations for the original_page.
        self.assertEqual(len(original_page_data["translations"]), 2)
        translation_locales = [t["locale"] for t in original_page_data["translations"]]
        self.assertIn("de", translation_locales)
        self.assertIn("fr", translation_locales)

    def test_pages_from_different_initial_locales(self):
        """Test pages that originate from different locales with translations."""
        self.client.force_login(self.staff_user)

        # Create page originally in English
        en_original = SimpleRichTextPage(title="English Original", slug="english-original", locale=self.en_locale, content="English content")
        self.en_home.add_child(instance=en_original)
        en_original.save_revision().publish()

        # Create page originally in German
        de_original = SimpleRichTextPage(title="German Original", slug="german-original-de", locale=self.de_locale, content="German content")
        self.de_home.add_child(instance=de_original)
        de_original.save_revision().publish()

        # Create translation of en_original to German
        en_to_de = en_original.copy_for_translation(self.de_locale)
        en_to_de.title = "German Translation"
        en_to_de.save_revision().publish()

        # Create translation of de_original to French
        de_to_fr = de_original.copy_for_translation(self.fr_locale)
        de_to_fr.title = "French Translation"
        de_to_fr.save_revision().publish()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # There should be 2 pages in the response (not their translations).
        pages_with_translations = response.context["pages_with_translations"]
        pages_in_response = [p["page"] for p in pages_with_translations]
        self.assertEqual(set(pages_in_response), set([en_original.page_ptr, de_original.page_ptr]))
        # Verify the translations in the data are correct.
        for page_data in pages_with_translations:
            translation_urls = [t["view_url"] for t in page_data["translations"]]
            if page_data["page"] == en_original.page_ptr:
                self.assertEqual(translation_urls, [en_to_de.url])
            elif page_data["page"] == de_original.page_ptr:
                self.assertEqual(translation_urls, [de_to_fr.url])

    def test_draft_and_published_pages(self):
        """Test that both draft and published pages are shown."""
        self.client.force_login(self.staff_user)

        # Create published page
        published_page = SimpleRichTextPage(title="Published Page", slug="published-page", locale=self.en_locale, content="Published content")
        self.en_home.add_child(instance=published_page)
        published_page.save_revision().publish()

        # Create draft page
        draft_page = SimpleRichTextPage(title="Draft Page", slug="draft-page", locale=self.en_locale, content="Draft content")
        self.en_home.add_child(instance=draft_page)
        draft_page.save_revision()  # Don't publish

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        pages_with_translations = response.context["pages_with_translations"]
        pages_in_response = [p["page"] for p in pages_with_translations]
        self.assertEqual(set(pages_in_response), set([published_page.page_ptr, draft_page.page_ptr]))

    def test_context_data_structure(self):
        """Test that the context data has the correct structure."""
        self.client.force_login(self.staff_user)

        # Create a page with translation
        original_page = SimpleRichTextPage(title="Test Page", slug="test-page", locale=self.en_locale, content="Test content")
        self.en_home.add_child(instance=original_page)
        original_page.save_revision().publish()

        translation = original_page.copy_for_translation(self.de_locale)
        translation.title = "Test Site De"
        translation.save_revision().publish()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        pages_with_translations = response.context["pages_with_translations"]
        self.assertIsInstance(pages_with_translations, list)

        # Check structure of page data
        self.assertEqual(
            pages_with_translations,
            [
                {
                    "page": original_page.page_ptr,
                    "translations": [
                        {
                            "locale": "de",
                            "edit_url": f"/cms-admin/pages/{translation.id}/edit/",
                            "view_url": translation.get_url(),
                            "percent_translated": 0,
                        }
                    ],
                    "edit_url": f"/cms-admin/pages/{original_page.id}/edit/",
                    "view_url": original_page.get_url(),
                }
            ],
        )

    def test_excludes_root_pages(self):
        """Test that root pages (depth <= 2) are excluded."""
        self.client.force_login(self.staff_user)

        response = self.client.get(self.url)
        pages_with_translations = response.context["pages_with_translations"]

        # Check that no root pages are included
        for page_data in pages_with_translations:
            page = page_data["page"]
            self.assertGreater(page.depth, 2, f"Page '{page.title}' with depth {page.depth} should be excluded")

    def test_original_language_filter(self):
        """Test filtering by a specific original_language."""
        self.client.force_login(self.staff_user)

        # Create a page in English.
        en_page = SimpleRichTextPage(title="English Page", slug="english-page", locale=self.en_locale, content="English content")
        self.en_home.add_child(instance=en_page)
        en_page.save_revision().publish()
        # Create a page in German.
        de_page = SimpleRichTextPage(title="German Page", slug="german-page", locale=self.de_locale, content="German content")
        self.de_home.add_child(instance=de_page)
        de_page.save_revision().publish()

        # Create a page in French.
        fr_page = SimpleRichTextPage(title="French Page", slug="french-page", locale=self.fr_locale, content="French content")
        self.fr_home.add_child(instance=fr_page)
        fr_page.save_revision().publish()

        # Give the en_page page a German translation.
        de_translation = en_page.copy_for_translation(self.de_locale)
        de_translation.title = "English Page translated to German"
        de_translation.content = "German content"
        de_translation.save_revision().publish()

        with self.subTest("Filter by German"):
            response = self.client.get(self.url, {"original_language": "de"})
            pages_with_translations = response.context["pages_with_translations"]
            # The response should contain only the de_page (not the de_translation of the English page).
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([de_page.page_ptr]))

        with self.subTest("Filter by English"):
            response = self.client.get(self.url, {"original_language": "en-US"})
            pages_with_translations = response.context["pages_with_translations"]

            # The response should contain only the en_page.
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([en_page.page_ptr]))

            # The page data should show the German translation of the en_page.
            page_data = pages_with_translations[0]
            translation_locales = [t["locale"] for t in page_data["translations"]]
            self.assertEqual(len(translation_locales), 1)
            self.assertIn("de", translation_locales)

        with self.subTest("Filter by invalid language"):
            # The response hould contain no results.
            response = self.client.get(self.url, {"original_language": "invalid-code"})
            pages_with_translations = response.context["pages_with_translations"]
            self.assertEqual(len(pages_with_translations), 0)

    def test_exists_in_language_filter(self):
        """Test filtering by exists_in_language (whether a page exists in a particular language)."""
        self.client.force_login(self.staff_user)

        # Create a page originally in English.
        en_page = SimpleRichTextPage(title="English Original", slug="english-page", locale=self.en_locale, content="English content")
        self.en_home.add_child(instance=en_page)
        en_page.save_revision().publish()

        # Create a page originally in German.
        de_page = SimpleRichTextPage(title="German Original", slug="german-page", locale=self.de_locale, content="German content")
        self.de_home.add_child(instance=de_page)
        de_page.save_revision().publish()

        # Create a page originally in French.
        fr_page = SimpleRichTextPage(title="French Original", slug="french-page", locale=self.fr_locale, content="French content")
        self.fr_home.add_child(instance=fr_page)
        fr_page.save_revision().publish()

        # Create German and French translations for the en_page.
        de_translation = en_page.copy_for_translation(self.de_locale)
        de_translation.title = "German Translation"
        de_translation.save_revision().publish()

        fr_translation = en_page.copy_for_translation(self.fr_locale)
        fr_translation.title = "French Translation"
        fr_translation.save_revision().publish()

        # Create Italian translations for the fr_page.
        it_translation = fr_page.copy_for_translation(self.it_locale)
        it_translation.title = "Italian Translation"
        it_translation.save_revision().publish()

        with self.subTest("Filter by exists in English"):
            # The response should contain en_page, since it is in English. No other
            # page has an English translation
            response = self.client.get(self.url, {"exists_in_language": "en-US"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([en_page.page_ptr]))

        with self.subTest("Filter by exists in German"):
            # The response should contain:
            #   - de_page, since it is in German
            #   - en_page, since it has a German translation
            response = self.client.get(self.url, {"exists_in_language": "de"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([de_page.page_ptr, en_page.page_ptr]))

        with self.subTest("Filter by exists in Italian"):
            # The response should contain:
            #   - fr_page, since it has an Italian translation
            response = self.client.get(self.url, {"exists_in_language": "it"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([fr_page.page_ptr]))

        with self.subTest("Filter by exists in French"):
            # The response should contain:
            #   - fr_page, since it is in French
            #   - en_page, since it has a French translation
            response = self.client.get(self.url, {"exists_in_language": "fr"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([en_page.page_ptr, fr_page.page_ptr]))

        with self.subTest("Filter by invalid language"):
            # The response should contain no results.
            response = self.client.get(self.url, {"exists_in_language": "invalid-code"})
            pages_with_translations = response.context["pages_with_translations"]
            self.assertEqual(len(pages_with_translations), 0)

        with self.subTest("Filter by blank value"):
            # The response should contain all pages.
            response = self.client.get(self.url, {"exists_in_language": ""})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(
                set(pages_in_response),
                set([en_page.page_ptr, de_page.page_ptr, fr_page.page_ptr]),
            )

    def test_multiple_filters_together(self):
        """Test using both original_language and exists_in_language filters together."""
        self.client.force_login(self.staff_user)

        # Create a page originally in English.
        en_page = SimpleRichTextPage(title="English Original", slug="english-page", locale=self.en_locale, content="English content")
        self.en_home.add_child(instance=en_page)
        en_page.save_revision().publish()

        # Create a page originally in German.
        de_page = SimpleRichTextPage(title="German Original", slug="german-page", locale=self.de_locale, content="German content")
        self.de_home.add_child(instance=de_page)
        de_page.save_revision().publish()

        # Create a page originally in French.
        fr_page = SimpleRichTextPage(title="French Original", slug="french-page", locale=self.fr_locale, content="French content")
        self.fr_home.add_child(instance=fr_page)
        fr_page.save_revision().publish()

        # Create German and French translations for the en_page.
        de_translation = en_page.copy_for_translation(self.de_locale)
        de_translation.title = "German Translation"
        de_translation.save_revision().publish()

        fr_translation = en_page.copy_for_translation(self.fr_locale)
        fr_translation.title = "French Translation"
        fr_translation.save_revision().publish()

        # Create Italian translations for the fr_page.
        it_translation = fr_page.copy_for_translation(self.it_locale)
        it_translation.title = "Italian Translation"
        it_translation.save_revision().publish()

        with self.subTest("original_language=en-US AND exists_in_language=de"):
            # The response should contain:
            #   - en_page, since it is originally in English and has a German translation
            response = self.client.get(self.url, {"original_language": "en-US", "exists_in_language": "de"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([en_page.page_ptr]))

        with self.subTest("original_language=de AND exists_in_language=fr"):
            # The response should contain no results
            response = self.client.get(self.url, {"original_language": "de", "exists_in_language": "fr"})
            pages_with_translations = response.context["pages_with_translations"]
            self.assertEqual(len(pages_with_translations), 0)

        with self.subTest("original_language=en-US AND exists_in_language=fr"):
            # The response should contain:
            #   - en_page, since it is originally in English and has a French translation
            response = self.client.get(self.url, {"original_language": "en-US", "exists_in_language": "fr"})
            pages_with_translations = response.context["pages_with_translations"]
            pages_in_response = [p["page"] for p in pages_with_translations]
            self.assertEqual(set(pages_in_response), set([en_page.page_ptr]))
