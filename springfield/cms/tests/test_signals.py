# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import transaction
from django.test import override_settings
from django.test.client import BOUNDARY, encode_multipart
from django.urls import reverse
from django.utils import timezone

import polib
import pytest
from wagtail.models import Locale, Page
from wagtail_localize.models import StringTranslation, Translation, TranslationSource
from wagtail_localize_smartling.api.types import JobStatus
from wagtail_localize_smartling.models import Job, Project

from springfield.cms.models import PageTranslationData, SimpleRichTextPage
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [
    pytest.mark.django_db,
]


@override_settings(WAGTAIL_ENABLE_ADMIN=True)
@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_creating_translation_of_page_creates_page_translation_data(_mock_on_commit, client, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 1: Creating a translation of a page should create PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Initially, there should be no PageTranslationData
    assert PageTranslationData.objects.count() == 0

    # Create a superuser and login
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
    client.force_login(user)

    # Submit the page for translation via the wagtail-localize view
    localize_url = reverse("wagtail_localize:submit_page_translation", args=[en_page.id])
    response = client.post(
        localize_url,
        data={"locales": [fr_locale.id]},
    )

    # The wagtail-localize view should redirect to the edit page after successful submission
    assert response.status_code == 302, f"Unexpected status code: {response.status_code}"

    # The signal should have created a PageTranslationData object with the expected data.
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.filter(
        source_page=en_page,
    ).first()
    assert translation_data is not None
    assert translation_data.source_page == en_page.page_ptr
    assert translation_data.translated_page.locale == fr_locale
    assert translation_data.percent_translated == 0


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_translating_field_updates_page_translation_data(_mock_on_commit, client, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 2: Translating a field should create or update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, created = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created with initial progress
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    initial_percent = translation_data.percent_translated

    # Create a superuser and login
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
    client.force_login(user)

    # Get a translatable string segment from the translation
    string_segment = translation_source.stringsegment_set.first()
    assert string_segment is not None, "No string segments found for translation"

    # Translate a string via the wagtail-localize edit_string_translation view
    edit_url = reverse(
        "wagtail_localize:edit_string_translation",
        args=[translation.id, string_segment.string_id],
    )

    response = client.put(
        edit_url, data=encode_multipart(BOUNDARY, {"value": "Contenu français"}), content_type=f"multipart/form-data; boundary={BOUNDARY}"
    )

    # The request should succeed
    assert response.status_code in [200, 201], f"Unexpected status code: {response.status_code}"

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    # Percent translated should have increased (or stayed the same if it was already 100%)
    assert translation_data.percent_translated >= initial_percent


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_deleting_translation_of_page_deletes_page_translation_data(_mock_on_commit, client, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 3: Deleting a translation of a page should delete PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    translated_page = translation_data.translated_page

    # Create a superuser and login
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
    client.force_login(user)

    # Delete the translated page via the Wagtail admin
    delete_url = reverse("wagtailadmin_pages:delete", args=[translated_page.id])
    response = client.post(delete_url)

    # The request should succeed (redirect after deletion)
    assert response.status_code == 302, f"Unexpected status code: {response.status_code}"

    # The signal should have deleted the PageTranslationData
    assert PageTranslationData.objects.filter(source_page=en_page, translated_page=translated_page).count() == 0


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_deleting_translation_of_field_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 4: Deleting a translation of a field should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)

    # Get a translatable string segment
    string_segment = translation_source.stringsegment_set.first()
    assert string_segment is not None, "No string segments found for translation"

    # Create a string translation directly via ORM
    string_translation = StringTranslation.objects.create(
        translation_of=string_segment.string,
        locale=fr_locale,
        context=string_segment.context,
        data="Contenu français",
    )

    # Get the updated translation percentage after adding translation
    translation_data.refresh_from_db()
    percent_before_deletion = translation_data.percent_translated

    # Now delete the string translation directly via ORM (this triggers the
    # signal to update PageTranslationData).
    string_translation.delete()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    # Percent translated should have decreased (or stayed at 0)
    assert translation_data.percent_translated <= percent_before_deletion


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_synchronizing_page_updates_page_translation_data(_mock_on_commit, client, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 5: Synchronizing a page and its translations should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Create a string translation directly via ORM.
    string_segment = translation_source.stringsegment_set.first()
    StringTranslation.objects.create(
        translation_of=string_segment.string,
        locale=fr_locale,
        context=string_segment.context,
        data="Contenu français",
    )

    # Create a superuser and login
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
    client.force_login(user)

    # Verify PageTranslationData exists.
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    # Set the percent_translated to 100 to make sure it gets updated later.
    translation_data.percent_translated = 100
    translation_data.save()

    # Synchronize the translation via the wagtail-localize update view
    # This updates the TranslationSource with the new content from the source page
    update_url = reverse(
        "wagtail_localize:update_translations",
        args=[translation_source.id],
    )
    response = client.post(update_url)

    # The request should succeed (redirect after update)
    assert response.status_code == 302, f"Unexpected status code: {response.status_code}"

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    # The percent translated should be lower than 100 (since only 1 field was
    # translated before the syncronization).
    assert translation_data is not None
    assert translation_data.percent_translated < 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_saving_page_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 6: Saving a page should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)

    # Save the page (this triggers the page_saved_signal)
    en_page.title = "Updated English Page"
    en_page.save()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    assert translation_data is not None


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_updating_translation_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 7: Updating an existing Translation should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)

    # Set the translation_data's percent_translated to 100, to make sure it gets updated later.
    translation_data.percent_translated = 100
    translation_data.save()

    # Update the translation (this triggers the translation_saved_signal)
    translation.enabled = False
    translation.save()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    assert translation_data.percent_translated < 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_updating_string_translation_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 8: Updating an existing StringTranslation should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Create a string translation
    string_segment = translation_source.stringsegment_set.first()
    string_translation = StringTranslation.objects.create(
        translation_of=string_segment.string,
        locale=fr_locale,
        context=string_segment.context,
        data="Contenu français",
    )

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    # Set the translation_data's percent_translated to 100, to make sure it gets updated later.
    translation_data.percent_translated = 100
    translation_data.save()

    # Update the string translation (this triggers the string_translation_saved_signal)
    string_translation.data = "Contenu français mis à jour"
    string_translation.save()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    assert translation_data.percent_translated < 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_updating_translation_source_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 9: Updating an existing TranslationSource should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    # Set the translation_data's percent_translated to 100, to make sure it gets updated later.
    translation_data.percent_translated = 100
    translation_data.save()

    # Update the source page and create a new translation source
    en_page.content = "Updated content"
    en_page.save_revision().publish()

    # Update the translation source (this triggers the translation_source_saved_signal)
    translation_source.update_from_db()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    assert translation_data.percent_translated < 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_updating_page_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 10: Updating an existing Page should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    # Set the translation_data's percent_translated to 100, to make sure it gets updated later.
    translation_data.percent_translated = 100
    translation_data.save()

    # Update the page (this triggers the page_saved_signal)
    en_page.content = "Updated English content"
    en_page.save_revision().publish()

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    assert translation_data.percent_translated < 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_translation_chain_creates_correct_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_and_some_translations):
    """Test scenario 11: Translation chain (A→B→C) - ensure signal correctly finds original translation."""
    # Get locales
    en_locale = Locale.objects.get(language_code="en-US")
    de_locale = Locale.objects.get(language_code="de")
    it_locale = Locale.objects.get(language_code="it")

    # Get the English page (A)
    en_page = SimpleRichTextPage.objects.get(locale=en_locale, slug="english-page")

    # Get the German translation (B - already exists from fixture)
    de_page = SimpleRichTextPage.objects.get(locale=de_locale, slug="english-page")

    # Create an Italian translation from the German page (C from B)
    translation_source, _ = TranslationSource.get_or_create_from_instance(de_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=it_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)
    it_page = SimpleRichTextPage.objects.get(locale=it_locale, slug="english-page")

    # Verify PageTranslationData exists for both German and Italian translations
    # Both should reference the original English page as the source
    assert PageTranslationData.objects.count() >= 2

    # Check that German translation data references English page
    de_translation_data = PageTranslationData.objects.get(source_page=en_page, translated_page=de_page)
    assert de_translation_data.source_page == en_page.page_ptr
    assert de_translation_data.translated_page == de_page.page_ptr

    # Check that Italian translation data references the original source page.
    it_translation_data = PageTranslationData.objects.get(translated_page=it_page)
    assert it_translation_data.source_page == en_page.page_ptr
    assert it_translation_data.translated_page == it_page.page_ptr


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_page_with_no_translations_creates_no_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages):
    """Test scenario 12: Page with no translations should not create PageTranslationData."""
    # Get the English home page
    en_home = Page.objects.get(locale__language_code="en-US", slug="home")

    # Create a new page with no translations
    en_page = SimpleRichTextPageFactory(
        title="Standalone Page",
        slug="standalone-page",
        locale=Locale.objects.get(language_code="en-US"),
        content="This page has no translations",
        parent=en_home,
    )
    en_page.save_revision().publish()
    en_page.save()

    # Verify that no PageTranslationData was created for this page
    assert PageTranslationData.objects.filter(source_page=en_page).count() == 0
    assert PageTranslationData.objects.filter(translated_page=en_page).count() == 0


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_uploading_po_file_updates_page_translation_data(_mock_on_commit, client, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 13: Uploading a .po file for a translation should update PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created with initial progress
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    assert translation_data.percent_translated < 100

    # Create a superuser and login
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")
    client.force_login(user)

    # Create a PO file with translations for the page
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "POT-Creation-Date": str(timezone.now()),
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=utf-8",
        "X-WagtailLocalize-TranslationID": str(translation.uuid),
    }

    # Get translatable string segments from the translation
    string_segments = translation_source.stringsegment_set.all()
    assert string_segments.count() > 0, "No string segments found for translation"

    # Add translations for all string segments to the PO file
    for segment in string_segments:
        po.append(
            polib.POEntry(
                msgid=segment.string.data,
                msgctxt=segment.context.path,
                msgstr=f"Traduction française: {segment.string.data}",
            )
        )

    # Make sure (just before uploading the .po file) that the percent translated is less than 100%.
    translation_data.refresh_from_db()
    assert translation_data.percent_translated < 100

    # Upload the PO file via the wagtail-localize upload_pofile view
    upload_url = reverse("wagtail_localize:upload_pofile", args=[translation.id])
    fr_page = translation.get_target_instance()
    response = client.post(
        upload_url,
        {
            "file": SimpleUploadedFile(
                "translations.po",
                str(po).encode("utf-8"),
                content_type="text/x-gettext-translation",
            ),
            "next": reverse("wagtailadmin_pages:edit", args=[fr_page.id]),
        },
    )

    # The request should succeed (redirect after upload)
    assert response.status_code == 302, f"Unexpected status code: {response.status_code}"

    # The signal should have updated PageTranslationData: all fields should now be translated.
    translation_data.refresh_from_db()
    assert translation_data.percent_translated == 100


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_smartling_sync_updates_page_translation_data(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page):
    """Test scenario 14: Getting translation data from wagtail_localize_smartling updates PageTranslationData."""
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify PageTranslationData was created with initial progress
    assert PageTranslationData.objects.count() == 1
    translation_data = PageTranslationData.objects.get(source_page=en_page)
    assert translation_data.percent_translated < 100

    ###########################################################################
    # Begin creating data that the sync_smartling management command expects. #
    ###########################################################################
    # Create a user for the job
    User = get_user_model()
    user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")

    # Create a Smartling Project (required for Job)
    project = Project.objects.create(
        project_id="test-project",
        name="Test Project",
        environment="production",
        account_uid="test-account-uid",
        archived=False,
    )

    # Create a Smartling Job
    job = Job.objects.create(
        translation_source=translation_source,
        user=user,
        project=project,
        translation_job_uid="test-job-uid",
        status=JobStatus.IN_PROGRESS,
        first_synced_at=timezone.now(),
        last_synced_at=timezone.now(),
    )
    job.translations.add(translation)

    # Create a PO file with translations as Smartling would provide
    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "POT-Creation-Date": str(timezone.now()),
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=utf-8",
        "X-WagtailLocalize-TranslationID": str(translation.uuid),
    }

    # Get translatable string segments from the translation
    string_segments = translation_source.stringsegment_set.all()
    assert string_segments.count() > 0, "No string segments found for translation"

    # Add translations for all string segments to the PO file
    for segment in string_segments:
        po.append(
            polib.POEntry(
                msgid=segment.string.data,
                msgctxt=segment.context.path,
                msgstr=f"Traduction Smartling: {segment.string.data}",
            )
        )

    # Create a mock ZIP file containing the PO file (as Smartling API would return)
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        # Smartling returns files in format "{localeId}/{fileUri}"
        zip_file.writestr(f"fr-FR/{job.file_uri}", str(po))
    zip_buffer.seek(0)

    # Mock the Smartling API client to return our ZIP file
    mock_zipfile = MagicMock()
    mock_zipfile.infolist.return_value = [MagicMock(filename=f"fr-FR/{job.file_uri}")]
    mock_zipfile.open.return_value.__enter__ = lambda self: BytesIO(str(po).encode("utf-8"))
    mock_zipfile.open.return_value.__exit__ = lambda self, *args: None
    ###########################################################################
    # End creating data that the sync_smartling management command expects.   #
    ###########################################################################

    # Make sure (just before calling the management command) that the percent
    # translated is 0%, and no StringTranslation objects.
    translation_data.refresh_from_db()
    assert translation_data.percent_translated == 0
    assert not StringTranslation.objects.filter(locale=fr_locale).exists()

    # Mock the Smartling API client methods to prevent actual API calls
    with (
        patch("wagtail_localize_smartling.models.Project.get_current") as mock_get_current,
        patch("wagtail_localize_smartling.sync.client.download_translations") as mock_download,
        patch("wagtail_localize_smartling.sync.client.get_job_details") as mock_get_job,
    ):
        # Mock Project.get_current() to return our test project without API calls
        mock_get_current.return_value = project

        mock_download.return_value.__enter__.return_value = mock_zipfile
        mock_download.return_value.__exit__ = lambda self, *args: None

        # Mock get_job_details to return a completed job status with all required fields
        mock_get_job.return_value = {
            "translationJobUid": "test-job-uid",
            "jobName": "Test Job",
            "description": "Test job description",
            "jobStatus": "COMPLETED",
            "dueDate": None,
            "referenceNumber": "test-ref-123",
        }

        # Call the sync_smartling management command
        call_command("sync_smartling")

    # The signal should have updated PageTranslationData
    translation_data.refresh_from_db()
    # Percent translated should be 100%
    assert translation_data.percent_translated == 100

    # Verify that the StringTranslations were created.
    smartling_translations = StringTranslation.objects.filter(locale=fr_locale)
    assert smartling_translations.count() == string_segments.count()


