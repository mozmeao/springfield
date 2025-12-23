# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.models import PreviewableMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet


class PreFooterCTASnippet(PreviewableMixin, TranslatableMixin):
    label = models.CharField(max_length=255, default="Get Firefox")
    link = models.URLField(max_length=255, blank=True)
    analytics_id = models.UUIDField(default=uuid4)

    panels = [
        FieldPanel("label"),
        FieldPanel("link"),
        FieldPanel("analytics_id"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Pre Footer Call to Action"
        verbose_name_plural = "Pre Footer Call to Action"

    def __str__(self):
        return f"{self.label} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pre-footer-cta-snippet-preview.html"


register_snippet(PreFooterCTASnippet)
