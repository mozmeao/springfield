# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
One-time management command to migrate download button labels from the old
plain-string format to the new FluentOrCustomTextBlock format.

Migrates:
  - PreFooterCTASnippet: label_old -> pretranslated_label + custom_label
  - DownloadFirefoxButtonBlock (in page StreamFields): plain string label ->
    {pretranslated_or_custom, custom_text}
  - Wagtail page revisions: same StreamField conversion
  - TranslationSource records: re-syncs so wagtail-localize sees the new
    block structure, then regenerates translated pages

After running in all environments, remove the deprecated label_old field
from PreFooterCTASnippet and add a RemoveField migration.
"""

import json
import logging
from collections.abc import MutableSequence

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.blocks import CharBlock
from wagtail.models import Locale, Page, Revision
from wagtail_localize.models import Translation, TranslationSource

from springfield.cms.models.snippets import PreFooterCTASnippet

logger = logging.getLogger(__name__)

# These use fluent IDs from globally-loaded FTL files (navigation-firefox.ftl,
# download_button.ftl) so translations already exist in all locales.
LABEL_TO_PRESET = {
    "Get Firefox": "navigation-get-firefox",
    "Download Firefox": "download-button-download-firefox",
}
DEFAULT_PRESET = "download-button-download-firefox"

PAGE_MODELS_AND_FIELDS = [
    ("HomePage", ["upper_content", "lower_content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("FreeFormPage", ["content"]),
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage", ["content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]


def convert_download_button_label(data, is_english=True):
    """Recursively convert label in download_button blocks. Returns True if any change was made.

    For English pages, matches label text to a fluent preset; unrecognised
    labels are kept as custom text.  For non-English pages, the translated
    label text is not useful (fluent handles it), so we always use
    DEFAULT_PRESET.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                if is_english:
                    preset = LABEL_TO_PRESET.get(old_label)
                    if preset:
                        value["label"] = {"pretranslated_or_custom": preset, "custom_text": ""}
                    else:
                        value["label"] = {"pretranslated_or_custom": "custom", "custom_text": old_label}
                else:
                    value["label"] = {"pretranslated_or_custom": DEFAULT_PRESET, "custom_text": ""}
                changed = True
        for v in list(data.values()):
            if convert_download_button_label(v, is_english=is_english):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_download_button_label(item, is_english=is_english):
                changed = True
    return changed


