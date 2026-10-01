# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Tests for downloading, uploading and publishing every locale of a page's translations at once

import html
import io
import re
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

import polib
import pytest
from wagtail.models import Locale, Page
from wagtail_localize.models import StringSegment, StringTranslation, Translation, TranslationSource
from wagtail_localize.views.submit_translations import SubmitTranslationForm
from wagtail_localize_smartling.api.types import JobStatus
from wagtail_localize_smartling.models import Job, Project
from wagtail_localize_smartling.utils import compute_content_hash

from springfield.cms.bulk_translations import TranslationRow, publish_translations
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory, WagtailUserFactory
from springfield.cms.wagtail_hooks import manage_translations_button

pytestmark = pytest.mark.django_db


@pytest.fixture
def translated_source(minimal_site):
    """An en-US page submitted (without Smartling) for translation into fr, de and the en-CA alias."""
    for code in ("de", "en-CA"):
        LocaleFactory(language_code=code)

    page = SimpleRichTextPageFactory(
        title="Download Firefox",
        slug="download-firefox",
        parent=minimal_site.root_page,
        content="Get the browser that respects you",
    )
    source, _ = TranslationSource.get_or_create_from_instance(page)
    translations = {}
    for code in ("fr", "de", "en-CA"):
        translation = Translation.objects.create(source=source, target_locale=Locale.objects.get(language_code=code), enabled=True)
        translation.save_target(publish=False)
        translations[code] = translation

    return SimpleNamespace(page=page, source=source, translations=translations)


def translations_url(page):
    return reverse("cms_page_translations", args=[page.id])


def translated_po_bytes(translation, text):
    po = translation.export_po()
    for entry in po:
        entry.msgstr = text
    return str(po).encode()


def first_segment_translation(translation):
    segment = StringSegment.objects.filter(source=translation.source).order_by("order").first()
    return StringTranslation.objects.filter(
        translation_of_id=segment.string_id, context_id=segment.context_id, locale=translation.target_locale
    ).first()


def message_texts(response):
    # Wagtail escapes message text for display.
    return [html.unescape(str(message)).strip() for message in response.context["messages"]]


def test_url(translated_source):
    assert translations_url(translated_source.page) == f"/cms-admin/pages/{translated_source.page.id}/translations/"


def test_anonymous_user_not_permitted(client, translated_source):
    response = client.get(translations_url(translated_source.page))

    assert response.status_code == 302
    assert response.url.startswith("/cms-admin/login/")


def test_user_without_translation_permission_not_permitted(admin_client, translated_source):
    editor = WagtailUserFactory(username="editor")
    admin_only = Group.objects.create(name="Admin access only")
    admin_only.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
    editor.groups.add(admin_only)
    admin_client.force_login(editor, backend="django.contrib.auth.backends.ModelBackend")

    response = admin_client.get(translations_url(translated_source.page))

    assert response.status_code == 302
    assert response.url == "/cms-admin/"


def test_page_without_translations_returns_404(admin_client, minimal_site):
    page = SimpleRichTextPageFactory(slug="untranslated", parent=minimal_site.root_page)

    assert admin_client.get(translations_url(page), follow=True).status_code == 404


def test_unknown_action_rejected(admin_client, translated_source):
    assert admin_client.post(translations_url(translated_source.page), {"action": "delete"}).status_code == 400


def test_checklist_starts_cleared_and_badges_aliases(admin_client, translated_source):
    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.translation.target_locale.language_code: row for row in response.context["rows"]}
    assert not any(row.checked for row in rows.values())
    assert rows["en-CA"].alias_of == "en-US"
    assert rows["fr"].alias_of is None
    assert reverse("wagtailadmin_pages:edit", args=[rows["fr"].target_page.pk]) in response.content.decode()
    content = response.content.decode()
    assert "alias → en-US" in content
    assert "translation-progress--none" in content
    assert reverse("wagtailadmin_pages:edit", args=[translated_source.page.id]) in content
    assert "Edit English (US) page" in content
    assert '<details class="help-block help-info translation-help">' in content


