# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command filling in the Enterprise Download block's editable
Resources content.

We assume that every stored entry is ``"value": null``.
"""

import json
import logging
from collections.abc import MutableSequence
from uuid import uuid4

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Revision
from wagtail_localize.models import TranslationSource

logger = logging.getLogger(__name__)

BLOCK_TYPE = "enterprise_download"

# Page models and StreamFields that can reach an enterprise_download block.
PAGE_MODELS_AND_FIELDS = [
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
    ("SmartWindowPage", ["content"]),
    ("SmartWindowExplainerPage", ["upper_content", "content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]

REVISION_FIELD_NAMES = sorted({name for _, field_names in PAGE_MODELS_AND_FIELDS for name in field_names})

HEADING = "<p>Resources</p>"

# Bare URLs for links.
RESOURCE_LINKS = [
    ("https://firefox-admin-docs.mozilla.org/", "Firefox Enterprise documentation"),
    ("https://github.com/mozilla/policy-templates/releases", "Policy templates"),
    ("https://support.mozilla.org/products/firefox-enterprise/whats-new-firefox-enterprise/", "Enterprise Release Notes"),
]

# The section was centred by the stylesheet before the setting to center the
# text existed.
CENTER_CONTENT = True


def build_rich_text():
    """Return the Resources list, with a fresh analytics uid on every link."""
    items = "".join(f'<li><a href="{href}" uid="{uuid4()}">{text}</a></li>' for href, text in RESOURCE_LINKS)
    return f"<ul>{items}</ul>"


def fill_enterprise_download_blocks(data):
    """
    Recursively fill every empty enterprise_download block in a block tree, in place.

    Returns True when anything changed, so callers only write rows they touched.
    """
    if isinstance(data, dict):
        if data.get("type") == BLOCK_TYPE:
            value = data.get("value")
            if isinstance(value, dict) and (value.get("heading") or value.get("rich_text")):
                return False
            data["value"] = {
                "center_content": CENTER_CONTENT,
                "heading": HEADING,
                "rich_text": build_rich_text(),
            }
            return True

        changed = False
        for child in data.values():
            if isinstance(child, (dict, list, MutableSequence)):
                changed = fill_enterprise_download_blocks(child) or changed
        return changed

    if isinstance(data, (list, MutableSequence)):
        changed = False
        for item in data:
            if isinstance(item, (dict, list, MutableSequence)):
                changed = fill_enterprise_download_blocks(item) or changed
        return changed

    return False


class Command(BaseCommand):
    help = "Fill in the Enterprise Download block's heading and text."

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

        translation_keys = self._fill_pages(dry_run)
        self._fill_revisions(dry_run)
        self._update_translation_sources(translation_keys, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _fill_pages(self, dry_run):
        """Fill the live page rows, returning the translation_keys of the pages changed."""
        self.stdout.write("Filling Enterprise Download blocks in page StreamFields...\n")
        total = 0
        translated = 0
        translation_keys = set()

        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.iterator():
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if not stream_value:
                        continue
                    if fill_enterprise_download_blocks(stream_value.raw_data):
                        changed_fields.append(field_name)
                if not changed_fields:
                    continue
                if not dry_run:
                    page.save(update_fields=changed_fields)
                total += 1
                translation_keys.add(page.translation_key)
                language_code = page.locale.language_code
                verb = "would update" if dry_run else "updated"
                self.stdout.write(f"  {model_name} pk={page.pk} [{language_code}]: {verb} {', '.join(changed_fields)}\n")
                if language_code != "en-US":
                    translated += 1

        self.stdout.write(f"  {total} pages {'would be updated' if dry_run else 'updated'}.\n")
        if translated:
            self.stdout.write(
                self.style.WARNING(
                    f"  {translated} of those are not en-US and were filled with English copy. "
                    "Translate them in the CMS, or let them re-sync through the usual translation workflow.\n"
                )
            )
        return translation_keys

    def _fill_revisions(self, dry_run):
        self.stdout.write("Filling Enterprise Download blocks in page revisions...\n")
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
                if fill_enterprise_download_blocks(field_data):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total += 1

        self.stdout.write(f"  {total} revisions {'would be updated' if dry_run else 'updated'}.\n")

    def _update_translation_sources(self, translation_keys, dry_run):
        """Re-sync the wagtail-localize snapshots of the pages this command changed."""
        self.stdout.write("Updating TranslationSource records...\n")

        if dry_run:
            self.stdout.write("  Skipping TranslationSource sync in dry-run mode.\n")
            return

        if not translation_keys:
            self.stdout.write("  0 TranslationSources updated.\n")
            return

        content_type_ids = [ContentType.objects.get_for_model(apps.get_model("cms", name)).pk for name in PAGE_MODEL_NAMES]
        total = 0
        sources = TranslationSource.objects.filter(
            specific_content_type_id__in=content_type_ids,
            object_id__in=translation_keys,
        )
        for source in sources:
            try:
                source.update_from_db()
                total += 1
            except Exception:
                logger.warning("Failed to update TranslationSource pk=%s (object_id=%s).", source.pk, source.object_id, exc_info=True)

        self.stdout.write(f"  {total} TranslationSources updated.\n")
