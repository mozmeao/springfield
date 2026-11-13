# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Idempotent management command to merge older spellings of an image tag into the spelling to
keep, and to delete tags that are no longer wanted.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from taggit.models import Tag, TaggedItem

from springfield.cms.images.tags import get_unique_slug, reindex_images
from springfield.cms.models.images import SpringfieldImage

# The spelling to keep, and the spellings to move onto it. Tag names are case-sensitive, so
# "fr" and "FR" are two tags.
MERGES = {
    "French": ("french", "fr", "FR"),
    "German": ("german", "de", "DE"),
    "pictogram": ("pictograms",),
    "Illustration": ("illustration",),
}

# Tags to take off every image and delete.
DELETIONS = ("human-reviewed", "ROW-Customise", "ROW-Private", "test")


class Command(BaseCommand):
    help = "Merge older spellings of an image tag into the spelling to keep, and delete tags that are no longer wanted."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.image_content_type = ContentType.objects.get_for_model(SpringfieldImage)

        merged = 0
        deleted = 0
        # Keyed by pk, because a tag merge and a tag deletion can touch the same image.
        touched_images = {}

        with transaction.atomic():
            for kept_name, old_names in MERGES.items():
                old_tags = [tag for tag in (self.find_tag(name) for name in old_names) if tag is not None]
                if not old_tags:
                    continue

                kept_tag = self.find_tag(kept_name)
                if kept_tag is None and not dry_run:
                    kept_tag = Tag.objects.create(name=kept_name)

                for old_tag in old_tags:
                    merged += 1
                    images = list(SpringfieldImage.objects.filter(tags=old_tag))
                    touched_images.update({image.pk: image for image in images})
                    self.stdout.write(f"Tag {old_tag.name!r} -> {kept_name!r}: {len(images)} images")
                    if dry_run:
                        continue

                    for image in images:
                        image.tags.add(kept_tag)
                    self.remove_tag(old_tag)

                if not dry_run:
                    self.reclaim_slug(kept_tag)

            for name in DELETIONS:
                tag = self.find_tag(name)
                if tag is None:
                    continue

                deleted += 1
                images = list(SpringfieldImage.objects.filter(tags=tag))
                touched_images.update({image.pk: image for image in images})
                self.stdout.write(f"Tag {name!r} deleted: {len(images)} images")
                if not dry_run:
                    self.remove_tag(tag)

            if touched_images and not dry_run:
                # Tag names are part of the image search index, and the writes above change
                # them without saving the images themselves.
                reindex_images(touched_images.values())

        self.stdout.write(f"{merged} {'tag' if merged == 1 else 'tags'} to merge" if dry_run else f"{merged} tags merged")
        self.stdout.write(f"{deleted} {'tag' if deleted == 1 else 'tags'} to delete" if dry_run else f"{deleted} tags deleted")
        self.stdout.write(f"{len(touched_images)} images affected")

    def find_tag(self, name):
        """The tag with exactly this name, or None."""
        return Tag.objects.filter(name=name).first()

    def remove_tag(self, tag):
        """Take a tag off every image, and delete it unless another kind of object still uses it."""
        TaggedItem.objects.filter(tag=tag, content_type=self.image_content_type).delete()
        if TaggedItem.objects.filter(tag=tag).exists():
            self.stdout.write(f"Tag {tag.name!r} kept, another kind of object still uses it")
        else:
            tag.delete()

    def reclaim_slug(self, tag):
        """Give a tag the slug its name would have had.

        A tag created while an older spelling held the slug was given a suffixed one, which
        the merge frees.
        """
        slug = get_unique_slug(tag)
        if tag.slug != slug:
            tag.slug = slug
            tag.save(update_fields=["slug"])