def create_smartling_job(source, translation, status, content_hash=""):
    project, _ = Project.objects.get_or_create(
        environment="production",
        account_uid="account",
        project_id="project",
        defaults={
            "archived": False,
            "name": "Project",
            "type_code": "APPLICATION_RESOURCES",
            "source_locale_description": "English",
            "source_locale_id": "en-US",
        },
    )
    job = Job.objects.create(
        user=WagtailUserFactory(username="submitter"),
        translation_source=source,
        project=project,
        name="Job",
        reference_number="1",
        status=status,
        first_synced_at=timezone.now(),
        last_synced_at=timezone.now(),
        translation_job_uid="uid",
        content_hash=content_hash,
    )
    job.translations.add(translation)
    return job


def translate_first_segment(translation, user=None, tool_name=""):
    segment = StringSegment.objects.filter(source=translation.source).order_by("order").first()
    StringTranslation.objects.create(
        translation_of_id=segment.string_id,
        context_id=segment.context_id,
        locale=translation.target_locale,
        data="Traduit",
        tool_name=tool_name,
        last_translated_by=user,
    )


def test_translated_via_reports_where_translations_came_from(admin_client, translated_source):
    fr, de, en_ca = (translated_source.translations[code] for code in ("fr", "de", "en-CA"))
    job = create_smartling_job(translated_source.source, fr, JobStatus.IN_PROGRESS)
    translate_first_segment(de, tool_name="PO File")
    translate_first_segment(en_ca, user=WagtailUserFactory(username="translator"))

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.translation.target_locale.language_code: row for row in response.context["rows"]}
    assert rows["fr"].translated_via == []
    assert rows["fr"].open_smartling_job == job
    assert rows["de"].translated_via == [("PO file", 1)]
    assert rows["en-CA"].translated_via == [("Translation editor", 1)]
    content = response.content.decode()
    assert "Smartling: In progress" in content
    assert reverse("wagtail_localize_smartling_jobs:inspect", args=[job.pk]) in content


def test_translated_via_credits_smartling_imports_and_hides_finished_jobs(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    create_smartling_job(translated_source.source, fr, JobStatus.COMPLETED)
    translate_first_segment(fr)

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.translation.target_locale.language_code: row for row in response.context["rows"]}
    assert rows["fr"].translated_via == [("Smartling", 1)]
    assert rows["fr"].open_smartling_job is None
    assert rows["de"].translated_via == []
    assert "Not translated yet" in response.content.decode()


def test_translate_more_link_shown_only_when_locales_remain(admin_client, translated_source):
    assert admin_client.get(translations_url(translated_source.page)).context["translate_more_url"] is None

    LocaleFactory(language_code="it")
    translate_more_url = admin_client.get(translations_url(translated_source.page)).context["translate_more_url"]

    submit_url = reverse("wagtail_localize:submit_page_translation", args=[translated_source.page.id])
    assert translate_more_url == f"{submit_url}?next=%2Fcms-admin%2Fpages%2F{translated_source.page.id}%2Ftranslations%2F"


def test_download_zips_selected_locales(admin_client, translated_source):
    fr, en_ca = translated_source.translations["fr"], translated_source.translations["en-CA"]

    response = admin_client.post(translations_url(translated_source.page), {"action": "download", "translations": [fr.pk, en_ca.pk]})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"] == 'attachment; filename="download-firefox-translations.zip"'
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert sorted(archive.namelist()) == ["download-firefox-en-CA.po", "download-firefox-fr.po"]
    po = polib.pofile(archive.read("download-firefox-fr.po").decode())
    assert po.metadata["X-WagtailLocalize-TranslationID"] == str(fr.uuid)


@pytest.mark.parametrize("action", ["download", "publish", "unpublish", "stop"])
def test_action_without_selection_shows_error(admin_client, translated_source, action):
    response = admin_client.post(translations_url(translated_source.page), {"action": action})

    assert response.status_code == 200
    assert "Choose at least one locale." in response.content.decode()
    assert all(row.checked is False for row in response.context["rows"])


def test_upload_imports_each_file_into_its_own_locale(admin_client, translated_source):
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]
    files = [
        # Deliberately misleading names: matching uses the ID inside each file.
        SimpleUploadedFile("de.po", translated_po_bytes(fr, "Texte français")),
        SimpleUploadedFile("fr.po", translated_po_bytes(de, "Deutscher Text")),
    ]

    response = admin_client.post(translations_url(translated_source.page), {"action": "upload", "files": files})

    assert response.status_code == 302
    assert response.url == translations_url(translated_source.page)
    assert first_segment_translation(fr).data == "Texte français"
    assert first_segment_translation(de).data == "Deutscher Text"


