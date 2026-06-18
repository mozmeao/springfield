# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to migrate download button labels from the old plain-string
format to the new pretranslated_label (snippet FK) / custom_label (text) structure.

Also re-syncs all Wagtail-Localize TranslationSources for affected page models so the
new block structure is reflected in translated content.

Each page's old label text is matched against PretranslatedPhrase records for the page's
own locale. If a match is found, the locale-specific snippet pk is stored (wagtail-localize
convention — translated pages reference their own locale's snippet). If no match is found,
the old label becomes custom_label.

The same conversion is applied to page revisions (in a single table scan).
"""

import json
import logging
from collections.abc import MutableSequence

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Revision

logger = logging.getLogger(__name__)


PAGE_MODELS_AND_FIELDS = [
    ("HomePage", ["upper_content", "lower_content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]


def build_label_map():
    """Build a map of (locale_id, label_text) → PretranslatedPhrase pk for every locale.

    Keying by locale is important because multiple English locales (en-US, en-GB, en-CA, …)
    all share the same label text but have distinct PretranslatedPhrase records, and each
    page should reference its own locale's snippet.
    """
    from springfield.cms.models import PretranslatedPhrase  # noqa: PLC0415 — deferred to avoid circular import at module load

    return {(s.locale_id, s.label): s.pk for s in PretranslatedPhrase.objects.all()}


def convert_download_button_label(data, locale_id, label_map):
    """Recursively convert label in download_button blocks for a page in a given locale.

    Matches the old label text against the (locale_id, label) → snippet pk map:
    - If a match is found, stores the locale-specific snippet pk.
    - If no match is found, the old label becomes custom_label.

    Returns True if any change was made. The isinstance(old_label, str) check is the
    idempotency guard.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                snippet_id = label_map.get((locale_id, old_label))
                if snippet_id is not None:
                    value["pretranslated_label"] = snippet_id
                    value["custom_label"] = ""
                else:
                    value["pretranslated_label"] = None
                    value["custom_label"] = old_label
                del value["label"]
                changed = True
        for v in list(data.values()):
            if convert_download_button_label(v, locale_id, label_map):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_download_button_label(item, locale_id, label_map):
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

        label_map = self._convert_pages(dry_run)
        self._convert_revisions(dry_run, label_map)
        self._update_translation_sources(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _convert_pages(self, dry_run):
        """Convert page StreamFields. Returns label_map for use by _convert_revisions."""
        self.stdout.write("Converting download_button labels in page StreamFields...\n")
        label_map = build_label_map()
        total = 0

        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.all():
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value and convert_download_button_label(stream_value.raw_data, page.locale_id, label_map):
                        changed_fields.append(field_name)
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    total += 1
                    self.stdout.write(f"  {model_name} pk={page.pk} locale_id={page.locale_id}: updated {', '.join(changed_fields)}\n")

        self.stdout.write(f"  {total} pages updated.\n")
        return label_map

    def _convert_revisions(self, dry_run, label_map):
        """Convert page revisions in a single table scan."""
        self.stdout.write("Converting download_button labels in page revisions...\n")
        page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
        content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]
        field_names = ["content", "upper_content", "lower_content"]
        total_revised = 0

        for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
            locale_id = revision.content.get("locale")
            if locale_id is None:
                continue
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if convert_download_button_label(field_data, locale_id, label_map):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total_revised += 1

        self.stdout.write(f"  {total_revised} revisions updated.\n")

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
        # Only page models — PretranslatedPhrase TranslationSources are managed by
        # create_pretranslated_phrases, not by this command.
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
