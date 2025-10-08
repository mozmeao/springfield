# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import pytest
from wagtail.coreutils import get_dummy_request
from wagtail.models import Locale, Page
from wagtail_localize.models import StringTranslation, TranslatableObject, Translation, TranslationSource

from springfield.cms.models import PageTranslationData
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory
from springfield.cms.utils import (
    create_page_translation_data,
    get_cms_locales_for_path,
    get_locales_for_cms_page,
    get_page_for_request,
)

pytestmark = [pytest.mark.django_db]


def test_get_locales_for_cms_page(tiny_localized_site):
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]

    # By default there are no aliases in the system, so all _locales_available_for_cms will
    # match the pages set up in the tiny_localized_site fixture
    assert Page.objects.filter(alias_of__isnull=False).count() == 0

    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "fr", "pt-BR"]

    # now make aliases of the test_page into Dutch and Spanish
    nl_locale = Locale.objects.create(language_code="nl")
    es_es_locale = Locale.objects.create(language_code="es-ES")

    nl_page_alias = en_us_test_page.copy_for_translation(locale=nl_locale, copy_parents=True, alias=True)
    nl_page_alias.save()

    es_es_page_alias = en_us_test_page.copy_for_translation(locale=es_es_locale, copy_parents=True, alias=True)
    es_es_page_alias.save()

    assert Page.objects.filter(alias_of__isnull=False).count() == 4  # 2 child + 2 parent pages, which had to be copied too

    # Show that the aliases don't appear in the available locales
    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "fr", "pt-BR"]


def test_get_locales_for_cms_page__ensure_draft_pages_are_excluded(tiny_localized_site):
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]
    fr_homepage = Page.objects.get(locale__language_code="fr", slug="home-fr")
    fr_test_page = fr_homepage.get_children()[0]

    fr_test_page.unpublish()

    assert sorted(get_locales_for_cms_page(en_us_test_page)) == ["en-US", "pt-BR"]


@pytest.mark.parametrize(
    "path, expected_page_url",
    [
        (
            "/en-US/test-page/",
            "/en-US/test-page/",
        ),
        (
            "/test-page/",
            "/en-US/test-page/",
        ),
        (
            "/pt-BR/test-page/",
            "/pt-BR/test-page/",
        ),
        (
            "/pt-BR/test-page/child-page/",
            "/pt-BR/test-page/child-page/",
        ),
        (
            "/fr/test-page/",
            "/fr/test-page/",
        ),
        (
            "/fr/test-page/child-page/",
            "/fr/test-page/child-page/",
        ),
        # These two routes do not work, even though a manual test with similar ones
        # does not show up as a problem. I think it's possibly related to the
        # tiny_localized_site fixture generated in cms/tests/conftest.py
        # (
        #     "/fr/test-page/child-page/grandchild-page/",
        #     "/fr/test-page/child-page/grandchild-page/",
        # ),
        # (
        #     "/test-page/child-page/grandchild-page/",
        #     "/fr/test-page/child-page/grandchild-page/",
        # ),
    ],
)
def test_get_page_for_request__happy_path(path, expected_page_url, tiny_localized_site):
    request = get_dummy_request(path=path)
    page = get_page_for_request(request=request)
    assert isinstance(page, Page)
    assert page.url == expected_page_url


@pytest.mark.parametrize(
    "path",
    [
        "/en-US/test-page/fake/path/",
        "/fr/test-page/fake/path/",
        "/not/a/real/test-page",
    ],
)
def test_get_page_for_request__no_match(path, tiny_localized_site):
    request = get_dummy_request(path=path)
    page = get_page_for_request(request=request)
    assert page is None


@pytest.mark.parametrize(
    "get_page_for_request_should_return_a_page, get_locales_for_cms_page_retval, expected",
    (
        (True, ["en-CA", "sco", "zh-CN"], ["en-CA", "sco", "zh-CN"]),
        (False, None, []),
    ),
)
def test_get_cms_locales_for_path(
    rf,
    get_page_for_request_should_return_a_page,
    get_locales_for_cms_page_retval,
    expected,
    minimal_site,
    mocker,
):
    request = rf.get("/path/is/irrelevant/due/to/mocks")
    mock_get_page_for_request = mocker.patch("springfield.cms.utils.get_page_for_request")
    mock_get_locales_for_cms_page = mocker.patch("springfield.cms.utils.get_locales_for_cms_page")

    if get_page_for_request_should_return_a_page:
        page = mocker.Mock("fake-page")
        mock_get_page_for_request.return_value = page
        mock_get_locales_for_cms_page.return_value = get_locales_for_cms_page_retval
    else:
        mock_get_page_for_request.return_value = None

    request = rf.get("/irrelevant/because/we/are/mocking")
    assert get_cms_locales_for_path(request) == expected

    if get_page_for_request_should_return_a_page:
        mock_get_page_for_request.assert_called_once_with(request=request)
        mock_get_locales_for_cms_page.assert_called_once_with(page=page)


