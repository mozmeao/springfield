# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to migrate download button labels from the old plain-string
format to the new pretranslated_label (snippet FK) / custom_label (text) structure.

Also re-syncs all Wagtail-Localize TranslationSources for affected page models so the
new block structure is reflected in translated content.

Two-pass conversion:
  Pass 1 — English pages: map label text to ButtonLabelSnippet ID (or fall back to
            custom_label for unrecognised strings). Record (page.translation_key,
            block_id) → snippet_id in english_block_labels.
  Pass 2 — Non-English pages: match the old label text against ButtonLabelSnippet records
            for the page's locale. If a match is found, store the locale-specific snippet pk
            (wagtail-localize convention). If no match is found, the label becomes custom_label.

The same two-pass approach is applied to page revisions.
"""

import json
import logging
from collections.abc import MutableSequence

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale, Revision

logger = logging.getLogger(__name__)

LABEL_TO_SNIPPET_ID = {
    "Get Firefox": settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID,
    "Download Firefox": settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID,
}
DEFAULT_SNIPPET_ID = settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID

PAGE_MODELS_AND_FIELDS = [
    ("HomePage", ["upper_content", "lower_content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("FreeFormPage", ["content"]),
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage", ["content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]


def convert_english_download_button_label(data):
    """Recursively convert label in download_button blocks for English pages.

    Maps known label strings to ButtonLabelSnippet IDs (pretranslated_label).
    Unrecognised strings become custom_label. Returns True if any change was made.
    The isinstance(old_label, str) check is the idempotency guard.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                snippet_id = LABEL_TO_SNIPPET_ID.get(old_label)
                if snippet_id:
                    value["pretranslated_label"] = snippet_id
                    value["custom_label"] = ""
                else:
                    value["pretranslated_label"] = None
                    value["custom_label"] = old_label
                del value["label"]
                changed = True
        for v in list(data.values()):
            if convert_english_download_button_label(v):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_english_download_button_label(item):
                changed = True
    return changed


def collect_english_block_labels(data, translation_key, out):
    """Walk converted English StreamField data and record snippet IDs by block ID.

    Populates out[(translation_key, block_id)] = snippet_id for each download_button.
    """
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            block_id = data.get("id")
            snippet_id = data["value"].get("pretranslated_label")
            if block_id is not None and snippet_id is not None:
                out[(translation_key, block_id)] = snippet_id
        for v in data.values():
            collect_english_block_labels(v, translation_key, out)
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            collect_english_block_labels(item, translation_key, out)


def build_localized_label_map(english_locale_ids):
    """Build a map of (locale_id, label_text) → locale-specific ButtonLabelSnippet pk.

    Used to resolve non-English button labels by label text. Wagtail-localize convention
    is that translated pages store locale-specific FK values, so non-English pages should
    reference their own locale's ButtonLabelSnippet rather than the English one.
    """
    from springfield.cms.models import ButtonLabelSnippet

    return {(s.locale_id, s.label): s.pk for s in ButtonLabelSnippet.objects.exclude(locale_id__in=english_locale_ids)}