@patch.object(transaction, "on_commit", side_effect=lambda func: func())
def test_page_saved_signal_skips_raw_save(_mock_on_commit, site_with_en_de_fr_it_homepages_1_en_page, tmp_path):
    """
    Saving a Page with raw=True should NOT trigger the signal handler.

    The post_save signal's "raw" argument from Django's documentation:
      A boolean; True if the model is saved exactly as presented (i.e. when
      loading a fixture). One should not query/modify other records in the
      database as the database might not be in a consistent state yet.

    When the export-db-to-sqlite.sh script is run, it triggers the post-save
    signal for Pages, which try to call create_page_translation_data() for the
    original translation of the Page. However, at this point in the script, there
    are (purposely) no wagtail-localize tables, to avoid exporting in-flight
    translated strings, so calling create_page_translation_data() would lead to
    a server error. Since Django passes kwargs={"raw": True} to the signal
    handler (correctly recognizing that the save is from a fixture/script, and
    not a user action we should not call create_page_translation_data().
    """
    # Get locales used in this test.
    fr_locale = Locale.objects.get(language_code="fr")

    # Get the English page.
    en_page = SimpleRichTextPage.objects.get(locale__language_code="en-US", slug="english-page")

    # Create a translation.
    translation_source, _ = TranslationSource.get_or_create_from_instance(en_page)
    translation = Translation.objects.create(
        source=translation_source,
        target_locale=fr_locale,
        enabled=True,
    )
    translation.save_target(user=None, publish=True)

    # Verify a PageTranslationData object was created.
    assert PageTranslationData.objects.count() == 1

    # Export to fixture including revisions
    fixture_file = tmp_path / "test_fixture.json"
    with open(fixture_file, "w") as f:
        call_command(
            "dumpdata",
            "cms.simplerichtextpage",
            "wagtailcore.page",
            "wagtailcore.revision",
            format="json",
            stdout=f,
        )

    # Delete the pages and wagtail-localize tables to simulate export-db-to-sqlite.sh
    en_page.delete()
    TranslationSource.objects.all().delete()
    Translation.objects.all().delete()
    # Delete all PageTranslationData objects.
    PageTranslationData.objects.all().delete()

    # Load the fixture - with raw=True, the signal handler should skip processing
    # This should not raise an error even though wagtail-localize tables don't exist.
    call_command("loaddata", str(fixture_file))

    # No PageTranslationData objects have been created.
    PageTranslationData.objects.all().delete()

    # Saving the en_page creates the PageTranslationData object again.
    en_page.save()
    assert PageTranslationData.objects.filter(source_page=en_page).exists()