def test_upload_without_files_shows_error(admin_client, translated_source):
    response = admin_client.post(translations_url(translated_source.page), {"action": "upload"})

    assert response.status_code == 200
    assert response.context["upload_form"].errors


def test_upload_skips_files_that_belong_elsewhere(admin_client, translated_source, minimal_site):
    other_page = SimpleRichTextPageFactory(slug="other-page", parent=minimal_site.root_page)
    other_source, _ = TranslationSource.get_or_create_from_instance(other_page)
    other_translation = Translation.objects.create(source=other_source, target_locale=Locale.objects.get(language_code="fr"))
    files = [
        SimpleUploadedFile("other.po", translated_po_bytes(other_translation, "Autre page")),
        SimpleUploadedFile("broken.po", b"\xff\xfe not a po file"),
    ]

    response = admin_client.post(translations_url(translated_source.page), {"action": "upload", "files": files}, follow=True)

    messages = message_texts(response)
    assert "Skipped other.po: it was downloaded for a different page or locale." in messages
    assert "Skipped broken.po: not a valid PO file." in messages
    assert "No translations were imported." in messages
    assert not StringTranslation.objects.filter(data="Autre page").exists()


def test_upload_skips_second_file_for_same_locale(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    files = [
        SimpleUploadedFile("first.po", translated_po_bytes(fr, "Première")),
        SimpleUploadedFile("second.po", translated_po_bytes(fr, "Deuxième")),
    ]

    response = admin_client.post(translations_url(translated_source.page), {"action": "upload", "files": files}, follow=True)

    assert "Skipped second.po: another file for French was already imported." in message_texts(response)
    assert first_segment_translation(fr).data == "Première"


def test_publish_publishes_only_selected_locales(admin_client, translated_source, django_capture_on_commit_callbacks):
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(translations_url(translated_source.page), {"action": "publish", "translations": [fr.pk]}, follow=True)

    assert "Published 1 of 1 locales: French." in message_texts(response)
    assert Page.objects.get(pk=fr.get_target_instance().pk).live is True
    assert Page.objects.get(pk=de.get_target_instance().pk).live is False


@pytest.mark.parametrize("action", ["publish", "unpublish"])
def test_publishing_actions_hidden_and_refused_without_publish_permission(admin_client, translated_source, monkeypatch, action):
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_publish", lambda self: False)
    fr = translated_source.translations["fr"]

    page_content = admin_client.get(translations_url(translated_source.page)).content.decode()
    response = admin_client.post(translations_url(translated_source.page), {"action": action, "translations": [fr.pk]})

    assert f'value="{action}"' not in page_content
    assert 'value="download"' in page_content
    assert 'value="stop"' in page_content
    assert response.status_code == 302
    assert response.url == "/cms-admin/"


def test_publish_checks_each_translated_page(admin_client, translated_source, monkeypatch, django_capture_on_commit_callbacks):
    # A group can publish the source page yet hold a lower level on its translations.
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_publish", lambda self: self.page.locale.language_code != "fr")
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(translations_url(translated_source.page), {"action": "publish", "translations": [fr.pk, de.pk]}, follow=True)

    messages = message_texts(response)
    assert "Published 1 of 2 locales: German." in messages
    assert "Could not publish French: you don't have permission to publish it" in messages
    assert Page.objects.get(pk=fr.get_target_instance().pk).live is False
    assert Page.objects.get(pk=de.get_target_instance().pk).live is True


def test_unpublish_takes_live_locales_offline(admin_client, translated_source, django_capture_on_commit_callbacks):
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]
    with django_capture_on_commit_callbacks(execute=True):
        fr.save_target(publish=True)

    response = admin_client.post(translations_url(translated_source.page), {"action": "unpublish", "translations": [fr.pk, de.pk]}, follow=True)

    messages = message_texts(response)
    assert "Unpublished 1 locales: French." in messages
    assert "Already not live, so left alone: German." in messages
    assert Page.objects.get(pk=fr.get_target_instance().pk).live is False