class Command(BaseCommand):
    help = "Migrate download button labels from plain strings to FluentOrCustomTextBlock format."

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
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        self._migrate_snippets(dry_run)
        self._convert_pages(dry_run)
        self._convert_revisions(dry_run)
        self._update_translation_sources(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete. No changes were made."))
        else:
            self.stdout.write(self.style.SUCCESS("Migration complete."))

    def _migrate_snippets(self, dry_run):
        self.stdout.write("Migrating PreFooterCTASnippet labels...")

        # Pass 1: Migrate English snippets using text matching.
        count = 0
        for snippet in PreFooterCTASnippet.objects.filter(locale__language_code__startswith="en"):
            preset = LABEL_TO_PRESET.get(snippet.label_old)
            if preset:
                snippet.pretranslated_label = preset
                snippet.custom_label = ""
            else:
                snippet.pretranslated_label = "custom"
                snippet.custom_label = snippet.label_old
                self.stdout.write(f"  PreFooterCTASnippet pk={snippet.pk} has custom label_old={snippet.label_old!r}, keeping as custom text")
            if not dry_run:
                snippet.save(update_fields=["pretranslated_label", "custom_label"])
            count += 1
        self.stdout.write(f"  Pass 1 (English): {count} snippets processed.")

        # Pass 2: Migrate non-English snippets by copying the English sibling's preset.
        count = 0
        for snippet in PreFooterCTASnippet.objects.exclude(locale__language_code__startswith="en"):
            english_sibling = PreFooterCTASnippet.objects.filter(
                translation_key=snippet.translation_key,
                locale__language_code__startswith="en",
            ).first()
            if english_sibling and english_sibling.pretranslated_label:
                snippet.pretranslated_label = english_sibling.pretranslated_label
                if english_sibling.pretranslated_label == "custom":
                    # Preserve the non-English translated label as custom text.
                    snippet.custom_label = snippet.label_old
                else:
                    snippet.custom_label = ""
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  PreFooterCTASnippet pk={snippet.pk} (locale={snippet.locale.language_code}) "
                        f"has no English sibling, defaulting to {DEFAULT_PRESET}"
                    )
                )
                snippet.pretranslated_label = DEFAULT_PRESET
                snippet.custom_label = ""
            if not dry_run:
                snippet.save(update_fields=["pretranslated_label", "custom_label"])
            count += 1
        self.stdout.write(f"  Pass 2 (non-English): {count} snippets processed.")

    def _convert_pages(self, dry_run):
        self.stdout.write("Converting download_button labels in page StreamFields...")
        total = 0
        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.all():
                is_english = page.locale.language_code.startswith("en")
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value and convert_download_button_label(stream_value.raw_data, is_english=is_english):
                        changed_fields.append(field_name)
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    total += 1
                    self.stdout.write(f"  {model_name} pk={page.pk}: updated {', '.join(changed_fields)}")
        self.stdout.write(f"  {total} pages updated.")

    def _convert_revisions(self, dry_run):
        self.stdout.write("Converting download_button labels in page revisions...")

        english_locale_ids = set(Locale.objects.filter(language_code__startswith="en").values_list("pk", flat=True))

        page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]

        field_names = ["content", "upper_content", "lower_content"]
        total = 0

        for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
            locale_id = revision.content.get("locale")
            is_english = locale_id in english_locale_ids if locale_id else True
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if convert_download_button_label(field_data, is_english=is_english):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total += 1
        self.stdout.write(f"  {total} revisions updated.")

    def _update_translation_sources(self, dry_run):
        """Re-sync TranslationSource records so wagtail-localize sees the new block structure.

        Temporarily patches CharBlock.to_python to return "" instead of None,
        working around a wagtail-localize incompatibility where extract_segments()
        crashes on None values from optional CharBlock fields (e.g. in
        wagtail_link_block's LinkBlock).
        """
        self.stdout.write("Updating TranslationSource records...")

        if dry_run:
            self.stdout.write("  Skipping TranslationSource sync in dry-run mode.")
            return

        page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
        all_models = page_models + [PreFooterCTASnippet]
        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in all_models]

        original_to_python = CharBlock.to_python
        original_get_default = CharBlock.get_default

        def safe_to_python(self, value):
            result = original_to_python(self, value)
            return result if result is not None else ""

        def safe_get_default(self):
            result = original_get_default(self)
            return result if result is not None else ""

        CharBlock.to_python = safe_to_python
        CharBlock.get_default = safe_get_default
        try:
            sources_updated = 0
            translations_synced = 0
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
                    continue

                # Regenerate translated pages so they pick up the new block structure.
                # Only publish pages that are already live to avoid accidentally
                # publishing draft content.
                for translation in Translation.objects.filter(source=source):
                    try:
                        translated_instance = source.get_translated_instance(translation.target_locale)
                        is_live = translated_instance.live if isinstance(translated_instance, Page) else True
                        source.create_or_update_translation(
                            translation.target_locale,
                            publish=is_live,
                            fallback=True,
                        )
                        translations_synced += 1
                    except Exception:
                        logger.warning(
                            "Failed to sync translation for TranslationSource pk=%s to locale %s.",
                            source.pk,
                            translation.target_locale.language_code,
                            exc_info=True,
                        )
        finally:
            CharBlock.to_python = original_to_python
            CharBlock.get_default = original_get_default

        self.stdout.write(f"  {sources_updated} TranslationSources updated, {translations_synced} translations synced.")
