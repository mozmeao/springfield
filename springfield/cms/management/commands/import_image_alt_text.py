# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to apply reviewed image titles, descriptions, tags and
decorative flags from a CSV.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.search.backends import get_search_backend

from springfield.cms.models.images import SpringfieldImage

DEFAULT_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "image-alt-text.csv"


def pending_changes(image, row):
    """The fields of `image` that `row` would change, as {field name: new value}.

    Only the fields a row names in its `changed_fields` column are considered, so a value an
    editor has changed since the CSV was written is kept wherever the row leaves that column
    alone. Tags come back as a set of names, under their own key, because they are written
    separately from the image row.
    """
    declared = row["changed_fields"].split()
    new_values = {
        "title": row["title"],
        "description": row["description"],
        "is_decorative": row["is_decorative"].strip().lower() == "true",
    }
    changes = {field: value for field, value in new_values.items() if field in declared and getattr(image, field) != value}

    if "tags" in declared:
        new_tags = {tag.strip() for tag in row["tags"].split(",") if tag.strip()}
        if {tag.name for tag in image.tags.all()} != new_tags:
            changes["tags"] = new_tags

    return changes


class Command(BaseCommand):
    help = "Apply image titles, descriptions, tags and decorative flags from a CSV of reviewed values."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(DEFAULT_CSV_PATH),
            help="Path to the CSV to read.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with open(options["csv"], encoding="utf-8", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))

        images = SpringfieldImage.objects.filter(pk__in={int(row["image_id"]) for row in rows}).prefetch_related("tags").in_bulk()

        missing = 0
        mismatched = 0
        already_correct = 0
        changed_ids = []

        with transaction.atomic():
            for row in rows:
                image = images.get(int(row["image_id"]))
                if image is None:
                    missing += 1
                    self.stdout.write(f"Image {row['image_id']}: no such image, skipped")
                    continue

                # The ids come from one snapshot of one database. Checking the file as well means
                # a row that has landed on a different image is reported rather than applied.
                if image.file.name != row["file"]:
                    mismatched += 1
                    self.stdout.write(f"Image {image.pk}: file is {image.file.name}, the CSV expects {row['file']}, skipped")
                    continue

                changes = pending_changes(image, row)
                if not changes:
                    already_correct += 1
                    continue

                changed_ids.append(image.pk)
                self.report_changes(image, changes)
                if dry_run:
                    continue

                new_tags = changes.pop("tags", None)
                if changes:
                    # update() rather than save(), which ignores update_fields and always
                    # pre-generates the image's renditions. No field here changes a rendition,
                    # and generating one needs the original file and a task queue.
                    SpringfieldImage.objects.filter(pk=image.pk).update(**changes)
                if new_tags is not None:
                    image.tags.set(new_tags)

            if changed_ids and not dry_run:
                # Title, description and tags are all indexed, and update() writes the row without
                # the signal that would otherwise keep the index in step.
                get_search_backend().add_bulk(SpringfieldImage, SpringfieldImage.objects.filter(pk__in=changed_ids))

        counted = "image" if len(changed_ids) == 1 else "images"
        self.stdout.write(f"{len(changed_ids)} {counted} to change" if dry_run else f"{len(changed_ids)} {counted} changed")
        self.stdout.write(f"{already_correct} already correct")
        self.stdout.write(f"{missing} skipped, no such image")
        self.stdout.write(f"{mismatched} skipped, file does not match")

    def report_changes(self, image, changes):
        """Print each field this run replaces, old value then new, as the record of the run."""
        for field, value in changes.items():
            if field == "tags":
                old_value, new_value = sorted(tag.name for tag in image.tags.all()), sorted(value)
            else:
                old_value, new_value = getattr(image, field), value
            self.stdout.write(f"Image {image.pk} {field}: {old_value!r} -> {new_value!r}")