def test_stop_removes_locales_from_the_list(admin_client, translated_source):
    en_ca = translated_source.translations["en-CA"]
    target_page_id = en_ca.get_target_instance().pk

    response = admin_client.post(translations_url(translated_source.page), {"action": "stop", "translations": [en_ca.pk]}, follow=True)

    assert "Stopped syncing 1 locales: English (Canada)." in message_texts(response)[0]
    assert [row.translation.target_locale.language_code for row in response.context["rows"]] == ["de", "fr"]
    en_ca.refresh_from_db()
    assert en_ca.enabled is False
    assert Page.objects.filter(pk=target_page_id).exists()


def test_stopping_every_locale_keeps_them_listed_as_not_syncing(admin_client, translated_source):
    all_ids = [translation.pk for translation in translated_source.translations.values()]

    response = admin_client.post(translations_url(translated_source.page), {"action": "stop", "translations": all_ids}, follow=True)

    assert response.context["rows"] == []
    assert [row.page.locale.language_code for row in response.context["not_syncing_rows"]] == ["de", "en-CA", "fr"]
    assert "No locales are syncing with this page." in response.content.decode()


def test_publish_translations_isolates_failures():
    good, bad = MagicMock(), MagicMock()
    bad.save_target.side_effect = ValidationError("Slug clash")

    published, failed = publish_translations([bad, good], user=None)

    assert published == [good]
    assert failed == [(bad, "Slug clash")]


def test_button_shown_on_translation_source(translated_source):
    admin = WagtailUserFactory(username="superuser", is_superuser=True)

    assert [button.label for button in manage_translations_button(translated_source.page, admin)] == ["Manage translations"]


def test_button_hidden_on_translated_and_untranslated_pages(translated_source, minimal_site):
    admin = WagtailUserFactory(username="superuser", is_superuser=True)
    translated_page = translated_source.translations["fr"].get_target_instance()
    untranslated_page = SimpleRichTextPageFactory(slug="untranslated", parent=minimal_site.root_page)

    assert list(manage_translations_button(translated_page, admin)) == []
    assert list(manage_translations_button(untranslated_page, admin)) == []


def test_button_renders_in_page_header(admin_client, translated_source):
    page = translated_source.page

    content = admin_client.get(reverse("wagtailadmin_pages:edit", args=[page.id])).content.decode()

    assert translations_url(page) in content


def test_submit_translation_form_badges_alias_locales(minimal_site):
    LocaleFactory(language_code="en-CA")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)

    form = SubmitTranslationForm(page)

    labels = {locale.language_code: str(form.fields["locales"].label_from_instance(locale)) for locale in form.fields["locales"].queryset}
    assert labels["fr"] == "French"
    assert labels["en-CA"].endswith('<span class="w-status w-status--label locale-role-badge">alias → en-US</span>')


def test_submit_translation_form_offers_select_all_except_aliases(minimal_site):
    LocaleFactory(language_code="en-CA")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)

    form = SubmitTranslationForm(page)

    assert list(form.fields)[:3] == ["select_all", "select_all_except_aliases", "locales"]
    # The script identifies aliases by the badge inside the label wrapping each checkbox.
    labels = {
        int(value): label for value, label in re.findall(r'<label[^>]*>\s*<input[^>]*value="(\d+)"[^>]*>(.*?)</label>', str(form["locales"]), re.S)
    }
    assert "locale-role-badge" in labels[Locale.objects.get(language_code="en-CA").pk]
    assert "locale-role-badge" not in labels[Locale.objects.get(language_code="fr").pk]


def test_submit_translation_form_omits_except_aliases_without_aliases(minimal_site):
    LocaleFactory(language_code="de")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)

    assert "select_all_except_aliases" not in SubmitTranslationForm(page).fields


def test_submitting_several_locales_opens_manage_translations(admin_client, minimal_site):
    LocaleFactory(language_code="de")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)
    locale_ids = list(Locale.objects.filter(language_code__in=["fr", "de"]).values_list("pk", flat=True))

    response = admin_client.post(reverse("wagtail_localize:submit_page_translation", args=[page.id]), {"locales": locale_ids})

    assert response.status_code == 302
    assert response.url == translations_url(page)


def test_submitting_one_locale_opens_manage_translations(admin_client, minimal_site):
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)
    fr = Locale.objects.get(language_code="fr")

    response = admin_client.post(reverse("wagtail_localize:submit_page_translation", args=[page.id]), {"locales": [fr.pk]})

    assert response.status_code == 302
    assert response.url == translations_url(page)