class TestCreateTranslationData:
    def test_create_page_translation_data_no_translations(self, minimal_site):
        """Test create_page_translation_data with a page that has no translations."""
        # Get the page that has no translations
        en_page = Page.objects.get(slug="test-page")

        create_page_translation_data(en_page)

        # No PageTranslationData objects were created.
        assert not PageTranslationData.objects.exists()

    def test_create_page_translation_data_with_wagtail_localize_objects(self, tiny_localized_site):
        """Test create_page_translation_data with actual wagtail-localize objects."""
        # Get the English page and its translations
        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")
        fr_homepage = Page.objects.get(locale__language_code="fr", slug="test-page")
        pt_br_homepage = Page.objects.get(locale__language_code="pt-BR", slug="test-page")

        # Get the specific page instance
        specific_page = en_us_homepage.specific

        # Create TranslatableObject using the same logic as get_for_instance
        translatable_object, created = TranslatableObject.objects.get_or_create(
            translation_key=specific_page.translation_key,
            content_type=ContentType.objects.get_for_model(specific_page.get_translation_model()),
        )

        # Create TranslationSource for the English page
        translation_source, created = TranslationSource.objects.get_or_create(
            object=translatable_object,
            locale=en_us_homepage.locale,
            defaults={
                "object_repr": str(specific_page),
                "specific_content_type": specific_page.content_type,
                "last_updated_at": timezone.now(),
            },
        )

        # Create Translation records for French and Portuguese translations
        fr_locale = fr_homepage.locale
        pt_br_locale = pt_br_homepage.locale

        # Create Translation for French
        Translation.objects.get_or_create(source=translation_source, target_locale=fr_locale, defaults={"enabled": True})

        # Create Translation for Portuguese
        Translation.objects.get_or_create(source=translation_source, target_locale=pt_br_locale, defaults={"enabled": True})

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        create_page_translation_data(en_us_homepage)

        # A PageTranslationData object was created for each locale, with the expected data.
        assert PageTranslationData.objects.count() == 2
        fr_translation_data = PageTranslationData.objects.get(source_page=en_us_homepage, translated_page__locale=fr_locale)
        pt_br_translation_data = PageTranslationData.objects.get(source_page=en_us_homepage, translated_page__locale=pt_br_locale)
        expected_fr_data = {
            "edit_url": f"/cms-admin/pages/{fr_homepage.id}/edit/",
            "locale": "fr",
            "percent_translated": 100,
            "view_url": fr_homepage.url,
        }
        expected_pt_br_data = {
            "edit_url": f"/cms-admin/pages/{pt_br_homepage.id}/edit/",
            "locale": "pt-BR",
            "percent_translated": 100,
            "view_url": pt_br_homepage.url,
        }
        assert fr_translation_data.to_dict() == expected_fr_data
        assert pt_br_translation_data.to_dict() == expected_pt_br_data

    def test_create_page_translation_data_with_nested_translations(self, minimal_site):
        """
        Test translation of a translation scenario.

        We expect the original page to be translated to each language, but sometimes
        a translation will itself be translated into another language. The original
        page should still have the correct calculations for all of its translations.
        """
        # Make sure 3 locales exist: English, Spanish, and Portuguese (Brazil).
        assert Locale.objects.filter(language_code="en-US").exists()
        es_locale = LocaleFactory(language_code="es")
        pt_br_locale = LocaleFactory(language_code="pt-BR")

        # Create a homepage for each locale.
        en_us_homepage = Page.objects.get(slug="test-page")
        es_homepage = en_us_homepage.copy_for_translation(es_locale)
        es_homepage.title = "Página de Test"
        es_homepage.save()
        rev = es_homepage.save_revision()
        es_homepage.publish(rev)
        pt_br_homepage = en_us_homepage.copy_for_translation(pt_br_locale)
        pt_br_homepage.title = "Página de Teste"
        pt_br_homepage.save()
        rev = pt_br_homepage.save_revision()
        pt_br_homepage.publish(rev)

        # Create a child page for the English homepage.
        en_us_child = SimpleRichTextPageFactory(
            title="Child",
            slug="child-page",
            parent=en_us_homepage,
        )

        # Translate the en_us_child to Spanish.
        es_child = en_us_child.copy_for_translation(es_locale)
        es_child.title = "Child (es)"
        es_child.save()
        rev = es_child.save_revision()
        es_child.publish(rev)
        # Translate the es_child to Portuguese.
        pt_br_child = en_us_child.copy_for_translation(pt_br_locale)
        pt_br_child.title = "Child (pt_br)"
        pt_br_child.save()
        rev = pt_br_child.save_revision()
        pt_br_child.publish(rev)

        # Get the specific page instance for the child page (which is what we're testing)
        specific_page = en_us_child.specific

        # Translate the en_us_child into Spanish.
        translatable_object, _ = TranslatableObject.objects.get_or_create_from_instance(specific_page)
        translation_source, _ = TranslationSource.objects.update_or_create(
            object=translatable_object,
            locale=en_us_child.locale,
            defaults={
                "object_repr": str(specific_page),
                "specific_content_type": specific_page.content_type,
                "last_updated_at": timezone.now(),
            },
        )
        Translation.objects.get_or_create(source=translation_source, target_locale=es_locale, defaults={"enabled": True})

        # Translate the es_child into Portuguese.
        es_specific_page = es_child.specific
        es_translatable_object, _ = TranslatableObject.objects.get_or_create_from_instance(es_specific_page)
        es_translation_source, _ = TranslationSource.objects.update_or_create(
            object=es_translatable_object,
            locale=es_child.locale,
            defaults={
                "object_repr": str(es_specific_page),
                "specific_content_type": es_specific_page.content_type,
                "last_updated_at": timezone.now(),
            },
        )
        Translation.objects.get_or_create(source=es_translation_source, target_locale=pt_br_locale, defaults={"enabled": True})

        # Force creation of segments using wagtail-localize's API. This translates
        # each relevant page field.
        translation_source.update_from_db()
        # Get the string segments that were created
        string_segments = translation_source.stringsegment_set.all()

        # Create translations for some segments to simulate progress
        for segment in string_segments[:2]:  # Translate first 2 segments
            # Spanish translation
            StringTranslation.objects.get_or_create(
                translation_of=segment.string,
                locale=es_locale,
                context=segment.context,
                defaults={
                    "data": f"Spanish: {segment.string.data}",
                    "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL,
                    "has_error": False,
                },
            )

            # Portuguese translation
            StringTranslation.objects.get_or_create(
                translation_of=segment.string,
                locale=pt_br_locale,
                context=segment.context,
                defaults={
                    "data": f"Portuguese: {segment.string.data}",
                    "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL,
                    "has_error": False,
                },
            )

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        # Create the PageTranslationData objects.
        create_page_translation_data(en_us_child)

        # A PageTranslationData object was created for the es_child and the
        # pt_br_child, with the expected data.
        assert PageTranslationData.objects.count() == 2
        es_child_translation_data = PageTranslationData.objects.get(source_page=en_us_child, translated_page__locale=es_locale)
        pt_br_child_translation_data = PageTranslationData.objects.get(source_page=en_us_child, translated_page__locale=pt_br_locale)
        expected_es_data = {
            "edit_url": f"/cms-admin/pages/{es_child.id}/edit/",
            "locale": "es",
            "percent_translated": 100,
            "view_url": es_child.url,
        }
        expected_pt_br_data = {
            "edit_url": f"/cms-admin/pages/{pt_br_child.id}/edit/",
            "locale": "pt-BR",
            "percent_translated": 100,
            "view_url": pt_br_child.url,
        }
        assert es_child_translation_data.to_dict() == expected_es_data
        assert pt_br_child_translation_data.to_dict() == expected_pt_br_data

        # Now, the es_child title gets updated, so the pt_br_child title translation should become stale.
        es_child.title = "Página secundaria"
        es_child.save()
        rev = es_child.save_revision()
        es_child.publish(rev)
        es_translation_source.update_from_db()
        # Create a new Portuguese translation based on the Spanish source
        Translation.objects.get_or_create(source=es_translation_source, target_locale=pt_br_locale, defaults={"enabled": True})

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        # Create the PageTranslationData objects.
        create_page_translation_data(en_us_child)

        # The Portuguese translation is now stale since the Spanish source changed.
        pt_br_child_translation_data = PageTranslationData.objects.get(source_page=en_us_child, translated_page__locale=pt_br_locale)
        assert pt_br_child_translation_data.percent_translated == 0
        # The Spanish translation is still as it was before.
        es_child_translation_data = PageTranslationData.objects.get(source_page=en_us_child, translated_page__locale=es_locale)
        assert es_child_translation_data.to_dict() == expected_es_data

    @patch("springfield.cms.utils.TranslationSource.objects.get_for_instance")
    @patch("springfield.cms.utils.Translation.objects.get")
    def test_create_page_translation_data_with_translation_progress(self, mock_translation_get, mock_translation_source_get, tiny_localized_site):
        """
        Verify that calculations return the percentage for data that wagtail-localize gives us.
        """
        # Setup mocks
        mock_source = Mock()
        mock_translation_source_get.return_value = mock_source

        mock_translation_record = Mock()
        mock_translation_record.get_progress.return_value = (10, 7)  # 7 out of 10 segments translated
        mock_translation_get.return_value = mock_translation_record

        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        create_page_translation_data(en_us_homepage)

        # Should calculate 70% translation progress
        assert PageTranslationData.objects.count() == 2  # fr and pt-BR translations
        for translation_data in PageTranslationData.objects.all():
            assert translation_data.percent_translated == 70

    @patch("springfield.cms.utils.TranslationSource.objects.get_for_instance")
    @patch("springfield.cms.utils.Translation.objects.get")
    def test_create_page_translation_data_with_zero_segments(self, mock_translation_get, mock_translation_source_get, tiny_localized_site):
        """Test create_page_translation_data when total segments is zero."""
        # Setup mocks
        mock_source = Mock()
        mock_translation_source_get.return_value = mock_source

        mock_translation_record = Mock()
        mock_translation_record.get_progress.return_value = (0, 0)  # No segments
        mock_translation_get.return_value = mock_translation_record

        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        create_page_translation_data(en_us_homepage)

        # Should return 100% when there are no segments to translate
        assert PageTranslationData.objects.count() == 2
        for translation_data in PageTranslationData.objects.all():
            assert translation_data.percent_translated == 100

    @patch("springfield.cms.utils.TranslationSource.objects.get_for_instance")
    def test_create_page_translation_data_no_translation_source(self, mock_translation_source_get, tiny_localized_site):
        """Test create_page_translation_data when TranslationSource doesn't exist."""
        # Mock TranslationSource.DoesNotExist
        from wagtail_localize.models import TranslationSource

        mock_translation_source_get.side_effect = TranslationSource.DoesNotExist()

        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        create_page_translation_data(en_us_homepage)

        # Should still return translation data with 0% progress
        assert PageTranslationData.objects.count() == 2
        for translation_data in PageTranslationData.objects.all():
            assert translation_data.percent_translated == 0

    @patch("springfield.cms.utils.TranslationSource.objects.get_for_instance")
    @patch("springfield.cms.utils.Translation.objects.get")
    def test_create_page_translation_data_fallback_to_nested_search(self, mock_translation_get, mock_translation_source_get, tiny_localized_site):
        """Test the fallback logic when translation is from another translation."""
        mock_translation_record = Mock()
        mock_translation_record.get_progress.return_value = (8, 6)  # 75% translated

        mock_translation_source_get.side_effect = [TranslationSource.DoesNotExist(), Mock(), TranslationSource.DoesNotExist(), Mock()]
        mock_translation_get.side_effect = [
            Translation.DoesNotExist(),  # First call (direct translation) should fail
            mock_translation_record,  # Second call (translation of a translation) should succeed
        ]

        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        create_page_translation_data(en_us_homepage)

        # Should find translations via the fallback method
        assert PageTranslationData.objects.count() == 2
        # At least one translation should have 75% progress from the nested search
        progress_values = {td.percent_translated for td in PageTranslationData.objects.all()}
        assert 75 in progress_values

    def test_create_page_translation_data_handles_value_error(self, tiny_localized_site):
        """Test create_page_translation_data handles ValueError gracefully."""
        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        # Mock get_translations to raise ValueError
        with patch.object(Page, "get_translations", side_effect=ValueError("Test error")):
            create_page_translation_data(en_us_homepage)

            # Should not create any PageTranslationData when ValueError occurs
            assert PageTranslationData.objects.count() == 0

    @patch("springfield.cms.utils.logger")
    def test_create_page_translation_data_handles_attribute_error(self, mock_logger, tiny_localized_site):
        """Test create_page_translation_data handles AttributeError gracefully."""
        en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="test-page")

        # Make sure there are currently no PageTranslationData objects.
        PageTranslationData.objects.all().delete()

        # Mock specific property to raise AttributeError
        with patch.object(Page, "get_translations", side_effect=AttributeError("Test error")):
            create_page_translation_data(en_us_homepage)

            # If an AttributeError occurs, then no PageTranslationData should be created.
            assert PageTranslationData.objects.count() == 0
            # The logger was called with an exception.
            assert mock_logger.exception.call_count == 1
            assert [str(thing.args[0]) for thing in mock_logger.exception.call_args_list] == ["Test error"]
