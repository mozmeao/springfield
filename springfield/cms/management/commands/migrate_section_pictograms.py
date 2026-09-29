# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to add pictograms into section blocks' pictogram field.

Until now, pictograms came from a background-image keyed on the section's anchor ID,
so a section inherited one by being named 'sovereignty'. This uploads each SVG as an
image record and writes it onto the sections that were relying on that rule.

The same logic is applied to page revisions, so the CMS editor and the live page agree
on what a page holds. A section that already has a pictogram is left alone.
"""

import json
import logging
from collections.abc import MutableSequence
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Revision
from wagtail_localize.models import TranslationSource

from springfield.cms.models import SpringfieldImage

logger = logging.getLogger(__name__)

SECTION_TYPE = "section"

# Stands in for an image that --dry-run reports but does not create, so the walk still runs.
DRY_RUN_IMAGE_ID = -1

# Anchor ID is the SVG under media/img/firefox/enterprise/ that its CSS rule pointed at,
# and the title its image record gets. The title is the idempotency key: Django suffixes a
# colliding upload (sovereignty-pictogram_dXUK2KY.svg), so a filename lookup would miss an
# image this command had already created and make a duplicate on each run.
PICTOGRAMS_BY_ANCHOR = {
    "sovereignty": ("sovereignty-pictogram.svg", "Sovereignty pictogram"),
    "security": ("security-pictogram.svg", "Security pictogram"),
    "resilience": ("resilience-pictogram.svg", "Resilience pictogram"),
    "trust": ("shield-lock.svg", "Trust pictogram"),
}

# The page models and StreamFields that can reach a section block.
PAGE_MODELS_AND_FIELDS = [
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
    ("SmartWindowPage", ["content"]),
    ("SmartWindowExplainerPage", ["upper_content", "content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]

REVISION_FIELD_NAMES = sorted({name for _, field_names in PAGE_MODELS_AND_FIELDS for name in field_names})


def set_section_pictograms(data, image_ids_by_anchor):
    """
    Walk nested StreamField data, setting the pictogram on every anchored section.

    Returns True when anything changed. A section that already holds a pictogram keeps it.

    The sequence check accepts MutableSequence as well as list because a page's
    StreamValue.raw_data is a StreamValue.RawDataView, which subclasses MutableSequence
    and not list. Checking for list alone makes this function return False for every page
    while still working on revisions, whose data comes back from json.loads as a real list,
    so the command would report success and write nothing.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == SECTION_TYPE:
            value = data.get("value") or {}
            anchor = (value.get("settings") or {}).get("anchor_id", "")
            image_id = image_ids_by_anchor.get(anchor)
            if image_id and not value.get("pictogram"):
                value["pictogram"] = image_id
                data["value"] = value
                changed = True
        for child in data.values():
            changed |= set_section_pictograms(child, image_ids_by_anchor)
    elif isinstance(data, (list, MutableSequence)):
        for child in data:
            changed |= set_section_pictograms(child, image_ids_by_anchor)
    return changed


class Command(BaseCommand):
    help = "Create pictogram images in the Section pictogram field, based on previous CSS rules."

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

        image_ids_by_anchor = self._create_images(dry_run)
        translation_keys = self._update_pages(image_ids_by_anchor, dry_run)
        self._update_revisions(image_ids_by_anchor, dry_run)
        self._update_translation_sources(translation_keys, dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete. No changes were made.\n"))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration complete.\n"))

    def _create_images(self, dry_run):
        """
        Upload each pictogram SVG once, returning {anchor_id: image pk}.

        Under --dry-run, an image that does not exist yet is reported and stands in as
        DRY_RUN_IMAGE_ID, so the walk below still finds and counts the sections that
        would change.
        """
        self.stdout.write("Creating pictogram image records...\n")
        image_ids_by_anchor = {}
        for anchor, (filename, title) in PICTOGRAMS_BY_ANCHOR.items():
            image = SpringfieldImage.objects.filter(title=title).first()
            if image is not None:
                image_ids_by_anchor[anchor] = image.pk
                continue
            if dry_run:
                self.stdout.write(f"  would create {filename}\n")
                image_ids_by_anchor[anchor] = DRY_RUN_IMAGE_ID
                continue
            file_path = Path(settings.ROOT) / "media" / "img" / "firefox" / "enterprise" / filename
            with file_path.open("rb") as pictogram_file:
                image = SpringfieldImage.objects.create(
                    title=title,
                    is_decorative=True,
                    file=ContentFile(pictogram_file.read(), name=filename),
                )
            self.stdout.write(f"  created {filename} as pk={image.pk}\n")
            image_ids_by_anchor[anchor] = image.pk
        return image_ids_by_anchor

    def _update_pages(self, image_ids_by_anchor, dry_run):
        """
        Set the pictogram on every anchored section, returning the translation keys of
        the pages that changed.
        """
        self.stdout.write("Setting pictograms on anchored sections...\n")
        translation_keys = set()
        pages_changed = 0
        for model_name, field_names in PAGE_MODELS_AND_FIELDS:
            Model = apps.get_model("cms", model_name)
            for page in Model.objects.iterator():
                changed_fields = []
                for field_name in field_names:
                    stream_value = getattr(page, field_name)
                    if stream_value and set_section_pictograms(stream_value.raw_data, image_ids_by_anchor):
                        changed_fields.append(field_name)
                if changed_fields:
                    if not dry_run:
                        page.save(update_fields=changed_fields)
                    # Counted separately from translation_keys: a page and its translations
                    # share one key, so len(translation_keys) under-reports whenever a page
                    # and a translation of it both change. A production deploy is gated on
                    # this number matching the dry run's, which is the worst place for a
                    # count that can mean two things.
                    pages_changed += 1
                    translation_keys.add(page.translation_key)
                    verb = "would update" if dry_run else "updated"
                    self.stdout.write(f"  {model_name} pk={page.pk}: {verb} {', '.join(changed_fields)}\n")
        verb = "would be updated" if dry_run else "updated"
        self.stdout.write(f"  {pages_changed} pages {verb}.\n")
        return translation_keys

    def _update_revisions(self, image_ids_by_anchor, dry_run):
        self.stdout.write("Setting pictograms in page revisions...\n")
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
                if set_section_pictograms(field_data, image_ids_by_anchor):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            if modified:
                if not dry_run:
                    revision.save(update_fields=["content"])
                total += 1
        verb = "would be updated" if dry_run else "updated"
        self.stdout.write(f"  {total} revisions {verb}.\n")

    def _update_translation_sources(self, translation_keys, dry_run):
        """
        Re-sync wagtail-localize TranslationSource snapshots for the pages that changed.

        Scoped to those pages on purpose: re-snapshotting a source that this command did not
        touch can mark its translations out of date for no reason. TranslationSource.object_id
        holds the object's translation_key.
        """
        self.stdout.write("Updating TranslationSource records...\n")
        if not translation_keys:
            self.stdout.write("  No pages changed; nothing to re-sync.\n")
            return
        content_type_ids = [ContentType.objects.get_for_model(apps.get_model("cms", name)).pk for name in PAGE_MODEL_NAMES]
        sources = TranslationSource.objects.filter(specific_content_type_id__in=content_type_ids, object_id__in=translation_keys)
        if dry_run:
            self.stdout.write(f"  {sources.count()} TranslationSources would be re-synced.\n")
            return
        total = 0
        for source in sources:
            try:
                source.update_from_db()
                total += 1
            except Exception:
                logger.warning("Failed to update TranslationSource pk=%s (object_id=%s).", source.pk, source.object_id, exc_info=True)
        self.stdout.write(f"  {total} TranslationSources updated.\n")