def test_sync_banner_shown_when_source_changed_since_last_sync(admin_client, translated_source):
    assert admin_client.get(translations_url(translated_source.page)).context["sync_url"] is None

    page = translated_source.page
    page.content = "Updated copy that hasn't been synced"
    page.save_revision().publish()
    response = admin_client.get(translations_url(page))

    sync_url = reverse("wagtail_localize:update_translations", args=[translated_source.source.id])
    assert response.context["sync_url"] == f"{sync_url}?next=%2Fcms-admin%2Fpages%2F{page.id}%2Ftranslations%2F"
    assert "has changed since its translations were last synced" in response.content.decode()


def test_sync_banner_ignores_unpublished_drafts(admin_client, translated_source):
    page = translated_source.page
    page.content = "Draft copy"
    page.save_revision()

    assert admin_client.get(translations_url(page)).context["sync_url"] is None


def test_translated_via_counts_each_source(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    segments = list(StringSegment.objects.filter(source=fr.source).order_by("order"))
    editor = WagtailUserFactory(username="translator")
    assert len(segments) == 2
    for segment, tool_name in zip(segments, ["PO File", ""], strict=True):
        StringTranslation.objects.create(
            translation_of_id=segment.string_id,
            context_id=segment.context_id,
            locale=fr.target_locale,
            data="Traduit",
            tool_name=tool_name,
            last_translated_by=editor,
        )

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.translation.target_locale.language_code: row for row in response.context["rows"]}
    assert rows["fr"].translated_via == [("PO file", 1), ("Translation editor", 1)]
    assert "PO file (1)" in response.content.decode()


def test_upload_skips_locales_the_user_cannot_edit(admin_client, translated_source, monkeypatch):
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_edit", lambda self: self.page.locale.language_code != "fr")
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]
    files = [SimpleUploadedFile("fr.po", translated_po_bytes(fr, "Texte")), SimpleUploadedFile("de.po", translated_po_bytes(de, "Text"))]

    response = admin_client.post(translations_url(translated_source.page), {"action": "upload", "files": files}, follow=True)

    assert "Skipped fr.po: you don't have permission to edit French." in message_texts(response)
    assert first_segment_translation(fr) is None
    assert first_segment_translation(de).data == "Text"


def test_download_leaves_out_locales_the_user_cannot_edit(admin_client, translated_source, monkeypatch):
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_edit", lambda self: self.page.locale.language_code != "fr")
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]

    response = admin_client.post(translations_url(translated_source.page), {"action": "download", "translations": [fr.pk, de.pk]})

    assert zipfile.ZipFile(io.BytesIO(response.content)).namelist() == ["download-firefox-de.po"]


def test_sync_banner_shown_when_only_a_synchronized_field_changed(admin_client, translated_source):
    page = translated_source.page
    page.show_in_menus = not page.show_in_menus
    page.save_revision().publish()

    assert admin_client.get(translations_url(page)).context["sync_url"] is not None


def test_publish_translations_reports_unexpected_errors():
    good, bad = MagicMock(), MagicMock()
    bad.save_target.side_effect = RuntimeError("Parent page missing")

    published, failed = publish_translations([bad, good], user=None)

    assert published == [good]
    assert failed == [(bad, "an unexpected error occurred, and has been logged.")]


def test_translated_counts_ignore_strings_with_errors(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    segment = StringSegment.objects.filter(source=fr.source).order_by("order").first()
    StringTranslation.objects.create(
        translation_of_id=segment.string_id,
        context_id=segment.context_id,
        locale=fr.target_locale,
        data="Trop long",
        tool_name="PO File",
        has_error=True,
    )

    rows = {row.translation.target_locale.language_code: row for row in admin_client.get(translations_url(translated_source.page)).context["rows"]}

    assert rows["fr"].translated_segments == 0
    assert rows["fr"].translated_via == []


def test_submitting_several_locales_without_source_edit_rights_keeps_default_redirect(admin_client, minimal_site, monkeypatch):
    LocaleFactory(language_code="de")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)
    locale_ids = list(Locale.objects.filter(language_code__in=["fr", "de"]).values_list("pk", flat=True))
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_edit", lambda self: False)

    response = admin_client.post(reverse("wagtail_localize:submit_page_translation", args=[page.id]), {"locales": locale_ids})

    assert response.url == reverse("wagtailadmin_explore", args=[page.get_parent().id])


