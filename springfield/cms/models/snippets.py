# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import PreviewableMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet

from springfield.cms.blocks import HEADING_TEXT_FEATURES
from springfield.cms.templatetags.cms_tags import remove_tags


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


class DownloadFirefoxCallToActionSnippet(TranslatableMixin):
    heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
    )
    description = RichTextField(
        features=HEADING_TEXT_FEATURES,
    )
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        FieldPanel("heading"),
        FieldPanel("description"),
        FieldPanel("image"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Download Firefox Call To Action Snippet"
        verbose_name_plural = "Download Firefox Call To Action Snippets"

    def __str__(self):
        return f"{remove_tags(self.heading)} – {self.locale}"


register_snippet(DownloadFirefoxCallToActionSnippet)