def convert_non_english_download_button_label(data, translation_key, english_block_labels, locale_id=None, localized_label_map=None):
    """Recursively convert label in download_button blocks for non-English pages.

    Matches the old label text against ButtonLabelSnippet records for the same locale:
    - If a match is found, stores the locale-specific snippet pk (wagtail-localize convention).
    - If no match is found, the old label becomes custom_label.

    Note: english_block_labels and translation_key are accepted for signature compatibility
    but are no longer used for lookup — block-ID matching was removed because it caused
    custom-text buttons to be incorrectly overwritten with a standard snippet when their
    English counterpart happened to use that snippet.
    Returns True if any change was made.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                snippet_id = None
                if locale_id is not None and localized_label_map is not None:
                    snippet_id = localized_label_map.get((locale_id, old_label))
                if snippet_id is not None:
                    value["pretranslated_label"] = snippet_id
                    value["custom_label"] = ""
                else:
                    value["pretranslated_label"] = None
                    value["custom_label"] = old_label
                del value["label"]
                changed = True
        for v in list(data.values()):
            if convert_non_english_download_button_label(v, translation_key, english_block_labels, locale_id, localized_label_map):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_non_english_download_button_label(item, translation_key, english_block_labels, locale_id, localized_label_map):
                changed = True
    return changed


class Command(BaseCommand):
    help = "Migrate download button labels from plain strings to pretranslated_label/custom_label."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made.\n"))

        english_block_labels, localized_label_map = self._convert_pages(dry_run)
        self._convert_revisions(dry_run, english_block_labels, localized_label_map)
        self._update_translation_sources(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _convert_pages(self, dry_run):
        """Convert page StreamFields. Returns english_block_labels dict for use by _convert_revisions."""
        self.stdout.write("Converting download_button labels in page StreamFields...\n")
        english_locale_ids = set(Locale.objects.filter(language_code__startswith="en").values_list("pk", flat=True))
        english_block_labels = {}
        localized_label_map = build_localized_label_map(english_locale_ids)
        total_english = 0
        total_non_english = 0

        # Pass 1: English pages
        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.filter(locale_id__in=english_locale_ids):
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value and convert_english_download_button_label(stream_value.raw_data):
                        changed_fields.append(field_name)
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    total_english += 1
                    self.stdout.write(f"  [EN] {model_name} pk={page.pk}: updated {', '.join(changed_fields)}\n")
                # Collect block labels from (now-converted) English data
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value:
                        collect_english_block_labels(stream_value.raw_data, page.translation_key, english_block_labels)

        self.stdout.write(f"  Pass 1 (English): {total_english} pages updated.\n")

        # Pass 2: Non-English pages
        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.exclude(locale_id__in=english_locale_ids):
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value and convert_non_english_download_button_label(
                        stream_value.raw_data,
                        page.translation_key,
                        english_block_labels,
                        locale_id=page.locale_id,
                        localized_label_map=localized_label_map,
                    ):
                        changed_fields.append(field_name)
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    total_non_english += 1
                    self.stdout.write(f"  [non-EN] {model_name} pk={page.pk}: updated {', '.join(changed_fields)}\n")

        self.stdout.write(f"  Pass 2 (non-English): {total_non_english} pages updated.\n")
        return english_block_labels, localized_label_map

    def _convert_revisions(self, dry_run, english_block_labels, localized_label_map):
        """Convert page revisions. Augments english_block_labels with revision data."""
        self.stdout.write("Converting download_button labels in page revisions...\n")
        english_locale_ids = set(Locale.objects.filter(language_code__startswith="en").values_list("pk", flat=True))

        page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]
        field_names = ["content", "upper_content", "lower_content"]
        total_english = 0
        total_non_english = 0

        # Pass 1: English revisions — convert and augment english_block_labels
        for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
            locale_id = revision.content.get("locale")
            if locale_id not in english_locale_ids:
                continue
            translation_key = revision.content.get("translation_key")
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if convert_english_download_button_label(field_data):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                    if translation_key:
                        collect_english_block_labels(field_data, translation_key, english_block_labels)
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total_english += 1

        self.stdout.write(f"  Pass 1 (English revisions): {total_english} updated.\n")

        # Pass 2: Non-English revisions
        for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
            locale_id = revision.content.get("locale")
            if locale_id in english_locale_ids or locale_id is None:
                continue
            translation_key = revision.content.get("translation_key")
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if convert_non_english_download_button_label(
                        field_data,
                        translation_key,
                        english_block_labels,
                        locale_id=locale_id,
                        localized_label_map=localized_label_map,
                    ):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total_non_english += 1

        self.stdout.write(f"  Pass 2 (non-English revisions): {total_non_english} updated.\n")

    def _update_translation_sources(self, dry_run):
        """Re-sync TranslationSource schema so wagtail-localize sees the new block structure.

        Only updates the source's serialized content — does NOT call
        create_or_update_translation(), which would re-materialize all translated pages
        and can silently drop blocks whose segments don't match the updated schema.
        Translated pages still render correctly via the old-format fallback in
        DownloadFirefoxButtonBlock.get_context(); they'll be re-synced through the
        normal Smartling workflow on next publish.
        """
        from wagtail_localize.models import TranslationSource

        self.stdout.write("Updating TranslationSource records...\n")

        if dry_run:
            self.stdout.write("  Skipping TranslationSource sync in dry-run mode.\n")
            return

        page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
        # Only page models — ButtonLabelSnippet TranslationSources are managed by
        # create_button_label_snippets, not by this command.
        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]

        sources_updated = 0
        for source in TranslationSource.objects.filter(specific_content_type_id__in=content_type_ids):
            try:
                source.update_from_db()
                sources_updated += 1
            except Exception:
                ct = ContentType.objects.get_for_id(source.specific_content_type_id)
                try:
                    obj = source.get_source_instance()
                except Exception:
                    obj = None
                logger.warning(
                    "Failed to update TranslationSource pk=%s (%s.%s, object_id=%s, page=%s).",
                    source.pk,
                    ct.app_label,
                    ct.model,
                    source.object_id,
                    obj,
                    exc_info=True,
                )

        self.stdout.write(f"  {sources_updated} TranslationSources updated.\n")