def test_progress_state_colours_complete_partial_and_untranslated():
    def row(translated):
        return TranslationRow(None, None, 4, translated, None, None, [])

    assert [row(translated).progress_state for translated in (4, 2, 0)] == ["complete", "partial", "none"]


def test_send_to_smartling_queues_a_job_for_eligible_locales(admin_client, translated_source, monkeypatch):
    fr, en_ca = translated_source.translations["fr"], translated_source.translations["en-CA"]
    calls = []
    monkeypatch.setattr(
        Job, "get_or_create_from_source_and_translation_data", lambda source, translations, **kwargs: calls.append((source, translations))
    )

    response = admin_client.post(translations_url(translated_source.page), {"action": "smartling", "translations": [fr.pk, en_ca.pk]}, follow=True)

    assert calls == [(translated_source.source, [fr])]
    messages = message_texts(response)
    assert messages[0].startswith("Sent 1 locales to Smartling for translation: French.")
    assert "Not sent, as these locales are never translated by Smartling: English (Canada)." in messages


def test_send_to_smartling_reports_when_smartling_is_unreachable(admin_client, translated_source, monkeypatch):
    def unreachable(*args, **kwargs):
        raise ConnectionError("Smartling is down")

    monkeypatch.setattr(Job, "get_or_create_from_source_and_translation_data", unreachable)
    fr = translated_source.translations["fr"]

    response = admin_client.post(translations_url(translated_source.page), {"action": "smartling", "translations": [fr.pk]}, follow=True)

    assert "Couldn't create the Smartling job, so nothing was sent. The error has been logged." in message_texts(response)


def test_rows_flag_smartling_jobs_sent_for_older_source(admin_client, translated_source):
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]
    create_smartling_job(translated_source.source, fr, JobStatus.COMPLETED, content_hash="older-source")
    create_smartling_job(translated_source.source, de, JobStatus.COMPLETED, content_hash=compute_content_hash(translated_source.source.export_po()))

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.translation.target_locale.language_code: row for row in response.context["rows"]}
    assert rows["fr"].smartling_outdated is True
    assert rows["de"].smartling_outdated is False
    assert "Source changed since last sent to Smartling" in response.content.decode()


def test_not_syncing_lists_stopped_and_never_synced_pages(admin_client, translated_source, django_capture_on_commit_callbacks):
    fr = translated_source.translations["fr"]
    with django_capture_on_commit_callbacks(execute=True):
        fr.save_target(publish=True)
    fr.enabled = False
    fr.save(update_fields=["enabled"])
    italian = LocaleFactory(language_code="it")
    translated_source.page.copy_for_translation(italian)

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.page.locale.language_code: row for row in response.context["not_syncing_rows"]}
    assert sorted(rows) == ["fr", "it"]
    assert rows["fr"].stopped_translation == fr
    assert rows["it"].stopped_translation is None
    content = response.content.decode()
    assert "Live, but not receiving source changes" in content
    assert "Syncing was stopped" in content
    assert "Never synced: created outside the translation workflow" in content
    assert content.count('name="action" value="restart"') == 1


