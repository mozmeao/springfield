# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from wagtail.admin.panels import FieldPanel
from wagtail.contrib.redirects.models import Redirect

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

    def save(self, *args, **kwargs):
        stored_path = type(self).objects.filter(pk=self.pk).values_list("path", flat=True).first()

        with transaction.atomic():
            super().save(*args, **kwargs)

            # If the path has changed, then create a redirect from the old path
            # to the new path.
            if stored_path is not None and stored_path != self.path:
                self._create_a_redirect_from(stored_path)

            if not self.document.file_hash:
                # Filled here because the serving view reads the stored hash
                # rather than computing one.
                self.document.get_file_hash()

    @property
    def url(self) -> str:
        return _stable_url_for_path(self.path)

    def _create_a_redirect_from(self, stored_path: str) -> None:
        """Point the stable URL built from ``stored_path`` at this record's current URL."""
        old_url = _stable_url_for_path(stored_path)

        # Looked up rather than left to a uniqueness error, because there is no
        # error to catch: Redirect.old_path is unique only together with site,
        # add_redirect leaves site NULL, and SQL counts NULLs as distinct. A
        # second row at the same old_path would insert cleanly and then make the
        # old URL answer 500 instead of redirecting, because RedirectMiddleware
        # recovers from MultipleObjectsReturned by looking the path up again
        # scoped to a real site, which finds nothing.
        existing_redirect = Redirect.objects.filter(old_path=Redirect.normalise_path(old_url), site=None).first()
        if existing_redirect is None:
            Redirect.add_redirect(old_path=old_url, redirect_to=self.url, is_permanent=False, automatically_created=True)
            return

        existing_redirect.redirect_link = self.url
        # Explicitly set redirect_page to None, so it does not conflict with
        # redirect_link.
        existing_redirect.redirect_page = None
        existing_redirect.save()

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


def _stable_url_for_path(path: str) -> str:
    return f"/{STABLE_DOCUMENT_URL_PREFIX}/{path}"


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
