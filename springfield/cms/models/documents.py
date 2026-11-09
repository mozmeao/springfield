# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from wagtail.admin.panels import FieldPanel

__all__ = [
    "PDF_MAGIC",
    "STABLE_DOCUMENT_URL_PREFIX",
    "StableDocumentURL",
    "stable_url_for_document",
    "stable_url_paths_by_document_id",
]

STABLE_DOCUMENT_URL_PREFIX = "documents"

_CACHE_KEY = "stable-document-urls"
_CACHE_SECONDS = 60

# Every PDF starts with this. Checked because the extension alone proves
# nothing: Wagtail derives a document's content type from its filename, so a
# file of HTML named .pdf would be served to the public as a PDF.
PDF_MAGIC = b"%PDF-"


class StableDocumentURL(models.Model):
    """Holds a stable public path for one Wagtail document."""

    # The public URL for the document is built from this path.
    path = models.SlugField(max_length=64, unique=True)
    # The human name for this URL, shown wherever the admin lists records.
    label = models.CharField(max_length=255)
    # Required, because the row itself records the assignment: unassigning a
    # path deletes the row rather than clearing this field.
    document = models.OneToOneField(
        "wagtaildocs.Document",
        on_delete=models.PROTECT,
        related_name="stable_url",
    )

    panels = [
        FieldPanel("path"),
        FieldPanel("label"),
        FieldPanel("document"),
    ]

    class Meta:
        verbose_name = "stable URL"
        verbose_name_plural = "stable URLs"
        ordering = ["path"]

    def __str__(self):
        return self.label

    @property
    def url(self) -> str:
        return f"/{STABLE_DOCUMENT_URL_PREFIX}/{self.path}"

    def clean(self):
        super().clean()
        # Make sure that the path is lowercased, so there is not confusion about
        # different casings of the same URL.
        self.path = self.path.lower()

        # Django calls clean() even when a required field has already failed,
        # so return None here.
        if self.document_id is None:
            return

        if not self.document.filename.lower().endswith(".pdf"):
            raise ValidationError({"document": "Only a PDF can be given a stable URL."})

        with self.document.file.open("rb") as document_file:
            if document_file.read(len(PDF_MAGIC)) != PDF_MAGIC:
                raise ValidationError({"document": "This file is named .pdf but is not a PDF."})

        if self.document.collection.get_view_restrictions().exists():
            raise ValidationError({"document": "A document in a collection with a privacy restriction cannot be given a stable URL."})


def stable_url_paths_by_document_id() -> dict[int, str]:
    """Map every assigned document's id to its stable URL, cached briefly."""
    paths_by_id = cache.get(_CACHE_KEY)
    if paths_by_id is None:
        paths_by_id = {row.document_id: row.url for row in StableDocumentURL.objects.all()}
        cache.set(_CACHE_KEY, paths_by_id, _CACHE_SECONDS)
    return paths_by_id


def stable_url_for_document(document) -> str | None:
    return stable_url_paths_by_document_id().get(document.pk)


@receiver([post_save, post_delete], sender=StableDocumentURL)
def _clear_stable_url_cache(sender, **kwargs):
    cache.delete(_CACHE_KEY)
