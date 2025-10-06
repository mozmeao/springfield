# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django.urls import reverse

from wagtail.models import Page


class PageTranslationData(models.Model):
    """Stores pre-calculated translation data for pages."""

    source_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="translation_data",
        db_index=True,
    )
    translated_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="source_translation_data",
    )
    percent_translated = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["source_page", "translated_page"]]
        indexes = [
            models.Index(fields=["source_page"]),
        ]

    def __str__(self):
        return f"{self.source_page} -> {self.translated_page} ({self.percent_translated}%)"

    @property
    def get_edit_url(self):
        """Generate edit URL for the translated page."""
        return reverse("wagtailadmin_pages:edit", args=[self.translated_page.id])

    @property
    def get_view_url(self):
        """Get view URL for the translated page."""
        if hasattr(self.translated_page, "get_url"):
            return self.translated_page.get_url()
        return ""

    def to_dict(self):
        """Return dictionary with translation data."""
        return {
            "locale": self.translated_page.locale.language_code,
            "edit_url": self.get_edit_url,
            "view_url": self.get_view_url,
            "percent_translated": self.percent_translated,
        }