def test_restart_resumes_syncing_a_stopped_locale(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    fr.enabled = False
    fr.save(update_fields=["enabled"])

    response = admin_client.post(translations_url(translated_source.page), {"action": "restart", "translation": fr.pk}, follow=True)

    fr.refresh_from_db()
    assert fr.enabled is True
    assert "Restarted syncing French. It now opens in the translation editor again." in message_texts(response)
    assert response.context["not_syncing_rows"] == []


def test_restart_rejects_a_locale_that_is_still_syncing(admin_client, translated_source):
    fr = translated_source.translations["fr"]

    assert admin_client.post(translations_url(translated_source.page), {"action": "restart", "translation": fr.pk}).status_code == 400


def test_submit_translation_form_omits_except_aliases_when_only_aliases_remain(minimal_site):
    LocaleFactory(language_code="en-CA")
    LocaleFactory(language_code="en-GB")
    page = SimpleRichTextPageFactory(slug="to-translate", parent=minimal_site.root_page)
    page.copy_for_translation(Locale.objects.get(language_code="fr"))

    assert "select_all_except_aliases" not in SubmitTranslationForm(page).fields


def test_send_to_smartling_refuses_while_source_is_behind(admin_client, translated_source, monkeypatch):
    calls = []
    monkeypatch.setattr(Job, "get_or_create_from_source_and_translation_data", lambda *args, **kwargs: calls.append(args))
    page = translated_source.page
    page.content = "Updated copy that hasn't been synced"
    page.save_revision().publish()
    fr = translated_source.translations["fr"]

    response = admin_client.post(translations_url(page), {"action": "smartling", "translations": [fr.pk]}, follow=True)

    assert calls == []
    assert message_texts(response)[0].startswith("Nothing was sent to Smartling: the source page has changes that haven't been synced")


def test_send_to_smartling_skips_locales_already_waiting_on_a_job(admin_client, translated_source, monkeypatch):
    fr, de = translated_source.translations["fr"], translated_source.translations["de"]
    create_smartling_job(translated_source.source, fr, JobStatus.IN_PROGRESS, content_hash=compute_content_hash(translated_source.source.export_po()))
    calls = []
    monkeypatch.setattr(Job, "get_or_create_from_source_and_translation_data", lambda source, translations, **kwargs: calls.append(translations))

    response = admin_client.post(translations_url(translated_source.page), {"action": "smartling", "translations": [fr.pk, de.pk]}, follow=True)

    assert calls == [[de]]
    assert "Not sent again, as they're already waiting on a Smartling job for this content: French." in message_texts(response)


def test_restart_rejects_a_malformed_translation_id(admin_client, translated_source):
    assert admin_client.post(translations_url(translated_source.page), {"action": "restart", "translation": "abc"}).status_code == 400


def test_restart_refused_without_edit_rights_on_the_locale(admin_client, translated_source, monkeypatch):
    fr = translated_source.translations["fr"]
    fr.enabled = False
    fr.save(update_fields=["enabled"])
    monkeypatch.setattr("wagtail.models.pages.PagePermissionTester.can_edit", lambda self: self.page.locale.language_code != "fr")

    response = admin_client.post(translations_url(translated_source.page), {"action": "restart", "translation": fr.pk}, follow=True)

    fr.refresh_from_db()
    assert fr.enabled is False
    assert "Could not restart syncing French: you don't have permission to edit it." in message_texts(response)


def test_stopped_locale_without_a_page_stays_listed_for_restart(admin_client, translated_source):
    italian = LocaleFactory(language_code="it")
    not_created = Translation.objects.create(source=translated_source.source, target_locale=italian, enabled=False)

    response = admin_client.get(translations_url(translated_source.page))

    rows = {row.locale.language_code: row for row in response.context["not_syncing_rows"]}
    assert rows["it"].page is None
    assert rows["it"].stopped_translation == not_created
    assert f'name="translation" value="{not_created.pk}"' in response.content.decode()


def test_upload_explains_files_for_stopped_locales(admin_client, translated_source):
    fr = translated_source.translations["fr"]
    po_bytes = translated_po_bytes(fr, "Texte")
    fr.enabled = False
    fr.save(update_fields=["enabled"])

    response = admin_client.post(
        translations_url(translated_source.page), {"action": "upload", "files": [SimpleUploadedFile("fr.po", po_bytes)]}, follow=True
    )

    assert "Skipped fr.po: French isn't syncing; restart it under “Not syncing” first." in message_texts(response)


def test_untracked_translations_are_listed_as_never_synced(admin_client, minimal_site):
    LocaleFactory(language_code="de")
    original = SimpleRichTextPageFactory(slug="untracked", parent=minimal_site.root_page)
    copy = original.copy_for_translation(Locale.objects.get(language_code="de"))
    admin = WagtailUserFactory(username="superuser", is_superuser=True)

    response = admin_client.get(translations_url(original))

    assert response.status_code == 200
    assert [(row.locale.language_code, row.stopped_translation) for row in response.context["not_syncing_rows"]] == [("de", None)]
    assert "Never synced: created outside the translation workflow" in response.content.decode()
    assert [button.label for button in manage_translations_button(original, admin)] == ["Manage translations"]
    assert list(manage_translations_button(copy, admin)) == []
