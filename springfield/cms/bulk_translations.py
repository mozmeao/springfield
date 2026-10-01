# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Work on every locale of one translation source at once.

Downloads and uploads .po files, publishes, unpublishes, stops and restarts syncing,
sends locales to Smartling, and finds translated pages that aren't syncing.
"""

import io
import json
import logging
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.utils.text import slugify

import polib
from wagtail.models import Page
from wagtail_localize.fields import get_translatable_fields
from wagtail_localize.models import StringSegment, StringTranslation, TranslationSource
from wagtail_localize_smartling.api.types import JobStatus
from wagtail_localize_smartling.constants import UNSYNCED_OR_PENDING_STATUSES
from wagtail_localize_smartling.models import Job
from wagtail_localize_smartling.settings import settings as smartling_settings
from wagtail_localize_smartling.utils import compute_content_hash

logger = logging.getLogger(__name__)

TRANSLATION_ID_HEADER = "X-WagtailLocalize-TranslationID"

FINISHED_JOB_STATUSES = {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.CLOSED, JobStatus.DELETED}


def alias_target(locale):
    """The locale code an alias locale serves content from, or None."""
    return settings.FALLBACK_LOCALES.get(locale.language_code)


def has_unsynced_source_changes(source):
    """True if syncing would change anything: a translated or synchronized field of the live source differs from the last sync.

    Both sides use the same serialization wagtail-localize stores on sync, so no segments need extracting.
    """
    live = source.get_source_instance()
    live_data = json.loads(live.to_json())
    synced_data = json.loads(source.content_json)
    return any(
        live_data.get(translatable_field.field_name) != synced_data.get(translatable_field.field_name)
        for translatable_field in get_translatable_fields(live.__class__)
        if translatable_field.is_translated(live) or translatable_field.is_synchronized(live)
    )


def enabled_translations(source):
    return source.translations.filter(enabled=True).select_related("target_locale").order_by("target_locale__language_code")


@dataclass
class TranslationRow:
    translation: object
    alias_of: str | None
    total_segments: int
    translated_segments: int
    target_page: object | None
    smartling_job: object | None
    translated_via: list
    smartling_outdated: bool = False
    checked: bool = False

    @property
    def progress_state(self):
        if self.is_fully_translated:
            return "complete"
        return "partial" if self.translated_segments else "none"

    @property
    def open_smartling_job(self):
        if self.smartling_job is not None and self.smartling_job.status not in FINISHED_JOB_STATUSES:
            return self.smartling_job
        return None

    @property
    def percent_translated(self):
        if not self.total_segments:
            return 100
        return int(self.translated_segments / self.total_segments * 100)

    @property
    def is_fully_translated(self):
        return self.translated_segments >= self.total_segments


def _translated_via_label(tool_name, user_id, has_smartling_job):
    if tool_name == "PO File":
        return "PO file"
    if tool_name:
        return tool_name
    if user_id is not None:
        return "Translation editor"
    # Smartling's import records neither a tool nor a user.
    return "Smartling" if has_smartling_job else "Imported"


def build_rows(source, translations, selected_ids=None):
    """One row per translation, checked only if it's in the submitted selection.

    Progress and sources are counted in bulk, the same way as Translation.get_progress().
    """
    translations = list(translations.prefetch_related("smartling_jobs"))
    locale_ids = [translation.target_locale_id for translation in translations]
    segment_keys = set(StringSegment.objects.filter(source=source).values_list("string_id", "context_id"))
    target_pages = {page.locale_id: page for page in Page.objects.filter(translation_key=source.object_id, locale_id__in=locale_ids)}

    via_counts = {locale_id: Counter() for locale_id in locale_ids}
    translated_counts = Counter()
    latest_jobs = {translation.pk: max(translation.smartling_jobs.all(), key=lambda job: job.pk, default=None) for translation in translations}
    has_job_by_locale = {translation.target_locale_id: latest_jobs[translation.pk] is not None for translation in translations}
    string_translations = StringTranslation.objects.filter(
        locale_id__in=locale_ids,
        context__object_id=source.object_id,
        translation_of__in=StringSegment.objects.filter(source=source).values("string"),
        has_error=False,
    ).values_list("locale_id", "translation_of_id", "context_id", "tool_name", "last_translated_by_id")
    for locale_id, string_id, context_id, tool_name, user_id in string_translations:
        if (string_id, context_id) not in segment_keys:
            continue
        translated_counts[locale_id] += 1
        via_counts[locale_id][_translated_via_label(tool_name, user_id, has_job_by_locale[locale_id])] += 1

    current_content_hash = compute_content_hash(source.export_po())

    def is_outdated(job):
        # Older jobs have no hash recorded, so their freshness is unknown.
        return job is not None and bool(job.content_hash) and job.content_hash != current_content_hash

    return [
        TranslationRow(
            translation=translation,
            alias_of=alias_target(translation.target_locale),
            total_segments=len(segment_keys),
            translated_segments=translated_counts[translation.target_locale_id],
            target_page=target_pages.get(translation.target_locale_id),
            smartling_job=latest_jobs[translation.pk],
            translated_via=sorted(via_counts[translation.target_locale_id].items(), key=lambda item: (-item[1], item[0])),
            smartling_outdated=is_outdated(latest_jobs[translation.pk]),
            checked=selected_ids is not None and str(translation.pk) in selected_ids,
        )
        for translation in translations
    ]


def po_filename(translation):
    # Same naming as wagtail-localize's single-locale download.
    return f"{slugify(translation.source.object_repr)}-{translation.target_locale.language_code}.po"


def build_po_zip(translations):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for translation in translations:
            archive.writestr(po_filename(translation), str(translation.export_po()))
    return buffer.getvalue()


def zip_filename(source):
    return f"{slugify(source.object_repr)}-translations.zip"


@dataclass
class ImportResult:
    imported: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


def _parse_po(uploaded_file):
    # polib.pofile() reads its argument as a path when one exists on disk, so
    # uploaded content is parsed from a temp file rather than passed directly.
    with tempfile.NamedTemporaryFile(suffix=".po") as temp:
        for chunk in uploaded_file.chunks():
            temp.write(chunk)
        temp.flush()
        return polib.pofile(temp.name)


def import_po_files(translations, uploaded_files, user):
    """Import each file into the translation its embedded ID names; skip the rest.

    Pass every translation of the source, so files for stopped locales get a clear reason.
    """
    by_uuid = {str(translation.uuid): translation for translation in translations}
    result = ImportResult()
    seen = set()

    with transaction.atomic():
        for uploaded_file in uploaded_files:
            try:
                po = _parse_po(uploaded_file)
            except (OSError, UnicodeDecodeError):
                result.skipped.append((uploaded_file.name, "not a valid PO file"))
                continue

            translation = by_uuid.get(po.metadata.get(TRANSLATION_ID_HEADER, ""))
            if translation is None:
                result.skipped.append((uploaded_file.name, "it was downloaded for a different page or locale"))
                continue
            if not translation.enabled:
                result.skipped.append(
                    (uploaded_file.name, f"{translation.target_locale.get_display_name()} isn't syncing; restart it under “Not syncing” first")
                )
                continue
            if translation.pk in seen:
                result.skipped.append((uploaded_file.name, f"another file for {translation.target_locale.get_display_name()} was already imported"))
                continue

            if not can_edit_translation(translation, user):
                result.skipped.append((uploaded_file.name, f"you don't have permission to edit {translation.target_locale.get_display_name()}"))
                continue

            seen.add(translation.pk)
            warnings = translation.import_po(po, user=user, tool_name="PO File")
            result.imported.append((uploaded_file.name, translation, warnings))

    return result


def _target_page_or_none(translation):
    try:
        return translation.get_target_instance()
    except ObjectDoesNotExist:
        return None


def can_edit_translation(translation, user):
    """Whether the user may edit this locale's page; one not created yet falls back to the caller's source check."""
    target_page = _target_page_or_none(translation)
    return target_page is None or target_page.permissions_for_user(user).can_edit()


def publish_translations(translations, user):
    """Publish each translation, isolating failures so one locale can't block the rest.

    Rights on the source page don't imply rights on its translations, so each existing
    translated page is checked; one not created yet falls back to the caller's check.
    """
    published, failed = [], []
    for translation in translations:
        target_page = _target_page_or_none(translation)
        if target_page is not None and not target_page.permissions_for_user(user).can_publish():
            failed.append((translation, "you don't have permission to publish it"))
            continue
        try:
            with transaction.atomic():
                translation.save_target(user=user, publish=True)
        except ValidationError as error:
            failed.append((translation, " ".join(error.messages)))
        except Exception:
            logger.exception("Publishing translation %s failed", translation.pk)
            failed.append((translation, "an unexpected error occurred, and has been logged."))
        else:
            published.append(translation)
    return published, failed


def unpublish_translations(translations, user):
    """Unpublish each translation's live page; ones that aren't live are left alone."""
    unpublished, not_live, failed = [], [], []
    for translation in translations:
        page = _target_page_or_none(translation)
        if page is None or not page.live:
            not_live.append(translation)
            continue
        try:
            page.unpublish(user=user)
        except PermissionDenied:
            failed.append((translation, "you don't have permission to unpublish it"))
        else:
            unpublished.append(translation)
    return unpublished, not_live, failed


def stop_translations(translations, user):
    """Stop syncing these locales, as wagtail-localize's "Stop translation" does; pages are kept."""
    stopped, failed = [], []
    for translation in translations:
        if not can_edit_translation(translation, user):
            failed.append((translation, "you don't have permission to edit it"))
            continue
        translation.enabled = False
        translation.save(update_fields=["enabled"])
        stopped.append(translation)
    return stopped, failed


