# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count
from django.db.models.expressions import F
from django.forms.widgets import CheckboxSelectMultiple
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

import requests
from modelcluster.fields import ParentalKey
from sentry_sdk import capture_message, new_scope
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, TitleFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.models import Orderable, Page as WagtailBasePage
from wagtail.rich_text import RichText
from wagtail.search import index
from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail_localize.fields import SynchronizedField
from wagtail_thumbnail_choice_block import ThumbnailRadioSelect

from lib import l10n_utils
from lib.l10n_utils.fluent import ftl, ftl_lazy
from springfield.base.geo import get_country_from_request
from springfield.cms.blocks import (
    HEADING_TEXT_FEATURES,
    ICON_CHOICES,
    UI_TOUR_CLASSES,
    UITOUR_BUTTON_SMART_WINDOW,
    BannerBlock,
    BlogArticleBlock,
    BlogCardsListBlock,
    ButtonRowBlock,
    CardGalleryBlock,
    CardsListBlock,
    CarouselBlock,
    CheckboxFieldBlock,
    CheckboxGroupFieldBlock,
    CodeBlock,
    CountrySelectFieldBlock,
    DownloadSupportBlock,
    EmailFieldBlock,
    EnterpriseDownloadBlock,
    FeaturedImageSectionBlock,
    HeadingBlock,
    HiddenFieldBlock,
    HomeKitBannerBlock,
    IntroBlock,
    KitBannerBlock,
    KitIntroBlock,
    LineCardsBlock,
    LocalizedLiveSnippetChooserBlock,
    MediaBlock,
    MediaContentBlock,
    MobileStoreQRCodeBlock,
    NotificationBlock,
    PhoneFieldBlock,
    QuoteBlock,
    RelatedArticlesListBlock,
    RoadmapListSectionBlock,
    SectionBlock,
    SelectFieldBlock,
    ShowcaseBlock,
    SlidingCarouselBlock,
    TextAreaFieldBlock,
    TextFieldBlock,
    TopicListBlock,
    VideoBlock,
    validate_animation_url,
)
from springfield.cms.fields import StreamField
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.rich_text import RichTextBlock, RichTextField

from .base import AbstractSpringfieldCMSPage, PromotedPageMixin

if TYPE_CHECKING:
    from springfield.cms.models import Tag


BASE_UTM_PARAMETERS = {
    "utm_source": "www.firefox.com",
    "utm_medium": "referral",
}


FIREFOX_THEME = ""
ENTERPRISE_THEME = "enterprise"
THEME_CHOICES = (
    (FIREFOX_THEME, "Firefox"),
    (ENTERPRISE_THEME, "Enterprise"),
)


class StructuralPage(AbstractSpringfieldCMSPage):
    """A page used to create a folder-like structure within a page tree,
    under/in which other pages live.
    Not directly viewable - will redirect to its parent page if called"""

    # There are minimal fields on this model - only exactly what we need
    # `title` and `slug` fields come from Page->AbstractSpringfieldCMSPage
    is_structural_page = True
    # TO COME: guard rails on page hierarchy
    # subpage_types = []
    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
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

    def get_utm_parameters(self):
        return {
            **BASE_UTM_PARAMETERS,
            "utm_campaign": self.slug,
        }

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["utm_parameters"] = self.get_utm_parameters()
        return context


class UTMParamsMixin(models.Model):
    STUB_ATTRIBUTION_MODES = (
        ("", "None"),
        ("default", "Default (used if no utm_campaign in URL)"),
        ("override", "Override (replaces utm_campaign from URL, respects cookie)"),
        ("force", "Force (replaces everything, clears attribution cookie)"),
    )

    stub_attr_utm_campaign_mode = models.CharField(
        max_length=20,
        blank=True,
        choices=STUB_ATTRIBUTION_MODES,
        verbose_name="Stub Attribution Mode",
        help_text="Controls how the campaign value is applied to download attribution.",
    )
    stub_attr_utm_campaign_value = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Stub Attribution Campaign Value",
        help_text="The campaign value to use for stub attribution. Only used if a mode is selected above.",
    )

    promote_panels = AbstractSpringfieldCMSPage.promote_panels + [
        MultiFieldPanel(
            [
                FieldPanel("stub_attr_utm_campaign_mode"),
                FieldPanel("stub_attr_utm_campaign_value"),
            ],
            heading="Stub Attribution UTM Parameters",
        ),
    ]

    class Meta:
        abstract = True

    def get_stub_attribution_utm_campaign(self):
        if self.stub_attr_utm_campaign_mode and self.stub_attr_utm_campaign_value:
            return self.stub_attr_utm_campaign_value
        return ""

    def get_utm_campaign(self):
        return self.get_stub_attribution_utm_campaign() or self.slug

    def get_utm_parameters(self):
        return {
            **BASE_UTM_PARAMETERS,
            "utm_campaign": self.get_utm_campaign(),
        }

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["utm_parameters"] = self.get_utm_parameters()
        return context


PRE_FOOTER_IMAGE_KIT = "kit"
PRE_FOOTER_IMAGE_GLOBE = "globe"
PRE_FOOTER_IMAGE_NONE = "none"
PRE_FOOTER_IMAGE_CHOICES = [
    (PRE_FOOTER_IMAGE_KIT, "Show Kit on Newsletter form"),
    (PRE_FOOTER_IMAGE_GLOBE, "Show globe pictogram on Newsletter form"),
    (PRE_FOOTER_IMAGE_NONE, "Hide Newsletter form image"),
]


class PreFooterImageMixin(models.Model):
    """Per-page choice of the pre-footer newsletter form illustration."""

    pre_footer_image = models.CharField(
        max_length=20,
        choices=PRE_FOOTER_IMAGE_CHOICES,
        default=PRE_FOOTER_IMAGE_KIT,
        verbose_name="Pre-footer options",
        help_text="Image shown alongside the pre-footer newsletter form.",
    )

    pre_footer_image_panels = [
        FieldPanel("pre_footer_image"),
    ]

    class Meta:
        abstract = True


class QRCodeFloatingSnippetMixin(AbstractSpringfieldCMSPage):
    """Mixin that adds per-page overrides for the floating QR code snippet."""

    show_qr_code_snippet = models.BooleanField(
        default=False,
        help_text="If true, a floating QR code snippet will be displayed on the page.",
    )
    show_floating_qr_code_snippet = models.BooleanField(
        default=False,
        verbose_name="Show Floating QR Code Snippet",
        help_text="If true, an updated floating QR code snippet will be displayed on the page.",
    )
    floating_qr_url = models.CharField(
        blank=True,
        verbose_name="Override Floating QR Code URL",
        help_text="Override the snippet URL. A QR code will be generated from this. Not used if an override image is set.",
    )
    floating_qr_image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Override Floating QR Code Image",
        help_text="Override with an uploaded QR code image. Takes priority over the URL.",
    )
    floating_qr_default_open = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Override Floating QR Code Default Open",
        help_text="Override the default open state of the Floating QR code snippet.",
    )

    floating_qr_panels = [
        FieldPanel("show_qr_code_snippet"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("show_floating_qr_code_snippet"),
                        FieldPanel("floating_qr_url"),
                        FieldPanel("floating_qr_image"),
                        FieldPanel("floating_qr_default_open"),
                    ]
                ),
            ],
            heading="QR Code Floating Button",
            classname="collapsed",
        ),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
        SynchronizedField("floating_qr_url"),
        SynchronizedField("floating_qr_image"),
        SynchronizedField("floating_qr_default_open"),
    ]

    class Meta:
        abstract = True

    def get_context(self, request, *args, **kwargs):
        from springfield.cms.models.snippets import QRCodeFloatingSnippet

        context = super().get_context(request, *args, **kwargs)
        if self.show_floating_qr_code_snippet:
            snippet = QRCodeFloatingSnippet.get_live(self.locale)
            if snippet:
                context["floating_qr_snippet"] = snippet.build_context(page=self, request=request)
        return context

    def clean(self):
        super().clean()
        if self.floating_qr_url and self.floating_qr_image:
            raise ValidationError("Only one of 'Floating QR Code URL Override' and 'Floating QR Code Image Override' is allowed.")
        if self.show_qr_code_snippet and self.show_floating_qr_code_snippet:
            raise ValidationError("Only one of the Floating QR Code snippets can be enabled.")
        if not self.show_floating_qr_code_snippet and any([self.floating_qr_url, self.floating_qr_image, self.floating_qr_default_open]):
            raise ValidationError("'QR Code Floating Button' fields can only be set if the 'Show Floating QR Code Snippet' is enabled.")


class HomePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    upper_content = StreamField(
        [
            ("intro", KitIntroBlock()),
            ("cards_list", CardsListBlock(template="cms/blocks/sections/cards-list-section.html")),
            ("carousel", CarouselBlock()),
        ],
        use_json_field=True,
    )
    lower_content = StreamField(
        [
            ("showcase", ShowcaseBlock()),
            ("card_gallery", CardGalleryBlock()),
            ("kit_banner", HomeKitBannerBlock()),
        ],
        null=True,
        blank=True,
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("lower_content"),
        InlinePanel("pencil_banner_placements", label="Pencil Banners"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("upper_content"),
        index.SearchField("lower_content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    def __str__(self):
        return f"HomePage: {self.title} - {self.locale}"

    @property
    def pencil_banners(self):
        placements = self.pencil_banner_placements.select_related("snippet").order_by("sort_order")
        snippets = [placement.snippet.get_localized() for placement in placements]
        # get_localized() can return None if the snippet isn't translated and published
        return [snippet for snippet in snippets if snippet]


class DownloadIndexPage(AbstractSpringfieldCMSPage):
    subpage_types = ["cms.DownloadPage"]

    def serve(self, request):
        return redirect(reverse("firefox.all"))

    def serve_preview(self, request, *args, **kwargs):
        return redirect(reverse("firefox.all"))


class DownloadPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    parent_page_types = ["cms.DownloadIndexPage"]

    ftl_files = [
        "firefox/download/download",
        "firefox/browsers/mobile/android",
        "firefox/browsers/mobile/ios",
        "firefox/browsers/desktop/chromebook",
    ]

    PLATFORM_CHOICES = (
        ("windows", ftl("firefox-new-platform-windows", ftl_files=["firefox/download/download"])),
        ("mac", ftl("firefox-new-platform-macos", ftl_files=["firefox/download/download"])),
        ("linux", ftl("firefox-new-platform-linux", ftl_files=["firefox/download/download"])),
        ("android", ftl("firefox-new-platform-android", ftl_files=["firefox/download/download"])),
        ("ios", ftl("firefox-new-platform-ios", ftl_files=["firefox/download/download"])),
        ("chromebook", ftl("firefox-new-platform-chromebook", ftl_files=["firefox/download/download"])),
    )

    platform = models.CharField(
        default="windows",
        max_length=50,
        choices=PLATFORM_CHOICES,
        help_text="The platform this download page is for (e.g., Windows, macOS, Linux).",
    )
    subheading = RichTextField(default="Subheading", features=HEADING_TEXT_FEATURES)
    intro_footer_text = RichTextField(null=True, blank=True, features=HEADING_TEXT_FEATURES)
    featured_image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="download_page_featured_images",
    )
    featured_image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode variant of the featured image.",
    )
    featured_image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional mobile variant of the featured image.",
    )
    featured_image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode mobile variant of the featured image.",
    )
    content = StreamField(
        [
            ("section", SectionBlock()),
            (
                "banner_snippet",
                LocalizedLiveSnippetChooserBlock(
                    target_model="cms.BannerSnippet",
                    template="cms/snippets/banner-snippet.html",
                    label="Banner Snippet",
                ),
            ),
        ],
        use_json_field=True,
        null=True,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("platform"),
        FieldPanel("subheading"),
        FieldPanel("intro_footer_text"),
        FieldPanel("featured_image"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("featured_image_dark_mode"),
                        FieldPanel("featured_image_mobile"),
                        FieldPanel("featured_image_dark_mode_mobile"),
                    ]
                ),
            ],
            heading="Featured Image Variants",
            classname="collapsed",
        ),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("subheading"),
        index.SearchField("intro_footer_text"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Download Page"
        verbose_name_plural = "Download Pages"

    def __str__(self):
        return f"DownloadPage: {self.title} - {self.locale}"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["platforms"] = dict(self.PLATFORM_CHOICES)
        platform_links = {
            "windows": "/browsers/desktop/windows",
            "mac": "/browsers/desktop/mac",
            "linux": "/browsers/desktop/linux",
            "android": "/browsers/mobile/android",
            "ios": "/browsers/mobile/ios",
            "chromebook": "/browsers/desktop/chromebook",
        }
        parent = self.get_parent().specific
        children = parent.get_children().filter(downloadpage__isnull=False).live().public().specific()
        for page in children:
            platform_links[page.platform] = page.get_url()
        context["platform_links"] = platform_links
        return context


class ThanksPage(UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
    """A thank you page displayed after the user downloads Firefox."""

    ftl_files = ["firefox/download/desktop"]

    content = StreamField(
        [
            ("section", SectionBlock(allow_uitour=False)),
            ("download_support", DownloadSupportBlock()),
            (
                "banner_snippet",
                LocalizedLiveSnippetChooserBlock(
                    target_model="cms.BannerSnippet",
                    template="cms/snippets/banner-snippet.html",
                    label="Banner Snippet",
                ),
            ),
        ],
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
        *QRCodeFloatingSnippetMixin.floating_qr_panels,
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
    ]

    def __str__(self):
        return f"ThanksPage: {self.title} - {self.locale}"

    def clean(self):
        super().clean()
        content_block_types = [block.block_type for block in self.content]
        if "download_support" not in content_block_types:
            raise ValidationError("The 'Download Support Message' block is required.")
        first_block = self.content[0]
        if first_block.block_type != "section":
            raise ValidationError("The first block must be a 'Section' block.")
        if first_block.value["settings"].get("show_to", {}).get("platforms"):
            section_blocks = [block for block in self.content if block.block_type == "section"]
            covered_platforms = set()
            for block in section_blocks:
                if platforms := block.value["settings"].get("show_to", {}).get("platforms"):
                    covered_platforms.update(platforms)
            if not {"windows", "osx", "linux", "android", "ios", "unsupported", "other-os"}.issubset(covered_platforms):
                raise ValidationError(
                    "When using conditional display in sections, all platform conditions "
                    "('Windows', 'macOS', 'Linux', 'Android', 'iOS', 'Other OS Users', and 'Unsupported OS Users') must be included."
                )

    def get_utm_campaign(self):
        return self.get_stub_attribution_utm_campaign() or "firefox-download-thanks"

    def get_template(self, request, *args, **kwargs):
        if request.GET.get("s") == "direct":
            return "firefox/download/rtamo.html"

        return "cms/thanks_page.html"

    @property
    def noindex(self):
        return True


class ArticleIndexPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    subpage_types = ["cms.ArticleDetailPage", "cms.ArticleThemePage"]

    sub_title = models.CharField(
        max_length=255,
        blank=True,
    )
    other_articles_heading = RichTextField(features=HEADING_TEXT_FEATURES)
    other_articles_subheading = RichTextField(features=HEADING_TEXT_FEATURES, blank=True)
    show_sibling_detail_pages = models.BooleanField(
        default=False,
        help_text=(
            "If checked, ArticleDetailPage siblings of this index page are included "
            "in the article listing alongside its children. Enable for index pages "
            "whose detail pages are siblings. Disable for index pages whose detail "
            "pages are children."
        ),
    )

    INDEX_CARD_STICKER = "sticker_card"
    INDEX_CARD_OUTLINE = "outline_card"
    INDEX_CARD_ILLUSTRATION = "illustration_card"

    INDEX_CARD_TYPE_CHOICES = (
        (INDEX_CARD_STICKER, "Sticker card"),
        (INDEX_CARD_OUTLINE, "Outline card"),
        (INDEX_CARD_ILLUSTRATION, "Illustration card"),
    )

    index_card_type = models.CharField(
        max_length=20,
        choices=INDEX_CARD_TYPE_CHOICES,
        default=INDEX_CARD_STICKER,
        help_text="Controls the card style used in the article listing.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("sub_title"),
        FieldPanel("other_articles_heading"),
        FieldPanel("other_articles_subheading"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
        FieldPanel("show_sibling_detail_pages"),
        FieldPanel("index_card_type"),
    ]

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("sub_title"),
        index.SearchField("other_articles_subheading"),
        index.SearchField("other_articles_heading"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    def __str__(self):
        return f"ArticleIndexPage: {self.title} - {self.locale}"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        child_ids = self.get_children().live().public().values_list("pk", flat=True)

        # Sometimes, when an ArticleIndexPage exists at the same hierarchical level as
        # ArticleDetailPage, we want to include those ArticleDetailPages on the
        # ArticleIndexPage; other times we do not. Make the determination based
        # on the show_sibling_detail_pages field.
        if self.show_sibling_detail_pages:
            sibling_ids = self.get_siblings(inclusive=False).live().public().values_list("pk", flat=True)
        else:
            sibling_ids = []

        all_articles = ArticleDetailPage.objects.filter(pk__in=[*child_ids, *sibling_ids]).order_by("-first_published_at")

        featured_articles = [page for page in all_articles if page.featured]
        list_articles = [page for page in all_articles if not page.featured]

        context["featured_articles"] = featured_articles
        context["list_articles"] = list_articles
        return context


class ArticleDetailPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    parent_page_types = ["cms.ArticleThemePage", "cms.ArticleIndexPage"]

    featured = models.BooleanField(
        default=False,
        help_text="Check to set as a featured article on the index page.",
    )
    featured_image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="A portrait-oriented image used in featured article cards.",
    )
    featured_image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode variant of the featured image.",
    )
    featured_image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional mobile variant of the featured image.",
    )
    featured_image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode mobile variant of the featured image.",
    )
    tag = models.ForeignKey(
        "cms.Tag",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
    )
    link_text = models.CharField(
        default="Read more",
        help_text="Custom text for the 'Read more' link on article cards.",
    )
    sticker = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="A sticker image used in article cards.",
    )
    sticker_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode variant of the sticker.",
    )
    sticker_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional mobile variant of the sticker.",
    )
    sticker_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode mobile variant of the sticker.",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        choices=ICON_CHOICES,
        help_text="Optional icon to display on icon article cards.",
    )
    index_page_heading = models.CharField(
        blank=True,
        help_text="Custom heading to be used on the index page card.",
    )
    description = RichTextField(
        blank=True,
        features=HEADING_TEXT_FEATURES,
        help_text="A short description used on the index page.",
    )

    image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode variant of the article image.",
    )
    image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional mobile variant of the article image.",
    )
    image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode mobile variant of the article image.",
    )
    content = StreamField(
        [
            ("text", RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL)),
            ("video", VideoBlock()),
            ("button_row", ButtonRowBlock()),
        ],
        use_json_field=True,
    )
    related_articles = StreamField(
        [
            ("related_articles_list", RelatedArticlesListBlock()),
        ],
        use_json_field=True,
        null=True,
        blank=True,
        max_num=1,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("featured"),
                FieldPanel("tag"),
                FieldPanel("featured_image"),
                MultiFieldPanel(
                    [
                        FieldRowPanel(
                            [
                                FieldPanel("featured_image_dark_mode"),
                                FieldPanel("featured_image_mobile"),
                                FieldPanel("featured_image_dark_mode_mobile"),
                            ]
                        )
                    ],
                    heading="Featured Image Variants",
                    classname="collapsed",
                ),
                FieldPanel("sticker"),
                MultiFieldPanel(
                    [
                        FieldRowPanel(
                            [
                                FieldPanel("sticker_dark_mode"),
                                FieldPanel("sticker_mobile"),
                                FieldPanel("sticker_dark_mode_mobile"),
                            ]
                        )
                    ],
                    heading="Sticker Variants",
                    classname="collapsed",
                ),
                FieldPanel(
                    "icon",
                    widget=ThumbnailRadioSelect(
                        thumbnail_template_mapping={choice[0]: "cms/wagtailadmin/icon-choice.html" for choice in ICON_CHOICES},
                        thumbnail_size=20,
                    ),
                ),
                FieldPanel("link_text"),
                FieldPanel("index_page_heading"),
                FieldPanel("description"),
            ],
            heading="Index Page Settings",
        ),
        FieldPanel("image"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("image_dark_mode"),
                        FieldPanel("image_mobile"),
                        FieldPanel("image_dark_mode_mobile"),
                    ]
                )
            ],
            heading="Article Image Variants",
            classname="collapsed",
        ),
        FieldPanel("content"),
        FieldPanel("related_articles"),
        InlinePanel("pencil_banner_placements", label="Pencil Banners"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    if TYPE_CHECKING:
        tag: Tag | None

    def __str__(self):
        return f"ArticleDetailPage: {self.title} - {self.locale}"

    def get_tag(self) -> Tag | None:
        if self.tag:
            return self.tag.get_localized()
        return None

    @property
    def pencil_banners(self):
        placements = self.pencil_banner_placements.select_related("snippet").order_by("sort_order")
        snippets = [placement.snippet.get_localized() for placement in placements]
        # get_localized() can return None if the snippet isn't translated and published
        return [snippet for snippet in snippets if snippet]


class ArticleThemePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays articles related to a specific theme."""

    upper_content = StreamField(
        [
            ("intro", IntroBlock()),
        ],
        use_json_field=True,
        blank=True,
        null=True,
    )

    content = StreamField(
        [
            ("intro", IntroBlock()),
            ("section", SectionBlock(require_heading=False)),
        ],
        use_json_field=True,
        default=list(),
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
        InlinePanel("pencil_banner_placements", label="Pencil Banners"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("upper_content"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    def __str__(self):
        return f"ArticleThemePage: {self.title} - {self.locale}"

    @property
    def pencil_banners(self):
        placements = self.pencil_banner_placements.select_related("snippet").order_by("sort_order")
        snippets = [placement.snippet.get_localized() for placement in placements]
        # get_localized() can return None if the snippet isn't translated and published
        return [snippet for snippet in snippets if snippet]


def _get_freeform_page_blocks(allow_uitour=True, allow_kit_intro=False):
    """Factory function to create block list for FreeFormPage2026 with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons in blocks.
                      If False, only allows regular buttons.

    Returns:
        List of tuples containing block names and instances configured
        with the appropriate button types.
    """
    base_blocks = [
        ("notification", NotificationBlock(group="Notification")),
        ("intro", IntroBlock(allow_uitour=allow_uitour, group="Intro")),
        ("section", SectionBlock(allow_uitour=allow_uitour, group="Main")),
        ("showcase", ShowcaseBlock(group="Media")),
        ("carousel", CarouselBlock(group="Media")),
        ("sliding_carousel", SlidingCarouselBlock(group="Media")),
        ("card_gallery", CardGalleryBlock(group="Media")),
        ("media_content", MediaContentBlock(group="Media", template="cms/blocks/sections/media-content-section.html")),
        ("cards_list", CardsListBlock(template="cms/blocks/sections/cards-list-section.html", allow_uitour=allow_uitour, group="Main")),
        ("featured_image_section", FeaturedImageSectionBlock(allow_uitour=allow_uitour, group="Main")),
        ("mobile_store_qr_code", MobileStoreQRCodeBlock(group="Media")),
        ("banner", BannerBlock(allow_uitour=allow_uitour, group="Banners")),
        ("topic_list", TopicListBlock(allow_uitour=allow_uitour, group="Main")),
        ("line_cards", LineCardsBlock(allow_uitour=allow_uitour, template="cms/blocks/sections/line-cards-section.html", group="Main")),
        ("button_row", ButtonRowBlock(allow_uitour=allow_uitour, group="Main")),
        ("enterprise_download", EnterpriseDownloadBlock(group="Main")),
        ("kit_banner", KitBannerBlock(allow_uitour=allow_uitour, group="Banners")),
        (
            "banner_snippet",
            LocalizedLiveSnippetChooserBlock(
                target_model="cms.BannerSnippet",
                template="cms/snippets/banner-snippet.html",
                label="Banner Snippet",
                group="Banners",
            ),
        ),
    ]
    if allow_kit_intro:
        return base_blocks + [
            ("kit_intro", KitIntroBlock(allow_uitour=allow_uitour, group="Intro")),
        ]
    return base_blocks


UPPER_FREEFORM_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=True, allow_kit_intro=True)
LOWER_FREEFORM_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=True, allow_kit_intro=False)


class PencilBannerPlacement(Orderable):
    page = ParentalKey("cms.FreeFormPage2026", on_delete=models.CASCADE, related_name="pencil_banner_placements")
    snippet = models.ForeignKey("cms.PencilBannerSnippet", on_delete=models.CASCADE, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Pencil Banner Placement"
        verbose_name_plural = "Pencil Banner Placements"

    panels = [
        FieldPanel("snippet"),
    ]

    def __str__(self):
        return self.page.title + " -> " + self.snippet.title


class HomePagePencilBannerPlacement(Orderable):
    page = ParentalKey("cms.HomePage", on_delete=models.CASCADE, related_name="pencil_banner_placements")
    snippet = models.ForeignKey("cms.PencilBannerSnippet", on_delete=models.CASCADE, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Home Page Pencil Banner Placement"
        verbose_name_plural = "Home Page Pencil Banner Placements"

    panels = [
        FieldPanel("snippet"),
    ]

    def __str__(self):
        return self.page.title + " -> " + self.snippet.title


class ArticleThemePagePencilBannerPlacement(Orderable):
    page = ParentalKey("cms.ArticleThemePage", on_delete=models.CASCADE, related_name="pencil_banner_placements")
    snippet = models.ForeignKey("cms.PencilBannerSnippet", on_delete=models.CASCADE, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Article Theme Page Pencil Banner Placement"
        verbose_name_plural = "Article Theme Page Pencil Banner Placements"

    panels = [
        FieldPanel("snippet"),
    ]

    def __str__(self):
        return self.page.title + " -> " + self.snippet.title


class ArticleDetailPagePencilBannerPlacement(Orderable):
    page = ParentalKey("cms.ArticleDetailPage", on_delete=models.CASCADE, related_name="pencil_banner_placements")
    snippet = models.ForeignKey("cms.PencilBannerSnippet", on_delete=models.CASCADE, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Article Detail Page Pencil Banner Placement"
        verbose_name_plural = "Article Detail Page Pencil Banner Placements"

    panels = [
        FieldPanel("snippet"),
    ]

    def __str__(self):
        return self.page.title + " -> " + self.snippet.title


class FreeFormPage2026(PreFooterImageMixin, PromotedPageMixin, UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
    """A flexible 2026 page type with optional upper/lower split layout."""

    upper_content = StreamField(
        UPPER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Optional upper content. If present, the page will use a split layout.",
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
        blank=True,
        null=True,
    )

    theme = models.CharField(
        max_length=20,
        blank=True,
        choices=THEME_CHOICES,
        default=FIREFOX_THEME,
        verbose_name="Theme",
        help_text="The theme to use for this page. This overrides the page's CSS, navigation, footer, logo and other visual elements.",
    )
    show_pre_footer = models.BooleanField(
        default=True,
        verbose_name="Show Pre-Footer",
        help_text="If true, the page will display the default pre-footer section.",
    )
    show_nav_cta = models.BooleanField(
        default=True,
        verbose_name="Show Navigation CTA",
        help_text="If true, the download button will appear in the navigation bar for this page. "
        "Only applicable if 'Show Navigation' is also enabled.",
    )
    show_navigation = models.BooleanField(
        default=True,
        verbose_name="Show Navigation",
        help_text="If true, the navigation menu will be displayed on this page's header bar.",
    )
    body_class = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Body Class",
        help_text=(
            "Additional CSS class to add to the body tag for this page, to be used for light theming. "
            "The page will also inject <this>.css, so ensure that exists before using this field."
        ),
    )
    extra_js = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Extra JS",
        help_text=("Additional JavaScript file to include for this page. Use the static bundle name (without the .js extension)."),
    )
    docs = RichTextField(
        blank=True,
        features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL,
        help_text=(
            "Optional documentation about this page. Only used by Flare Docs demo pages "
            "to describe the block(s) or snippet(s) being demonstrated — leave blank on production pages."
        ),
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    promote_panels = UTMParamsMixin.promote_panels + [
        FieldPanel("enable_marketing_attribution"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
        MultiFieldPanel(
            [
                FieldPanel("theme"),
                FieldPanel("body_class"),
                FieldPanel("extra_js"),
            ],
            heading="Appearance",
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_navigation"),
                FieldPanel("show_nav_cta"),
            ],
            heading="Navigation",
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_pre_footer"),
                *PreFooterImageMixin.pre_footer_image_panels,
                InlinePanel("pencil_banner_placements", label="Pencil Banners"),
                *QRCodeFloatingSnippetMixin.floating_qr_panels,
            ],
            heading="Snippets",
        ),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
        SynchronizedField("pre_footer_image"),
    ]

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("upper_content"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Free Form 2026 Page"
        verbose_name_plural = "Free Form 2026 Pages"

    def __str__(self):
        return f"FreeFormPage2026: {self.title} - {self.locale}"

    @property
    def noindex(self):
        return self.enable_marketing_attribution

    @property
    def pencil_banners(self):
        placements = self.pencil_banner_placements.select_related("snippet").order_by("sort_order")
        snippets = [placement.snippet.get_localized() for placement in placements]
        # get_localized() can return None if the snippet isn't translated and published
        return [snippet for snippet in snippets if snippet]


class WhatsNewIndexPage(AbstractSpringfieldCMSPage):
    """Index page for the Whats New pages that redirect to the latest version's What's New Page."""

    # Empty parent page types will prevent this page from being created from the Wagtail admin
    # Only one instance of this page should exist
    # When a HomePage is implemented, this page should be moved to be a child of HomePage
    # parent_page_types = []
    subpage_types = ["cms.WhatsNewPage2026"]

    class Meta:
        verbose_name = "What's New Index Page"
        verbose_name_plural = "What's New Index Pages"

    def __str__(self):
        return f"WhatsNewIndexPage: {self.title} - {self.locale}"

    def serve(self, request):
        latest_whats_new = (
            self.get_children()
            .live()
            .public()
            .exclude(slug="general")
            .annotate(version=F("whatsnewpage2026__version"))
            .order_by("-version")
            .specific()
            .first()
        )
        if latest_whats_new:
            return redirect(request.build_absolute_uri(latest_whats_new.get_url()))
        return redirect("/")


class WhatsNewPage2026(PreFooterImageMixin, UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
    """A 2026 version of the What's New page with optional upper/lower split layout."""

    parent_page_types = ["cms.WhatsNewIndexPage"]
    subpage_types = []

    ftl_files = ["firefox/whatsnew/evergreen"]

    version = models.CharField(
        max_length=10,
        help_text="The version of Firefox this What's New page refers to, or 'general' for a non-version-specific page.",
    )
    upper_content = StreamField(
        UPPER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Optional upper content. If present, the page will use a split layout.",
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
    )

    theme = models.CharField(
        max_length=20,
        blank=True,
        choices=THEME_CHOICES,
        default=FIREFOX_THEME,
        verbose_name="Theme",
        help_text="The theme to use for this page. This overrides the page's CSS, navigation, footer, logo and other visual elements.",
    )
    body_class = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Body Class",
        help_text=(
            "Additional CSS class to add to the body tag for this page, to be used for light theming. "
            "The page will also inject <this>.css, so ensure that exists before using this field."
        ),
    )
    extra_js = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Extra JS",
        help_text=("Additional JavaScript file to include for this page. Use the static bundle name (without the .js extension)."),
    )

    content_panels = [
        FieldPanel("title"),
        TitleFieldPanel("version", placeholder="123"),
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
        MultiFieldPanel(
            [
                FieldPanel("theme"),
                FieldPanel("body_class"),
                FieldPanel("extra_js"),
            ],
            heading="Appearance",
        ),
        MultiFieldPanel(
            PreFooterImageMixin.pre_footer_image_panels,
            heading="Snippets",
        ),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
        SynchronizedField("pre_footer_image"),
    ]

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("upper_content"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
    ]

    class Meta:
        indexes = [
            models.Index(fields=["version"]),
        ]
        verbose_name = "What's New 2026 Page"
        verbose_name_plural = "What's New 2026 Pages"

    def __str__(self):
        return f"WhatsNewPage2026: {self.title} - {self.locale}"

    def get_utm_campaign(self):
        return self.get_stub_attribution_utm_campaign() or f"whatsnew-{self.version}"

    @property
    def noindex(self):
        return True


class SmartWindowPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page to promote Smart Window"""

    ALLOWED_TERRITORIES = {"US", "CA", "FR"}
    ALLOWED_TERRITORIES_OPTION = "allowed_territories"
    ALLOWED_TERRITORIES_LABEL = "US, Canada, and France only"

    heading_text = RichTextField(features=HEADING_TEXT_FEATURES)
    subheading_text = RichTextField(features=HEADING_TEXT_FEATURES)

    animation = models.URLField(blank=True, validators=[validate_animation_url], help_text="Link to a webm video from assets.mozilla.net.")
    animation_alt = models.CharField(max_length=255, blank=True, help_text="Text for screen readers describing the video.")
    image = models.ForeignKey(
        "cms.SpringfieldImage", on_delete=models.PROTECT, related_name="+", help_text="Used as fallback if an animation is provided."
    )
    image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode variant of the image.",
    )
    image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional mobile variant of the image.",
    )
    image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode mobile variant of the image.",
    )

    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
    )

    # TODO: remove this field. This was kept here to avoid a rename migration.
    waitlist_button_label = models.CharField(default="Try Smart Window", max_length=255)
    show_smart_window_button = models.CharField(
        max_length=20,
        choices=(
            ("all", "Show to all users"),
            (ALLOWED_TERRITORIES_OPTION, ALLOWED_TERRITORIES_LABEL),
            ("never", "Never show to any users"),
        ),
        default=ALLOWED_TERRITORIES_OPTION,
        help_text="Controls whether the 'Try Smart Window' button is shown on the page. When not available, the Waitlist form is shown instead.",
    )
    smart_window_button_label = models.CharField(max_length=255, default="Try Smart Window")
    nav_button_uid = models.UUIDField(default=uuid.uuid4, help_text="Unique identifier for the Header Smart Window button.")
    intro_button_uid = models.UUIDField(default=uuid.uuid4, help_text="Unique identifier for the Intro Smart Window button.")
    redirect_page = models.ForeignKey(
        "cms.SmartWindowExplainerPage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The page users will be taken to after clicking the Smart Window button.",
    )

    waitlist_submit_uid = models.UUIDField(default=uuid.uuid4, help_text="Unique identifier for the Waitlist form submit button.")
    form_submit_label = models.CharField(max_length=255, default="Join the Waitlist")
    thank_you_heading = RichTextField(features=HEADING_TEXT_FEATURES, default='<p data-block-key="abcdef">You’re on the list!</p>')
    thank_you_message = RichTextField(features=HEADING_TEXT_FEATURES, default='<p data-block-key="abcdef">Thank you!</p>')
    privacy_notice = RichTextField(
        features=HEADING_TEXT_FEATURES,
        default='<p data-block-key="abcdef">I’m okay with Mozilla handling my info as explained in this '
        '<a href="https://www.mozilla.org/privacy/websites/">Privacy Notice</a>.</p>',
    )
    mobile_message = RichTextField(
        features=HEADING_TEXT_FEATURES,
        default='<p data-block-key="abcdef">This experience is only available on desktop. Please open this page on your computer.</p>',
    )

    download_button_label = models.CharField(max_length=255, default="Download Firefox", help_text="Label for the button to download Firefox.")
    nav_download_button_uid = models.UUIDField(default=uuid.uuid4, help_text="Unique identifier for the Header Download Firefox button.")
    intro_download_button_uid = models.UUIDField(default=uuid.uuid4, help_text="Unique identifier for the Intro Download Firefox button.")

    update_button_label = models.CharField(
        max_length=255, default="How to update Firefox", help_text="Label for the button that appears if the user needs to update Firefox."
    )
    update_button_uid = models.UUIDField(
        default=uuid.uuid4, help_text="Unique identifier for the Update Firefox button that appears if the user needs to update."
    )
    update_instructions = RichTextField(
        features=HEADING_TEXT_FEATURES,
        default="<p data-block-key='abcdef'>Before you can try Smart Window, you’ll need to download the latest version of Firefox.</p>",
        help_text="Instructions displayed to the user if they need to update Firefox before trying Smart Window.",
    )
    update_link = models.URLField(
        default="https://support.mozilla.org/en-US/products/firefox/installation-and-updates",
        help_text="URL for the update Firefox instructions page.",
    )
    copy_to_clipboard_label = models.CharField(
        max_length=255, default="Copy link to page", help_text="Label for the button that copies the page link to the clipboard."
    )
    copy_success_label = models.CharField(
        max_length=255, default="Copied", help_text="Label displayed when the link is successfully copied to the clipboard."
    )
    post_download_instructions = RichTextField(
        features=HEADING_TEXT_FEATURES,
        blank=True,
        default="<p data-block-key='abcdef'>Return to this page after updating Firefox to unlock access to Smart Window BETA.</p>",
        help_text="Instructions displayed to the user for next steps after downloading Firefox.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("heading_text"),
                FieldPanel("subheading_text"),
                FieldPanel("animation"),
                FieldPanel("animation_alt"),
                FieldPanel("image"),
                FieldRowPanel(
                    [
                        FieldPanel("image_dark_mode"),
                        FieldPanel("image_mobile"),
                        FieldPanel("image_dark_mode_mobile"),
                    ],
                    heading="Image Variants",
                ),
            ],
            heading="Intro",
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_smart_window_button"),
                FieldPanel("smart_window_button_label"),
                FieldPanel("nav_button_uid"),
                FieldPanel("intro_button_uid"),
                FieldPanel("redirect_page"),
                FieldPanel("mobile_message"),
            ],
            heading="Smart Window Button",
        ),
        MultiFieldPanel(
            [
                FieldPanel("thank_you_heading"),
                FieldPanel("thank_you_message"),
                FieldPanel("form_submit_label"),
                FieldPanel("waitlist_submit_uid"),
                FieldPanel("privacy_notice"),
            ],
            heading="Waitlist Form",
        ),
        MultiFieldPanel(
            [
                FieldPanel("download_button_label"),
                FieldPanel("nav_download_button_uid"),
                FieldPanel("intro_download_button_uid"),
                FieldPanel("update_button_label"),
                FieldPanel("update_button_uid"),
                FieldPanel("update_instructions"),
                FieldPanel("update_link"),
                FieldPanel("copy_to_clipboard_label"),
                FieldPanel("copy_success_label"),
                FieldPanel("post_download_instructions"),
            ],
            heading="Download and Update Buttons",
        ),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("heading_text"),
        index.SearchField("subheading_text"),
        index.SearchField("content"),
        index.SearchField("mobile_message"),
        index.SearchField("thank_you_heading"),
        index.SearchField("thank_you_message"),
        index.SearchField("privacy_notice"),
        index.SearchField("update_instructions"),
        index.SearchField("post_download_instructions"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Smart Window Page"
        verbose_name_plural = "Smart Window Pages"

    def __str__(self):
        return f"SmartWindowPage: {self.title} - {self.locale}"

    def clean(self):
        super().clean()
        if self.animation and not self.animation_alt:
            raise ValidationError("An alt text description is required when an animation URL is provided.")

    def serve(self, request, *args, **kwargs):
        if request.GET.get("v") == "product":
            if child := self.get_children().live().public().filter(slug="start").first():
                return redirect(child.get_url(request))

        response = super().serve(request, *args, **kwargs)
        if self.show_smart_window_button == self.ALLOWED_TERRITORIES_OPTION:
            add_never_cache_headers(response)
        return response

    def get_utm_campaign(self):
        return self.get_stub_attribution_utm_campaign() or "smart_window"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["ui_tour_class"] = UI_TOUR_CLASSES[UITOUR_BUTTON_SMART_WINDOW]
        context["redirect_url"] = self.redirect_page.get_url() if self.redirect_page else None
        context["override_view"] = request.GET.get("view")

        # ?view=waitlist forces waitlist regardless of geo
        if context["override_view"] == "waitlist":
            context["show_try_smart_window"] = False
        else:
            country = get_country_from_request(request)
            context["show_try_smart_window"] = self.show_smart_window_button == "all" or (
                self.show_smart_window_button == self.ALLOWED_TERRITORIES_OPTION and country in self.ALLOWED_TERRITORIES
            )
        return context


class SmartWindowExplainerPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A Smart Window themed page"""

    upper_content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS,
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("upper_content"),
        index.SearchField("content"),
    ]

    class Meta:
        verbose_name = "Smart Window Explainer Page"
        verbose_name_plural = "Smart Window Explainer Pages"

    def __str__(self):
        return f"SmartWindowExplainerPage: {self.title} - {self.locale}"


