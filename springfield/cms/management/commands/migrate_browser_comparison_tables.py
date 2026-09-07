# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command converting comparison_table blocks that used the removed
"browser-comparison" variant into the browser_comparison_table block type.

A comparison table that never used the variant keeps its type and only loses the
variant key, which the block no longer defines. Its cells can no longer hold optional
content either, so any that still do are reported for an author to move over by hand.

The same conversion is applied to page revisions, so the CMS editor and the live page
agree on what a page holds.
"""

import json
import logging
from collections.abc import MutableSequence

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Revision
from wagtail_localize.models import TranslationSource

logger = logging.getLogger(__name__)

BROWSER_VARIANT = "browser-comparison"

# Block types. A tab names each of its table fields after the block type that field
# accepts, which is why a retyped table also has to move between them.
TABLE_TYPE = "comparison_table"
BROWSER_TABLE_TYPE = "browser_comparison_table"

# Page models and StreamFields that can reach a comparison_table block.
PAGE_MODELS_AND_FIELDS = [
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("SmartWindowPage", ["content"]),
    ("SmartWindowExplainerPage", ["upper_content", "content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
    ("RoadmapPage", ["intro", "content"]),
    ("ReferralHubPage", ["upper_content", "lower_content", "extra_content"]),
    ("ReferralGetFirefoxPage", ["upper_content", "lower_content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]

REVISION_FIELD_NAMES = sorted({name for _, field_names in PAGE_MODELS_AND_FIELDS for name in field_names})


def uses_browser_variant(block):
    return isinstance(block, dict) and block.get("type") == TABLE_TYPE and (block.get("value") or {}).get("variant") == BROWSER_VARIANT


def retype_as_browser_table(block):
    block["type"] = BROWSER_TABLE_TYPE
    block["value"].pop("variant", None)


def move_tab_table(tab_value):
    """Move a tab's browser-variant table into the field that accepts its new type.

    A tab's tables live in StreamBlocks that each accept one child type, so retyping a
    block without moving it leaves a child the StreamBlock rejects, and Wagtail drops
    unrecognised children silently when it loads the page.
    """
    tables = tab_value.get(TABLE_TYPE)
    if not isinstance(tables, list):
        return False

    stays = [block for block in tables if not uses_browser_variant(block)]
    moves = [block for block in tables if uses_browser_variant(block)]
    if not moves:
        return False

    for block in moves:
        retype_as_browser_table(block)
    tab_value[TABLE_TYPE] = stays
    tab_value.setdefault(BROWSER_TABLE_TYPE, []).extend(moves)
    return True


def convert_browser_comparison_tables(data):
    """Recursively convert every comparison_table block in a block tree, in place.

    Returns True when anything changed, so callers only write rows they touched.
    """
    if isinstance(data, dict):
        if data.get("type") == TABLE_TYPE:
            value = data.get("value") or {}
            if "variant" not in value:
                return False
            if value.pop("variant") == BROWSER_VARIANT:
                data["type"] = BROWSER_TABLE_TYPE
            return True

        # Runs before the walk below so the walk sees the moved blocks in their new
        # field, and so no key is added to the dict while it is being iterated.
        changed = move_tab_table(data)
        for value in data.values():
            if isinstance(value, (dict, list, MutableSequence)):
                changed = convert_browser_comparison_tables(value) or changed
        return changed

    if isinstance(data, (list, MutableSequence)):
        changed = False
        for item in data:
            if isinstance(item, (dict, list, MutableSequence)):
                changed = convert_browser_comparison_tables(item) or changed
        return changed

    return False


def iter_comparison_tables(data):
    """Yield every comparison_table block in a block tree."""
    if isinstance(data, dict):
        if data.get("type") == TABLE_TYPE:
            yield data
            return
        for value in data.values():
            yield from iter_comparison_tables(value)
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            yield from iter_comparison_tables(item)


def count_orphaned_optional_content(block):
    """Count the block's cells that still hold optional content.

    Only the browser comparison table renders optional content, so such a cell falls
    back to its plain text - nothing at all, when the author filled in only the
    optional content.
    """
    value = block.get("value") or {}
    rows = [*(value.get("header_row") or []), *(value.get("content_rows") or [])]
    return sum(1 for row in rows for cell in ((row.get("value") or {}).get("cells") or []) if (cell.get("value") or {}).get("optional_content"))


class Command(BaseCommand):
    help = "Convert comparison tables that used the browser-comparison variant into browser comparison tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made.\n"))

        self._convert_pages(dry_run)
        self._convert_revisions(dry_run)
        self._update_translation_sources(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _convert_pages(self, dry_run):
        self.stdout.write("Converting comparison tables in page StreamFields...\n")
        total = 0

        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.iterator():
                changed_fields = []
                orphaned = 0
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if not stream_value:
                        continue
                    if convert_browser_comparison_tables(stream_value.raw_data):
                        changed_fields.append(field_name)
                    # Counted after the conversion, so the tables that moved to the
                    # browser type - the ones that can still render it - are excluded.
                    orphaned += sum(count_orphaned_optional_content(table) for table in iter_comparison_tables(stream_value.raw_data))
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    total += 1
                    self.stdout.write(f"  {model_name} pk={page.pk}: updated {', '.join(changed_fields)}\n")
                if orphaned:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {model_name} pk={page.pk}: {orphaned} comparison table cell(s) hold optional content "
                            "that no longer renders. Rebuild the table as a browser comparison table to keep it.\n"
                        )
                    )

        self.stdout.write(f"  {total} pages updated.\n")

    def _convert_revisions(self, dry_run):
        self.stdout.write("Converting comparison tables in page revisions...\n")
        content_type_ids = [ContentType.objects.get_for_model(apps.get_model("cms", name)).pk for name in PAGE_MODEL_NAMES]
        total = 0

        for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
            modified = False
            for field_name in REVISION_FIELD_NAMES:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                if convert_browser_comparison_tables(field_data):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total += 1

        self.stdout.write(f"  {total} revisions updated.\n")

    def _update_translation_sources(self, dry_run):
        """Re-sync wagtail-localize TranslationSource snapshots so they hold the new block type.

        Only updates the source's serialized content — does NOT call
        create_or_update_translation(), which would re-materialize translated pages and
        can silently drop blocks whose segments don't match the updated schema. Translated
        live rows are converted directly above, so they keep rendering; the re-pathed
        segments re-sync through the normal Smartling workflow on next publish.
        """
        self.stdout.write("Updating TranslationSource records...\n")

        if dry_run:
            self.stdout.write("  Skipping TranslationSource sync in dry-run mode.\n")
            return

        content_type_ids = [ContentType.objects.get_for_model(apps.get_model("cms", name)).pk for name in PAGE_MODEL_NAMES]
        total = 0
        for source in TranslationSource.objects.filter(specific_content_type_id__in=content_type_ids):
            try:
                source.update_from_db()
                total += 1
            except Exception:
                logger.warning("Failed to update TranslationSource pk=%s (object_id=%s).", source.pk, source.object_id, exc_info=True)

        self.stdout.write(f"  {total} TranslationSources updated.\n")