def send_to_smartling(source, translations, user):
    """Queue a Smartling job for these locales, as the "Translate" form's Smartling option does.

    Returns the locales newly sent, those already waiting on a job for this content, and
    those Smartling is configured never to receive. Raises if Smartling can't be reached.
    """
    excluded = [translation for translation in translations if translation.target_locale.language_code in smartling_settings.EXCLUDE_LOCALES]
    queued_locale_ids = set(
        Job.objects.filter(
            translation_source=source,
            content_hash=compute_content_hash(source.export_po()),
            status__in=UNSYNCED_OR_PENDING_STATUSES,
        ).values_list("translations__target_locale_id", flat=True)
    )
    already_queued = [
        translation for translation in translations if translation not in excluded and translation.target_locale_id in queued_locale_ids
    ]
    sent = [translation for translation in translations if translation not in excluded and translation not in already_queued]
    if sent:
        Job.get_or_create_from_source_and_translation_data(source, sent, user=user, due_date=None)
    return sent, already_queued, excluded


@dataclass
class NotSyncingRow:
    locale: object
    page: object | None
    stopped_translation: object | None

    @property
    def alias_of(self):
        return alias_target(self.locale)


def build_not_syncing_rows(source, page):
    """Locales that don't receive source changes: stopped syncs (with or without a page) and pages never synced.

    The source may be None when the page's translations were all made outside wagtail-localize.
    """
    translations = source.translations.select_related("target_locale") if source is not None else []
    syncing_locale_ids = {translation.target_locale_id for translation in translations if translation.enabled}
    stopped = {translation.target_locale_id: translation for translation in translations if not translation.enabled}
    # Wagtail alias pages mirror their original, so they never fall behind.
    pages = page.get_translations().filter(alias_of__isnull=True).exclude(locale_id__in=syncing_locale_ids).select_related("locale")
    rows = [
        NotSyncingRow(locale=translated_page.locale, page=translated_page, stopped_translation=stopped.get(translated_page.locale_id))
        for translated_page in pages
    ]
    locale_ids_with_pages = {row.locale.pk for row in rows}
    rows += [
        NotSyncingRow(locale=translation.target_locale, page=None, stopped_translation=translation)
        for locale_id, translation in stopped.items()
        if locale_id not in locale_ids_with_pages
    ]
    return sorted(rows, key=lambda row: row.locale.language_code)


def has_translations(page):
    """Whether "Manage translations" applies: the page is the source of tracked translations,
    or the original of other-locale pages made outside wagtail-localize."""
    source = TranslationSource.objects.get_for_instance_or_none(page)
    if source is not None and source.translations.exists():
        return True
    # Untracked pages have no recorded source, so the oldest page stands in for it, as in the translations dashboard.
    oldest_page_id = Page.objects.filter(translation_key=page.translation_key).order_by("pk").values_list("pk", flat=True).first()
    return oldest_page_id == page.pk and page.get_translations().filter(alias_of__isnull=True).exists()


def restart_translation(translation, user):
    """Resume syncing a stopped locale, as wagtail-localize's "Start Synced translation" does; False if not permitted."""
    if not can_edit_translation(translation, user):
        return False
    translation.enabled = True
    translation.save(update_fields=["enabled"])
    return True
