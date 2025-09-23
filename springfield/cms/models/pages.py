# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models
from django.shortcuts import redirect

from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page as WagtailBasePage

from springfield.cms.blocks import FeaturesBlock, HighlightsBlock, IntroBlock, QRCodeBannerBlock, SubscribeBannerBlock, TagCardsBlock

from .base import AbstractSpringfieldCMSPage


class StructuralPage(AbstractSpringfieldCMSPage):
    """A page used to create a folder-like structure within a page tree,
    under/in which other pages live.
    Not directly viewable - will redirect to its parent page if called"""

    # There are minimal fields on this model - only exactly what we need
    # `title` and `slug` fields come from Page->AbstractSpringfieldCMSPage
    is_structural_page = True
    # TO COME: guard rails on page hierarchy
    # subpage_types = []
    settings_panels = WagtailBasePage.settings_panels + [
        FieldPanel("show_in_menus"),
    ]
    content_panels = [
        FieldPanel("title"),
        FieldPanel("slug"),
    ]
    promote_panels = []

    def serve_preview(self, request, mode_name="irrelevant"):
        # Regardless of mode_name, always redirect to the parent page
        return redirect(self.get_parent().get_full_url())

    def serve(self, request):
        return redirect(self.get_parent().get_full_url())


class SimpleRichTextPage(AbstractSpringfieldCMSPage):
    """Simple page that renders a rich-text field, using our broadest set of
    allowed rich-text features.

    Not intended to be commonly used, this is more a very simple reference
    implementation.

    Note that this page is actively used in tests, so removing this will
    require relevant tests to be refactored, too
    """

    # 1. Define model fields
    # `title` and `slug` fields come from Page->AbstractSpringfieldCMSPage
    content = RichTextField(
        blank=True,
        features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL,
    )
    # Note there are no other custom fields here

    # 2. Define editing UI by extending the default field list
    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
    ]

    # 3. Specify HTML Template:
    # If not set, Wagtail will automatically choose a name for the template
    # in the format `<app_label>/<model_name_in_snake_case>.html`
    template = "cms/simple_rich_text_page.html"


class ArticleIndexPageBase(AbstractSpringfieldCMSPage):
    sub_title = models.CharField(
        max_length=255,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("sub_title"),
    ]

    class Meta:
        abstract = True


class ArticleDetailPageBase(AbstractSpringfieldCMSPage):
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    desc = models.CharField(
        max_length=500,
        blank=True,
        help_text="A short description used on index page.",
    )

    content = RichTextField(
        blank=True,
        features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("image"),
        FieldPanel("desc"),
        FieldPanel("content"),
    ]

    class Meta:
        abstract = True


class WhatsNewPage(AbstractSpringfieldCMSPage):
    """A page that displays the latest Firefox updates and changes."""

    content = StreamField(
        [
            ("paragraph", blocks.RichTextBlock()),
            ("intro", IntroBlock()),
            ("features", FeaturesBlock()),
            ("highlights", HighlightsBlock()),
            ("subscribe_banner", SubscribeBannerBlock()),
            ("tag_cards", TagCardsBlock()),
            ("qr_code_banner", QRCodeBannerBlock()),
        ]
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
    ]
