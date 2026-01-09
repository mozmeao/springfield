# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.conf import settings
from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import PreviewableMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet
from wagtail.templatetags.wagtailcore_tags import richtext

from lib.l10n_utils import fluent_l10n, get_locale
from springfield.cms.blocks import EXPANDED_TEXT_FEATURES, HEADING_TEXT_FEATURES, ButtonBlock
from springfield.cms.fields import StreamField
from springfield.cms.templatetags.cms_tags import remove_tags


class FluentPreviewableMixin(PreviewableMixin):
    """
    A PreviewableMixin that renders templates with localized Fluent strings.
    """

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        locale = get_locale(request)
        context["fluent_l10n"] = fluent_l10n([locale, "en"], settings.FLUENT_DEFAULT_FILES)
        return context


class PreFooterCTASnippet(FluentPreviewableMixin, TranslatableMixin):
    """A snippet for the big Get Firefox button at the bottom of pages."""

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


class PreFooterCTAFormSnippet(FluentPreviewableMixin, TranslatableMixin):
    """A snippet for the Newsletter sign-up form at the bottom of pages."""

    heading = RichTextField(features=HEADING_TEXT_FEATURES)
    subheading = RichTextField(features=HEADING_TEXT_FEATURES)
    analytics_id = models.UUIDField(default=uuid4)

    panels = [
        FieldPanel("heading"),
        FieldPanel("subheading"),
        FieldPanel("analytics_id"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Pre Footer Call To Action Form"
        verbose_name_plural = "Pre Footer Call To Action Forms"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pre-footer-cta-form-snippet-preview.html"


register_snippet(PreFooterCTAFormSnippet)


class DownloadFirefoxCallToActionSnippet(TranslatableMixin):
    """A snippet to render an image with a Call to Action for downloading Firefox."""

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


class BannerSnippet(FluentPreviewableMixin, TranslatableMixin):
    """A snippet to render a banner with a QR code."""

    kit_theme = models.BooleanField(default=False, help_text="Use the Kit theme for this banner.")
    heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
    )
    content = RichTextField(
        features=EXPANDED_TEXT_FEATURES,
    )
    buttons = StreamField(
        [
            ("button", ButtonBlock()),
        ],
        blank=True,
        use_json_field=True,
        max_num=2,
    )
    qr_code = models.CharField(blank=True)

    panels = [
        FieldPanel("kit_theme"),
        FieldPanel("heading"),
        FieldPanel("content"),
        FieldPanel("buttons"),
        FieldPanel("qr_code"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Banner Snippet"
        verbose_name_plural = "Banner Snippets"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/banner-snippet-preview.html"


register_snippet(BannerSnippet)