class BlogIndexPage(RoutablePageMixin, UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that lists blog posts."""

    subpage_types = ["cms.BlogArticlePage"]
    ftl_files = ["cms/blog"]

    page_heading = StreamField(
        [("heading", HeadingBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
    )
    featured_articles = StreamField(
        [("article", BlogArticleBlock())],
        max_num=8,
        use_json_field=True,
        null=True,
        blank=True,
        help_text="Up to 8 featured articles shown at the top of the index page.",
    )
    more_articles_heading = RichTextField(features=HEADING_TEXT_FEATURES, default='<p data-block-key="53ojj213">Read more</p>')
    view_all_label = models.CharField(default="View All Articles")
    cards_lists = StreamField(
        [
            ("cards_list", BlogCardsListBlock()),
        ],
        use_json_field=True,
        null=True,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("page_heading"),
        FieldPanel("featured_articles"),
        MultiFieldPanel(
            [
                FieldPanel("more_articles_heading"),
                FieldPanel("view_all_label"),
                FieldPanel("cards_lists"),
            ],
            heading="More Articles",
        ),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("page_heading"),
        index.SearchField("more_articles_heading"),
        index.SearchField("cards_lists"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Index Page"
        verbose_name_plural = "Blog Index Pages"

    def __str__(self):
        return f"BlogIndexPage: {self.title} - {self.locale}"

    def _prefetch_streamfield_articles(self):
        """Bulk-fetch all BlogArticlePages referenced in featured_articles and cards_lists,
        and populate _article_cache on each block value to avoid per-block DB queries."""
        from springfield.cms.models.snippets import Tag

        # StreamField iteration yields BoundBlocks; their .value is BlockArticleValue.
        # ListBlock iteration yields StructValues (BlockArticleValue) directly.
        featured_articles_values = [b.value for b in (self.featured_articles or [])]
        cards_lists_values = []
        for cards_list_block in self.cards_lists or []:
            cards_lists_values.extend(list(cards_list_block.value["articles"]))

        all_values = featured_articles_values + cards_lists_values
        pks = [value["article"].pk for value in all_values if value.get("article")]

        if not pks:
            return

        articles_by_pk = {
            a.pk: a
            for a in BlogArticlePage.objects.filter(pk__in=pks)
            .select_related(
                "topic",
                "image",
                "image_dark_mode",
                "image_mobile",
                "image_dark_mode_mobile",
            )
            .prefetch_related(
                "tags",
                "image__renditions",
                "image_dark_mode__renditions",
                "image_mobile__renditions",
                "image_dark_mode_mobile__renditions",
            )
            .defer("content")
        }

        active_locale = SpringfieldLocale.get_active()
        localized_tags = Tag.objects.filter(locale=active_locale).live()
        localized_tags_by_slug = {tag.slug: tag for tag in localized_tags}

        for value in all_values:
            page = value.get("article")
            if page and page.pk in articles_by_pk:
                article = articles_by_pk[page.pk]
                if article.topic and article.topic.slug in localized_tags_by_slug:
                    article._topic_cache = localized_tags_by_slug[article.topic.slug]
                tags_cache = []
                for tag in article.tags.all():
                    if tag.slug in localized_tags_by_slug:
                        tags_cache.append(localized_tags_by_slug[tag.slug])
                article._tags_cache = tags_cache
                value._article_cache = article

    def get_context(self, request, *args, **kwargs):
        from springfield.cms.models.snippets import Tag

        context = super().get_context(request, *args, **kwargs)

        self._prefetch_streamfield_articles()

        base_qs = BlogArticlePage.objects.child_of(self).live().public()
        all_topics = (
            Tag.objects.filter(locale=self.locale, blog_articles__in=base_qs.values("pk"))
            .annotate(article_count=Count("blog_articles"))
            .order_by("-article_count")
        )
        context["all_topics"] = all_topics
        return context

    def _render_route(self, request, template, extra_context=None):
        request.is_preview = False
        request = self._patch_request_for_springfield(request)
        context = self.get_context(request)
        if extra_context:
            context.update(extra_context)
        return l10n_utils.render(request, template, context, ftl_files=self.ftl_files)

    @path("")
    def index_route(self, request):
        return self._render_route(request, self.get_template(request))

    @path("topics/")
    def topics_route(self, request):
        return self._render_route(request, "cms/blog_topics_page.html")

    @path("all/")
    def all_route(self, request):
        from springfield.cms.models.snippets import Tag

        base_qs = (
            BlogArticlePage.objects.child_of(self)
            .live()
            .public()
            .select_related(
                "topic",
                "image",
                "image_dark_mode",
                "image_mobile",
                "image_dark_mode_mobile",
            )
            .prefetch_related(
                "tags",
                "image__renditions",
                "image_dark_mode__renditions",
                "image_mobile__renditions",
                "image_dark_mode_mobile__renditions",
            )
            .defer("content")
        )

        topic = None
        topic_slug = request.GET.get("topic")
        if topic_slug:
            topic = Tag.objects.filter(slug=topic_slug, locale=self.locale).first()
            base_qs = base_qs.filter(topic=topic)

        list_articles_qs = base_qs.order_by("-first_published_at")
        paginator = Paginator(list_articles_qs, 10)

        if topic:
            topic.article_count = paginator.count
        list_articles = paginator.get_page(request.GET.get("page", 1))

        return self._render_route(
            request,
            "cms/blog_all_page.html",
            {
                "list_articles": list_articles,
                "topic": topic,
            },
        )


class BlogArticlePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays a single blog article."""

    parent_page_types = ["cms.BlogIndexPage"]
    ftl_files = ["cms/blog"]

    description = RichTextField(
        blank=True,
        features=HEADING_TEXT_FEATURES,
        help_text="A short description used on the index page.",
    )
    display_image = models.BooleanField(
        default=False,
        help_text="Display image on the article's list",
    )

    topic = models.ForeignKey(
        "cms.Tag",
        on_delete=models.PROTECT,
        related_name="blog_articles",
    )
    tags = models.ManyToManyField(
        "cms.Tag",
        related_name="blog_articles_tags",
        blank=True,
    )
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    image_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode variant of the article image.",
    )
    image_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional mobile variant of the article image.",
    )
    image_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional dark mode mobile variant of the article image.",
    )
    content = StreamField(
        [
            ("text", RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL)),
            ("media", MediaBlock()),
            ("code", CodeBlock()),
            ("quote", QuoteBlock()),
        ],
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("description"),
                FieldPanel("display_image"),
            ],
            heading="Index Page Settings",
        ),
        MultiFieldPanel(
            [
                FieldPanel("topic"),
                FieldPanel("tags", widget=CheckboxSelectMultiple()),
            ],
            heading="Tags",
        ),
        MultiFieldPanel(
            [
                FieldPanel("image"),
                FieldRowPanel(
                    [
                        FieldPanel("image_dark_mode"),
                        FieldPanel("image_mobile"),
                        FieldPanel("image_dark_mode_mobile"),
                    ]
                ),
            ],
            heading="Article Image Variants",
        ),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("description"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Article Page"
        verbose_name_plural = "Blog Article Pages"

    def __str__(self):
        return f"BlogArticlePage: {self.title} - {self.locale}"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        related = (
            BlogArticlePage.objects.sibling_of(self).live().public().filter(topic=self.topic).exclude(pk=self.pk).order_by("-first_published_at")[:4]
        )
        context["related_articles"] = list(related)
        return context

    def get_topic(self):
        if not hasattr(self, "_topic_cache"):
            if self.topic:
                self._topic_cache = self.topic.get_localized()
            else:
                self._topic_cache = None
        return self._topic_cache

    def get_tags(self):
        if not hasattr(self, "_tags_cache"):
            if self.tags.all():
                self._tags_cache = [tag.get_localized() for tag in self.tags.all()]
            else:
                self._tags_cache = None
        return self._tags_cache


class RoadmapPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays the Firefox roadmap."""

    ftl_files = ["cms/roadmap"]

    intro = StreamField(
        [("intro", IntroBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
    )
    content = StreamField(
        [
            ("roadmap_list_section", RoadmapListSectionBlock()),
            ("banner", BannerBlock(group="Banners")),
            ("kit_banner", KitBannerBlock(group="Banners")),
        ],
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("intro"),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("intro"),
        index.SearchField("content"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Roadmap Page"
        verbose_name_plural = "Roadmap Pages"

    def __str__(self):
        return f"RoadmapPage: {self.title} - {self.locale}"


class ContactPage(AbstractSpringfieldCMSPage):
    """A CMS-editable contact form page with a configurable StreamField form builder."""

    template = "cms/contact_page.html"
    ftl_files = ["cms/contact"]

    intro = StreamField(
        [("intro", IntroBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
    )

    form_fields = StreamField(
        [
            ("text_field", TextFieldBlock()),
            ("textarea_field", TextAreaFieldBlock()),
            ("email_field", EmailFieldBlock()),
            ("phone_field", PhoneFieldBlock()),
            ("select_field", SelectFieldBlock()),
            ("checkbox_field", CheckboxFieldBlock()),
            ("checkbox_group_field", CheckboxGroupFieldBlock()),
            ("hidden_field", HiddenFieldBlock()),
            ("country_select_field", CountrySelectFieldBlock()),
        ],
        blank=True,
        null=True,
        use_json_field=True,
        help_text="Define the form fields that will appear on the contact page.",
    )

    to_email_address = models.EmailField(
        blank=True,
        help_text="Email address where form submissions will be sent.",
    )

    basket_api_path = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "Basket API path (e.g. /api/v1/contact/). Concatenated with settings.BASKET_URL on submission. Required if Email Address is not set."
        ),
    )

    redirect_to = models.ForeignKey(
        "wagtailcore.Page",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        help_text="Page to redirect to after a successful form submission (e.g. a thank-you page).",
    )

    thank_you_message = RichTextField(
        blank=True,
        help_text="Message shown in place of the form after a successful submission. Required if Redirect To is not set.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("intro"),
        FieldPanel("form_fields"),
        FieldPanel("thank_you_message"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
        MultiFieldPanel(
            [
                FieldPanel("to_email_address"),
                FieldPanel("basket_api_path"),
                FieldPanel("redirect_to"),
            ],
            heading="Form Submission Settings",
        ),
    ]

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("intro"),
        index.SearchField("form_fields"),
        index.SearchField("thank_you_message"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Contact Page"
        verbose_name_plural = "Contact Pages"

    def __str__(self):
        return f"ContactPage: {self.title} - {self.locale}"

    def clean(self):
        super().clean()
        errors = {}

        has_email = bool(self.to_email_address)
        has_basket = bool(self.basket_api_path)

        if not has_email and not has_basket:
            msg = "Set either an email address or a basket API path."
            errors["to_email_address"] = msg
            errors["basket_api_path"] = msg
        elif has_email and has_basket:
            msg = "Set either an email address or a basket API path, not both."
            errors["to_email_address"] = msg
            errors["basket_api_path"] = msg

        if has_basket and not has_email:
            parsed = urlparse(self.basket_api_path)
            if parsed.scheme or parsed.netloc:
                errors["basket_api_path"] = "Enter a path (e.g. /api/v1/contact/), not a full URL."
            elif not parsed.path.startswith("/"):
                errors["basket_api_path"] = "Path must start with /."

        if not self.redirect_to and not self.thank_you_message:
            msg = "Set either a redirect page or a thank you message."
            errors["redirect_to"] = msg
            errors["thank_you_message"] = msg

        # On production, only certain paths are allowed to send POST requests
        if settings.PROD:
            parent = self.get_parent()
            path = parent.url_path + self.slug + "/" if parent else "/" + self.slug + "/"
            # Using .search() instead of .match() because paths will often start with /home/parent/child/
            # We don't use .get_url() because it doesn't use the instance's current slug
            if not any(re.search(allowed_path, path) for allowed_path in settings.CONTACT_PAGE_ALLOWED_PATHS):
                errors["slug"] = f"Slug must match one of the allowed paths: {', '.join(settings.CONTACT_PAGE_ALLOWED_PATHS)}"

        if errors:
            raise ValidationError(errors)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        form = getattr(request, "form", None)
        context["form_errors"] = getattr(form, "errors", {})
        if getattr(request, "form_success", False):
            context["form_success"] = True
        context["form_data"] = self._get_display_data(form)
        return context

    def serve(self, request, *args, **kwargs):
        request.form = self.get_form(request)
        success = None

        if request.method == "POST":
            if request.form.is_valid():
                if self.basket_api_path:
                    success = self.send_to_basket(request)
                elif self.to_email_address:
                    success = self.send_form_email(request)
                if not success:
                    request.form.add_error(None, ftl_lazy("contact-form-error-sending", ftl_files=self.ftl_files))
            else:
                success = False

            request.form_success = success

            if success and self.redirect_to:
                return redirect(self.redirect_to.localized.url)

        response = super().serve(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    def get_form(self, request):
        """Return a Django Form instance generated from the form_fields StreamField.

        Bound to ``request.POST`` for POST requests, unbound otherwise.
        """
        form_fields = {}
        for field in self.form_fields:
            value = field.value
            form_fields[value["internal_identifier"]] = value.get_form_field()

        ContactForm = type("ContactForm", (forms.Form,), form_fields)

        # Hidden fields always arrive in POST, they must not be considered when checking for an empty submission.
        hidden_identifiers = {field.value["internal_identifier"] for field in self.form_fields if field.block_type == "hidden_field"}
        visible_identifiers = {field.value["internal_identifier"] for field in self.form_fields if field.block_type != "hidden_field"}

        def clean_form(_self):
            # The honeypot must stay empty, and every hidden field must have a value
            honeypot = _self.data.get("office_fax")
            empty_hidden_fields = any(not _self.data.get(identifier) for identifier in hidden_identifiers)
            if honeypot or empty_hidden_fields:
                raise forms.ValidationError(ftl_lazy("contact-form-error-sending", ftl_files=self.ftl_files))
            # Only flag an empty submission when no per-field error already exists
            has_any_data = any(_self.cleaned_data.get(identifier) for identifier in visible_identifiers)
            if not has_any_data and not _self.errors:
                raise forms.ValidationError(ftl_lazy("contact-form-error-empty", ftl_files=self.ftl_files))

        ContactForm.clean = clean_form

        if request.method == "POST":
            return ContactForm(request.POST)
        return ContactForm()

    def _get_display_data(self, form):
        """Build a display dict from raw form data for template persistence"""

        if form is None:
            return {}
        data = form.data
        result = {}
        for field in self.form_fields:
            if field.block_type == "hidden_field":
                continue
            identifier = field.value["internal_identifier"]
            if field.value.is_multivalue:
                result[identifier] = data.getlist(identifier)
            else:
                result[identifier] = data.get(identifier, "")
        return result

    def _collect_field_values(self, form):
        """Return submitted values keyed by internal_identifier, normalized to the
        string types the basket API and email template expect."""

        values = {}
        for field in self.form_fields:
            identifier = field.value["internal_identifier"]
            value = form.cleaned_data.get(identifier)
            if isinstance(value, list):
                value = ", ".join(value)
            elif isinstance(value, bool):
                value = "on" if value else ""
            elif value is None:
                value = ""
            values[identifier] = value
        return values

    def send_form_email(self, request) -> bool:
        """Collect form data and send it as an email."""

        from springfield.cms.templatetags.cms_tags import remove_tags  # Circular import

        success = None
        try:
            values = self._collect_field_values(request.form)
            field_data = []
            for field in self.form_fields:
                label = field.value["label"]
                if isinstance(label, RichText):
                    label = remove_tags(richtext(label))
                field_data.append({"label": label, "value": values.get(field.value["internal_identifier"], "")})

            msg = render_to_string("cms/emails/contact-form.txt", {"fields": field_data})
            subject = f"Contact form submission: {self.title}"
            email = EmailMessage(subject, msg, settings.DEFAULT_FROM_EMAIL, [self.to_email_address])
            email.send()
            success = True
        except Exception as exc:
            with new_scope() as scope:
                scope.set_extra("exception", str(exc))
                capture_message(
                    "Failed to send contact form email",
                    level="error",
                )
            success = False
        return success

    def send_to_basket(self, request) -> bool:
        """Collect form data and send it to the basket API."""

        success = None
        form_data = self._collect_field_values(request.form)
        try:
            api_response = requests.post(
                f"{settings.BASKET_URL}{self.basket_api_path}",
                json=form_data,
                timeout=settings.BASKET_TIMEOUT,
            )
            if api_response.ok:
                success = True
            else:
                # Log any unexpected 4xx errors to Sentry
                UNPROCESSABLE_CONTENT = 422  # Basket rejects data such as invalid characters
                TOO_MANY_REQUESTS = 429  # Rate limiting
                if api_response.status_code not in (UNPROCESSABLE_CONTENT, TOO_MANY_REQUESTS) and 400 <= api_response.status_code < 500:
                    with new_scope() as scope:
                        scope.set_extra("post_data", form_data)
                        scope.set_extra("basket_path", self.basket_api_path)
                        scope.set_extra("status_code", api_response.status_code)
                        capture_message(
                            f"Basket API returned {api_response.status_code} for path {self.basket_api_path}",
                            level="error",
                        )
                success = False
        except requests.RequestException as exc:
            with new_scope() as scope:
                scope.set_extra("basket_path", self.basket_api_path)
                scope.set_extra("exception", str(exc))
                capture_message(
                    f"Basket API request failed for path {self.basket_api_path}",
                    level="error",
                )
            success = False
        return success


_FLARE_SECTION_ORDER = ["blocks", "snippets", "sample-pages"]


class FlareDocsIndexPage(AbstractSpringfieldCMSPage):
    """
    A page containing an index of all docs pages for Flare26.
    It shows links to other docs pages.
    """

    # Only created programmatically
    parent_page_types = []

    template = "cms/flare_docs_index_page.html"

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    def __str__(self):
        return f"FlareDocsIndexPage: {self.title} - {self.locale}"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        children = list(self.get_children().live().public().specific().order_by("title"))
        children.sort(key=lambda p: (_FLARE_SECTION_ORDER.index(p.slug) if p.slug in _FLARE_SECTION_ORDER else len(_FLARE_SECTION_ORDER), p.title))
        steplen = WagtailBasePage.steplen
        pages_by_parent = {}
        for desc in self.get_descendants().live().public().specific().order_by("title"):
            pages_by_parent.setdefault(desc.path[:-steplen], []).append(desc)

        def build_node(page):
            children = [build_node(c) for c in pages_by_parent.get(page.path, [])]
            children.sort(key=lambda n: (0 if n["children"] else 1, n["page"].title))
            return {"page": page, "children": children}

        context["sections"] = [build_node(child) for child in children]
        return context
