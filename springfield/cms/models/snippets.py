# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.models import PreviewableMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet


class BottomCTASnippet(PreviewableMixin, TranslatableMixin):
    label = models.CharField(max_length=255, default="Get Firefox")
    link = models.URLField(max_length=255, blank=True)

    panels = [
        FieldPanel("label"),
        FieldPanel("link"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Bottom Call to Action Snippet"
        verbose_name_plural = "Bottom Call to Action Snippets"

    def __str__(self):
        return f"{self.label} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/bottom-cta-snippet-preview.html"


register_snippet(BottomCTASnippet)
