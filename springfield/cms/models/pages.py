# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import functools
import re
import uuid
from types import SimpleNamespace
from typing import TYPE_CHECKING

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import DatabaseError, models
from django.db.models import Count
from django.db.models.expressions import F
from django.http import Http404
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.functional import SimpleLazyObject

import requests
from modelcluster.fields import ParentalKey
from sentry_sdk import capture_message, new_scope
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface, TitleFieldPanel
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
from springfield.base.waffle import switch
from springfield.cms.blocks import (
    HEADING_TEXT_FEATURES,
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
    ComparisonTableBlock,
    CountrySelectFieldBlock,
    DownloadSupportBlock,
    EmailFieldBlock,
    EnterpriseDownloadBlock,
    FeaturedImageSectionBlock,
    HeadingBlock,
    HiddenFieldBlock,
    HomeKitBannerBlock,
    IconChoiceBlock,
    ImageCaptionBlock,
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
from springfield.cms.fields import LocalizedClusterTaggableManager, StreamField
from springfield.cms.middleware import mark_locale_fallback_exempt
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.rich_text import RichTextBlock, RichTextField
from springfield.firefox.referral import crypto
from springfield.firefox.referral.models import FirefoxReferralData
from springfield.firefox.referral.utils import REFERRAL_ID_LENGTH, validate_referral_id

from .base import AbstractSpringfieldCMSPage, PromotedPageMixin

if TYPE_CHECKING:
    from springfield.cms.models import Tag


BASE_UTM_PARAMETERS = {
    "utm_source": "www.firefox.com",
    "utm_medium": "referral",
}

# Pre-built widget for the ArticleDetailPage.icon model field — reuses the same
# directory scan and thumbnail map as IconChoiceBlock used in StreamFields.
_icon_choice_widget = IconChoiceBlock(required=False).field.widget


FIREFOX_THEME = ""
ENTERPRISE_THEME = "enterprise"
THEME_CHOICES = (
    (FIREFOX_THEME, "Firefox"),
    (ENTERPRISE_THEME, "Enterprise"),
)

ARTICLES_PER_PAGE = 10


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
    content_panels = AbstractSpringfieldCMSPage.content_panels + [
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


class PageThemeMixin(models.Model):
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

    theme_panels = [
        FieldPanel("theme"),
        FieldPanel("body_class"),
        FieldPanel("extra_js"),
    ]

    class Meta:
        abstract = True


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

    # NOTE: stored DB value remains "sticker_card" for backwards compatibility.
    INDEX_CARD_PICTOGRAM = "sticker_card"
    INDEX_CARD_OUTLINE = "outline_card"
    INDEX_CARD_ILLUSTRATION = "illustration_card"

    INDEX_CARD_TYPE_CHOICES = (
        (INDEX_CARD_PICTOGRAM, "Pictogram card"),
        (INDEX_CARD_OUTLINE, "Outline card"),
        (INDEX_CARD_ILLUSTRATION, "Illustration card"),
    )

    index_card_type = models.CharField(
        max_length=20,
        choices=INDEX_CARD_TYPE_CHOICES,
        default=INDEX_CARD_PICTOGRAM,
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
        help_text="A pictogram image used in article cards.",
    )
    sticker_dark_mode = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode variant of the pictogram.",
    )
    sticker_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional mobile variant of the pictogram.",
    )
    sticker_dark_mode_mobile = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional dark mode mobile variant of the pictogram.",
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        default="",
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
                    heading="Pictogram Variants",
                    classname="collapsed",
                ),
                FieldPanel(
                    "icon",
                    widget=ThumbnailRadioSelect(
                        choices=_icon_choice_widget.choices,
                        thumbnail_mapping=_icon_choice_widget.thumbnail_mapping,
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
        ("featured_image_section", FeaturedImageSectionBlock(allow_uitour=allow_uitour, group="Media")),
        ("mobile_store_qr_code", MobileStoreQRCodeBlock(group="Media")),
        ("banner", BannerBlock(allow_uitour=allow_uitour, group="Banners")),
        ("topic_list", TopicListBlock(allow_uitour=allow_uitour, group="Main")),
        ("line_cards", LineCardsBlock(allow_uitour=allow_uitour, template="cms/blocks/sections/line-cards-section.html", group="Main")),
        ("button_row", ButtonRowBlock(allow_uitour=allow_uitour, group="Main")),
        ("comparison_table", ComparisonTableBlock(group="Main")),
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
        ("image_caption", ImageCaptionBlock(group="Media")),
        (
            "rich_text",
            RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL, group="Main", template="cms/blocks/sections/rich-text-section.html"),
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


class BlogArticleAuthor(Orderable):
    page = ParentalKey("cms.BlogArticlePage", on_delete=models.CASCADE, related_name="article_authors")
    author = models.ForeignKey("cms.BlogAuthor", on_delete=models.PROTECT, related_name="+")

    class Meta(Orderable.Meta):
        verbose_name = "Blog Article Author"
        verbose_name_plural = "Blog Article Authors"

    panels = [
        FieldPanel("author"),
    ]

    def __str__(self):
        return f"{self.page.title} -> {self.author.name}"


class FreeFormPage2026(
    PageThemeMixin, PreFooterImageMixin, PromotedPageMixin, UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage
):
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
                *PageThemeMixin.theme_panels,
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

    def clean(self):
        super().clean()
        if self.theme == ENTERPRISE_THEME and self.show_pre_footer:
            raise ValidationError({"show_pre_footer": "Enterprise-themed pages cannot show the pre-footer section."})


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


class WhatsNewPage2026(PageThemeMixin, PreFooterImageMixin, UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
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

    content_panels = [
        FieldPanel("title"),
        FieldPanel("internal_title"),
        TitleFieldPanel("version", placeholder="123"),
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels + [
        MultiFieldPanel(
            [
                *PageThemeMixin.theme_panels,
            ],
            heading="Appearance",
        ),
        MultiFieldPanel(
            [
                *PreFooterImageMixin.pre_footer_image_panels,
                *QRCodeFloatingSnippetMixin.floating_qr_panels,
            ],
            heading="Snippets",
        ),
    ]

    override_translatable_fields = [
        *QRCodeFloatingSnippetMixin.override_translatable_fields,
        SynchronizedField("version"),
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


def cache_localized_tags(articles):
    """Populate _tags_cache on each article from a single BlogTag lookup, so rendering
    localized tag names costs one query rather than one per tag."""
    from springfield.cms.models.snippets import BlogTag  # circular import

    slugs = {tag.slug for article in articles for tag in article.tags.all()}
    localized_tags_by_slug = {tag.slug: tag for tag in BlogTag.objects.filter(slug__in=slugs, locale=SpringfieldLocale.get_active()).live()}
    for article in articles:
        article._tags_cache = [localized_tags_by_slug[tag.slug] for tag in article.tags.all() if tag.slug in localized_tags_by_slug]


MAX_HEADER_TOPICS = 8


def article_list_queryset(queryset):
    """Add everything the article list and card templates render to a BlogArticlePage
    queryset, so rendering does not fan out into a query per article."""
    return (
        queryset.select_related(
            "topic",
            "image",
            "image_dark_mode",
            "image_mobile",
            "image_dark_mode_mobile",
            "listing_image",
        )
        .prefetch_related(
            "tags",
            "image__renditions",
            "image_dark_mode__renditions",
            "image_mobile__renditions",
            "image_dark_mode_mobile__renditions",
            "listing_image__renditions",
        )
        .defer("content")
    )


def prefetch_article_blocks(values):
    """Bulk-fetch the BlogArticlePages referenced by a list of BlockArticleValues and
    populate _article_cache on each, so rendering does not issue a query per block.

    Topics and tags are swapped for their active-locale equivalents at the same time,
    because the referenced article is always the source-locale page."""
    # Inline import: snippets and pages import from each other at module scope.
    from springfield.cms.models.snippets import BlogTopic

    pks = [value["article"].pk for value in values if value.get("article")]
    if not pks:
        return

    articles_by_pk = {article.pk: article for article in article_list_queryset(BlogArticlePage.objects.filter(pk__in=pks))}
    cache_localized_tags(articles_by_pk.values())

    active_locale = SpringfieldLocale.get_active()
    localized_topics_by_slug = {topic.slug: topic for topic in BlogTopic.objects.filter(locale=active_locale).live()}

    for value in values:
        page = value.get("article")
        if page and page.pk in articles_by_pk:
            article = articles_by_pk[page.pk]
            if article.topic and article.topic.slug in localized_topics_by_slug:
                article._topic_cache = localized_topics_by_slug[article.topic.slug]
            value._article_cache = article


class BlogIndexPage(RoutablePageMixin, UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that lists blog posts."""

    subpage_types = ["cms.BlogArticlePage", "cms.BlogTopicPage"]
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
    featured_topics = StreamField(
        [("topic", LocalizedLiveSnippetChooserBlock("cms.BlogTopic"))],
        max_num=MAX_HEADER_TOPICS,
        use_json_field=True,
        null=True,
        blank=True,
        help_text=f"Up to {MAX_HEADER_TOPICS} topics shown at the top of the index page. If empty, the topics with the most articles are shown.",
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

    blog_options_panels = [
        FieldPanel("featured_topics"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(blog_options_panels, heading="Blog Options"),
            ObjectList(AbstractSpringfieldCMSPage.promote_panels, heading="Promote"),
            ObjectList(settings_panels, heading="Settings"),
        ]
    )

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

    def prefetch_streamfield_articles(self):
        """Prefetch every article referenced by this page's featured_articles and cards_lists."""
        # StreamField iteration yields BoundBlocks; their .value is BlockArticleValue.
        # ListBlock iteration yields StructValues (BlockArticleValue) directly.
        values = [block.value for block in (self.featured_articles or [])]
        for cards_list_block in self.cards_lists or []:
            values.extend(list(cards_list_block.value["articles"]))
        prefetch_article_blocks(values)

    def live_articles(self):
        """Published, publicly visible articles under this index."""
        return BlogArticlePage.objects.child_of(self).live().public()

    def get_all_topics(self):
        """Topics that have at least one live article here, most-populated first."""
        # Inline import: snippets and pages import from each other at module scope.
        from springfield.cms.models.snippets import BlogTopic

        return (
            BlogTopic.objects.filter(locale=self.locale, blog_articles__in=self.live_articles().values("pk"))
            .annotate(article_count=Count("blog_articles"))
            .live()
            .order_by("-article_count")
        )

    def get_topic_context(self, request, topic, topic_page=None):
        """Context for the topics/<slug>/ route, shared by the plain listing and by
        BlogTopicPage. Articles already shown in a curated header are dropped from the
        list before pagination, so the count matches what is rendered."""
        articles = article_list_queryset(self.live_articles()).filter(topic=topic)

        if topic_page:
            featured_values = [block.value for block in (topic_page.featured_articles or [])]
            prefetch_article_blocks(featured_values)
            featured_pks = [value["article"].pk for value in featured_values if value.get("article")]
            if featured_pks:
                articles = articles.exclude(pk__in=featured_pks)

        paginator = Paginator(articles.order_by("-first_published_at"), ARTICLES_PER_PAGE)
        topic.article_count = paginator.count
        list_articles = paginator.get_page(request.GET.get("page", 1))
        cache_localized_tags(list_articles.object_list)

        return {
            "blog_index": self,
            "topic": topic,
            "all_topics": self.get_all_topics(),
            "topic_page": topic_page,
            "list_articles": list_articles,
        }

    def get_header_topics(self):
        """Topics for the page header: the editor-selected featured topics, or the
        topics with the most articles when none are selected.
        """
        from springfield.cms.models.snippets import BlogTopic  # circular import

        selected_topics = [block.value for block in (self.featured_topics or []) if block.value]
        if not selected_topics:
            return list(self.get_all_topics()[:MAX_HEADER_TOPICS])

        localized_topics = BlogTopic.objects.filter(
            translation_key__in=[topic.translation_key for topic in selected_topics],
            locale_id=self.locale_id,
        ).live()
        localized_topics_by_key = {topic.translation_key: topic for topic in localized_topics}

        return [localized_topics_by_key[topic.translation_key] for topic in selected_topics if topic.translation_key in localized_topics_by_key]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        self.prefetch_streamfield_articles()
        context["all_topics"] = self.get_all_topics()
        context["header_topics"] = SimpleLazyObject(self.get_header_topics)
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

    @path("topics/<slug:topic_slug>/")
    def topic_route(self, request, topic_slug):
        # Inline import: snippets and pages import from each other at module scope.
        from springfield.cms.models.snippets import BlogTopic

        topic = BlogTopic.objects.filter(slug=topic_slug, locale=self.locale).live().first()
        if topic is None:
            raise Http404

        topic_page = BlogTopicPage.objects.child_of(self).live().public().filter(topic=topic).first()
        if topic_page:
            return topic_page.serve(request)

        return self._render_route(request, "cms/blog_topic_page.html", self.get_topic_context(request, topic))

    @path("all/")
    def all_route(self, request):
        # Inline import: snippets and pages import from each other at module scope.
        from springfield.cms.models.snippets import BlogTopic

        base_qs = article_list_queryset(self.live_articles())

        topic = None
        topic_slug = request.GET.get("topic")
        if topic_slug:
            topic = BlogTopic.objects.filter(slug=topic_slug, locale=self.locale).first()
            if topic:
                base_qs = base_qs.filter(topic=topic)

        list_articles_qs = base_qs.order_by("-first_published_at")
        paginator = Paginator(list_articles_qs, ARTICLES_PER_PAGE)

        if topic:
            topic.article_count = paginator.count
        list_articles = paginator.get_page(request.GET.get("page", 1))
        cache_localized_tags(list_articles.object_list)

        return self._render_route(
            request,
            "cms/blog_all_page.html",
            {
                "list_articles": list_articles,
                "topic": topic,
            },
        )

    def get_sitemap_urls(self, request=None):
        """Add the URLs this page serves through its routes, which have no Page of their own
        for the sitemap to find.
        """
        urls = super().get_sitemap_urls(request=request)
        page_entry = urls[0]
        if not page_entry["location"]:
            return urls

        route_paths = ["topics/", "all/", *(f"topics/{topic.slug}/" for topic in self.get_all_topics())]
        urls.extend(page_entry | {"location": f"{page_entry['location']}{route_path}"} for route_path in route_paths)
        return urls


class BlogTopicPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """An editor-curated header for one blog topic.

    Served by BlogIndexPage.topic_route at topics/<slug>/ in place of the plain topic
    heading. The automatic article list still renders below it."""

    parent_page_types = ["cms.BlogIndexPage"]
    subpage_types = []
    ftl_files = ["cms/blog"]

    topic = models.ForeignKey(
        "cms.BlogTopic",
        on_delete=models.PROTECT,
        related_name="topic_pages",
    )
    page_heading = StreamField(
        [("heading", HeadingBlock())],
        max_num=1,
        use_json_field=True,
        blank=True,
    )
    featured_articles = StreamField(
        [("article", BlogArticleBlock())],
        max_num=4,
        use_json_field=True,
        blank=True,
        help_text="Up to 4 featured articles shown at the top. These are left out of the list below.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("topic"),
        FieldPanel("page_heading"),
        FieldPanel("featured_articles"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    search_fields = AbstractSpringfieldCMSPage.search_fields + [
        index.SearchField("page_heading"),
    ]

    override_translatable_fields = [
        *AbstractSpringfieldCMSPage.override_translatable_fields,
    ]

    class Meta:
        verbose_name = "Blog Topic Page"
        verbose_name_plural = "Blog Topic Pages"

    def __str__(self):
        return f"BlogTopicPage: {self.title} - {self.locale}"

    def clean(self):
        """Reject a second page for a topic another page already covers.

        A clean() check rather than a database constraint: Wagtail's copy and translate
        flows create rows that a hard constraint would reject with an opaque
        IntegrityError."""
        super().clean()
        if self.topic_id is None:
            return
        duplicate = BlogTopicPage.objects.filter(topic_id=self.topic_id, locale_id=self.locale_id).exclude(pk=self.pk).first()
        if duplicate:
            raise ValidationError({"topic": f'"{duplicate.title}" already covers this topic.'})

    def get_url_parts(self, request=None):
        """Report the topics/<slug>/ route URL rather than this page's own tree path, so
        page.url, the canonical tag, the admin's view-live link and the sitemap all agree
        with where the page is actually served."""
        parent = self.get_parent()
        if parent is None or self.topic_id is None:
            return super().get_url_parts(request)
        parent_parts = parent.get_url_parts(request)
        if parent_parts is None:
            return super().get_url_parts(request)
        site_id, root_url, parent_path = parent_parts
        return (site_id, root_url, f"{parent_path}topics/{self.topic.slug}/")

    def route(self, request, path_components):
        """Refuse to serve at this page's own tree path, so topics/<slug>/ is the only URL
        for this content. BlogIndexPage.topic_route reaches it through serve(), and the
        admin previews it through serve_preview(); neither goes through route()."""
        raise Http404

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        blog_index = self.get_parent().specific
        context.update(blog_index.get_topic_context(request, self.topic, topic_page=self))
        return context

    def get_template(self, request, *args, **kwargs):
        return "cms/blog_topic_page.html"


class HeroStyle(models.TextChoices):
    STANDARD_IMAGE = "standard_image", "Standard image"
    LARGE_IMAGE = "large_image", "Large featured image"
    TEXT_ONLY = "text_only", "No image, text only"
    VIDEO = "video", "Featured video"


class BlogArticlePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays a single blog article."""

    parent_page_types = ["cms.BlogIndexPage"]
    ftl_files = ["cms/blog"]

    description = RichTextField(
        blank=True,
        features=HEADING_TEXT_FEATURES,
        help_text="A short description used on the index page.",
    )
    updated_date = models.DateField(
        null=True,
        blank=True,
        help_text="Shown as “Last updated on …”. Leave empty to show only the published date.",
    )
    hide_dates = models.BooleanField(
        default=False,
        help_text="Hide the published and updated dates on this article.",
    )
    hero_style = models.CharField(
        max_length=32,
        choices=HeroStyle,
        default=HeroStyle.STANDARD_IMAGE,
        help_text="Layout for the article header.",
    )
    hero_video = StreamField(
        [("video", VideoBlock())],
        max_num=1,
        use_json_field=True,
        null=True,
        blank=True,
        help_text="Video shown in the header when the hero style is “Featured video”.",
    )

    # Null so rows without a topic remain valid; blank stays False (the
    # default) so the Wagtail admin form still requires one.
    topic = models.ForeignKey(
        "cms.BlogTopic",
        null=True,
        on_delete=models.PROTECT,
        related_name="blog_articles",
    )
    tags = LocalizedClusterTaggableManager(through="cms.TaggedBlogArticle", blank=True)
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
    listing_image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Optional image for article cards and lists. Falls back to the featured image.",
    )
    content = StreamField(
        [
            ("text", RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL)),
            ("media", MediaBlock()),
            ("image_caption", ImageCaptionBlock()),
            ("code", CodeBlock()),
            ("quote", QuoteBlock()),
        ],
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("description"),
        MultiFieldPanel(
            [
                FieldPanel("topic"),
                FieldPanel("tags"),
            ],
            heading="Topic & Tags",
        ),
        InlinePanel("article_authors", label="Authors"),
        MultiFieldPanel(
            [
                FieldPanel("first_published_at"),
                FieldPanel("updated_date"),
                FieldPanel("hide_dates"),
            ],
            heading="Dates",
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
                FieldPanel("listing_image"),
            ],
            heading="Featured Image",
        ),
        MultiFieldPanel(
            [
                FieldPanel("hero_style"),
                FieldPanel("hero_video"),
            ],
            heading="Hero Options",
            classname="collapsed",
        ),
        FieldPanel("content"),
    ]

    settings_panels = AbstractSpringfieldCMSPage.settings_panels

    # Drops show_in_menus, unused by the CMS
    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
            ],
            heading="For search engines",
        ),
        FieldPanel("og_image"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(promote_panels, heading="Promote & SEO"),
            ObjectList(settings_panels, heading="Settings"),
        ]
    )

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

    def clean(self):
        """Reject a hero style whose asset is missing, keyed to the field the editor
        has to fill in."""
        super().clean()
        if self.hero_style in (HeroStyle.STANDARD_IMAGE, HeroStyle.LARGE_IMAGE) and not self.image_id:
            raise ValidationError({"image": "This hero style needs a featured image."})
        if self.hero_style == HeroStyle.VIDEO and not self.hero_video:
            raise ValidationError({"hero_video": "This hero style needs a video."})

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if self.topic_id:
            related = (
                BlogArticlePage.objects.sibling_of(self)
                .live()
                .public()
                .filter(topic=self.topic)
                .exclude(pk=self.pk)
                .prefetch_related("tags")
                .order_by("-first_published_at")[:4]
            )
            context["related_articles"] = list(related)
            cache_localized_tags(context["related_articles"])
        else:
            context["related_articles"] = []
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
            self._tags_cache = [localized for tag in self.tags.all() if (localized := tag.get_localized())]
        return self._tags_cache

    def get_authors(self):
        """The article's authors in editor order, localized where a live translation
        exists and falling back to the stored author otherwise. Authors that are not
        live in any usable locale are omitted."""
        if not hasattr(self, "_authors_cache"):
            self._authors_cache = [
                resolved
                for placement in self.article_authors.select_related("author")
                if (resolved := placement.author.get_localized() or (placement.author if placement.author.live else None))
            ]
        return self._authors_cache

    def get_listing_image(self):
        """The image for cards and list items. Fall back to the featured image."""
        return self.listing_image or self.image

    def get_listing_image_variants(self):
        """Dark and mobile variants for the listing image. Only available for the featured image."""
        if self.listing_image_id:
            return SimpleNamespace(dark_mode=None, mobile=None, dark_mode_mobile=None)
        return SimpleNamespace(
            dark_mode=self.image_dark_mode,
            mobile=self.image_mobile,
            dark_mode_mobile=self.image_dark_mode_mobile,
        )


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


BASKET_CONTACT_ENTERPRISE_PATH = "/api/v1/contact/enterprise/"

# The form field identifiers each basket endpoint accepts, mirroring basket's request schemas.
# Basket's honeypot fields are deliberately absent: the contact page renders its own honeypot
# outside form_fields, so those fields are never part of the submitted payload.
BASKET_ENDPOINT_FIELDS = {
    BASKET_CONTACT_ENTERPRISE_PATH: {
        "required": {
            "first_name",
            "last_name",
            "company",
            "job_title",
            "business_email",
            "country",
            "firefox_use_stage",
            "deployment_size",
            "support_needs",
            "timeline",
        },
        "optional": {
            "business_phone",
            "company_size",
            "opt_in",
            "lead_source",
            "cta",
            "message",
        },
    },
}

BASKET_API_PATH_CHOICES = [(path, path) for path in BASKET_ENDPOINT_FIELDS]


class ContactPageForm(WagtailAdminPageForm):
    """Admin form for ContactPage that validates the allowed slug only when publishing.

    The slug check is publish-only (rather than in the model's clean()) so drafts
    can be saved with any slug.
    """

    def clean(self):
        cleaned_data = super().clean()

        # `action-publish` is present in the POST data when the editor clicks
        # "Publish". Draft saves and "Submit for moderation" omit it, so they
        # skip this check.
        is_publishing = "action-publish" in self.data
        slug = cleaned_data.get("slug")
        if is_publishing and slug and settings.PROD:
            parent = self.parent_page or self.instance.get_parent()
            path = parent.url_path + slug + "/" if parent else "/" + slug + "/"
            # Using .search() instead of .match() because paths will often start with /home/parent/child/
            if not any(re.search(allowed_path, path) for allowed_path in settings.CONTACT_PAGE_ALLOWED_PATHS):
                self.add_error("slug", f"Slug must match one of the allowed paths: {', '.join(settings.CONTACT_PAGE_ALLOWED_PATHS)}")

        return cleaned_data


class ContactPage(PageThemeMixin, AbstractSpringfieldCMSPage):
    """A CMS-editable contact form page with a configurable StreamField form builder."""

    base_form_class = ContactPageForm

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
        choices=BASKET_API_PATH_CHOICES,
        help_text="Basket endpoint the form posts to. Required if Email Address is unset. Form fields must match what it accepts.",
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
                *PageThemeMixin.theme_panels,
            ],
            heading="Appearance",
        ),
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
            allowed_fields = BASKET_ENDPOINT_FIELDS.get(self.basket_api_path)
            if allowed_fields is None:
                errors["basket_api_path"] = f"{self.basket_api_path} is not a basket endpoint."
            else:
                identifiers = {field.value["internal_identifier"] for field in self.form_fields}
                optional_identifiers = {field.value["internal_identifier"] for field in self.form_fields if not field.value["required"]}
                unaccepted = identifiers - allowed_fields["required"] - allowed_fields["optional"]
                missing = allowed_fields["required"] - identifiers
                not_marked_required = allowed_fields["required"] & optional_identifiers
                field_errors = []
                if unaccepted:
                    field_errors.append(f"{self.basket_api_path} does not accept these fields: {', '.join(sorted(unaccepted))}.")
                if missing:
                    field_errors.append(f"{self.basket_api_path} requires these fields: {', '.join(sorted(missing))}.")
                if not_marked_required:
                    field_errors.append(
                        f"{self.basket_api_path} requires these fields to be marked as required: {', '.join(sorted(not_marked_required))}."
                    )
                if field_errors:
                    errors["form_fields"] = field_errors

        if not self.redirect_to and not self.thank_you_message:
            msg = "Set either a redirect page or a thank you message."
            errors["redirect_to"] = msg
            errors["thank_you_message"] = msg

        if errors:
            raise ValidationError(errors)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["form"] = getattr(request, "form", None)
        if getattr(request, "form_success", False):
            context["form_success"] = True
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

    def serve_preview(self, request, mode_name):
        request.form = self.get_form(request)
        return super().serve_preview(request, mode_name)

    def get_form(self, request):
        """Return a Django Form instance generated from the form_fields StreamField.

        Bound to ``request.POST`` for POST requests, unbound otherwise.
        """
        locale = self.locale.language_code
        form_fields = {}
        for field in self.form_fields:
            value = field.value
            form_field = value.get_form_field(locale=locale)
            if field.block_type == "hidden_field":
                override_param = value["query_param_override"]
                if override_param and (override := request.GET.get(override_param)):
                    form_field.initial = override
            form_fields[value["internal_identifier"]] = form_field

        # Hidden fields always arrive in POST, they must not be considered when checking for an empty submission.
        hidden_identifiers = {field.value["internal_identifier"] for field in self.form_fields if field.block_type == "hidden_field"}
        visible_identifiers = {field.value["internal_identifier"] for field in self.form_fields if field.block_type != "hidden_field"}

        class ContactForm(forms.Form):
            def __init__(_self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                _self.fields.update(form_fields)

            def clean(_self):
                # The honeypot must stay empty, and every hidden field must have a value
                honeypot = _self.data.get("office_fax")
                empty_hidden_fields = any(not _self.data.get(identifier) for identifier in hidden_identifiers)
                if honeypot or empty_hidden_fields:
                    raise forms.ValidationError(ftl_lazy("contact-form-error-sending", ftl_files=self.ftl_files))
                # Only flag an empty submission when no per-field error already exists
                has_any_data = any(_self.cleaned_data.get(identifier) for identifier in visible_identifiers)
                if not has_any_data and not _self.errors:
                    raise forms.ValidationError(ftl_lazy("contact-form-error-empty", ftl_files=self.ftl_files))
                return _self.cleaned_data

        # auto_id="%s" keeps the rendered ids equal to the author-defined internal identifiers
        # instead of Django's "id_" prefixed defaults.
        if request.method == "POST":
            return ContactForm(request.POST, auto_id="%s")
        return ContactForm(auto_id="%s")

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


def referral_geo_check(serve_method):
    """Redirect visitors outside the relevant area for the referral program to the homepage"""

    @functools.wraps(serve_method)
    def wrapper(self, request, *args, **kwargs):
        country = get_country_from_request(request)
        if country not in settings.FF_REFERRAL_COUNTRY_CODES:
            if locale := getattr(request, "locale"):
                return redirect(f"/{locale}/")
            else:
                return redirect("/")
        return serve_method(self, request, *args, **kwargs)

    return wrapper


class ReferralHubPage(AbstractSpringfieldCMSPage):
    """Page where a user gets their invitation link and
    can monitor their invites' impact (an anonymous install count)
    """

    parent_page_types = ["cms.HomePage"]
    template = "cms/referral_hub_page.html"

    upper_content = StreamField(
        [
            ("showcase", ShowcaseBlock(allow_tabs=True)),
        ],
        max_num=1,
        null=True,
        blank=True,
        use_json_field=True,
    )
    lower_content = StreamField(
        [
            ("intro", IntroBlock()),
            ("cards_list", CardsListBlock(template="cms/blocks/sections/cards-list-section.html", max_buttons=5)),
            ("kit_banner", KitBannerBlock()),
        ],
        null=True,
        blank=True,
        use_json_field=True,
    )
    extra_content = StreamField(
        [
            ("showcase", ShowcaseBlock(allow_tabs=True)),
        ],
        max_num=1,
        null=True,
        blank=True,
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("lower_content"),
        FieldPanel("extra_content"),
    ]

    class Meta:
        verbose_name = "Referral Program: Referral Hub Page"

    def get_context(self, request, *args, **kwargs):
        """
        Adds an invite_url to the context using the referral-hub ID
        ("ref_key") in the URL that opens this Referral Hub page.
        If ref_key is missing or invalid, invite_url is empty.

        The invite_url is the one that can be copied and sent to friends
        and can be turned into a QR code as needed, etc.

        install_count is the number of installs credited to this ref_key. It
        drives the achieved/locked state of the impact dashboard's badges.
        """

        context = super().get_context(request, *args, **kwargs)

        # The defaults stand for every case where there is no usable `ref_key`:
        # no invite link to offer and no progress to report.
        context["invite_url"] = ""
        context["install_count"] = 0

        referral_id = request.GET.get("ref_key", "")
        try:
            # Validates as well as encrypts -- `referral_id_to_invite_code`
            # runs the same `validate_referral_id` that `serve()` does, so a
            # missing or malformed value lands in the `except` below.
            invite_code = crypto.referral_id_to_invite_code(referral_id)
            context["invite_url"] = crypto.invite_url_for_code(invite_code)
        except ValueError:
            # Left at the defaults rather than raising, and deliberately not
            # reported. `serve()` is what rejects and reports a public request
            # without a usable `ref_key`, so nothing from the referral flow can
            # reach this point. What can reach it are the callers that skip
            # `serve()` -- CMS preview, and Wagtail's
            # `serve_password_required_response`, which calls `get_context`
            # directly -- and a bad value from those is not a signal.
            return context

        context["install_count"] = self._get_install_count(referral_id)

        return context

    def _get_install_count(self, referral_id: str) -> int:
        """Installs credited to this ref_key, or 0 if it cannot be determined.

        Returns 0 rather than raising for every failure mode -- an unknown
        ref_key, or the referral table being unavailable -- because the impact
        dashboard is one optional part of this page and must not be able to fail
        the whole hub render.

        Note this collapses "we don't know" and "you genuinely have 0 installs"
        into the same value. If the design ever needs to distinguish them (e.g.
        "we couldn't load your progress"), this should return None instead.
        """
        if not referral_id:
            return 0

        try:
            return FirefoxReferralData.objects.get(referral_id=referral_id).install_count
        except FirefoxReferralData.DoesNotExist:
            return 0
        except DatabaseError as exc:
            with new_scope() as scope:
                scope.set_extra("exception", str(exc))
                capture_message("Failed to read FirefoxReferralData install count", level="error")
                return 0

    @referral_geo_check
    def serve(self, request, *args, **kwargs):
        """Require a well-formed ref_key

        The hub is meaningless without a referral ID -- there is no invite link to
        copy and no progress to show -- so a URL missing that part is treated as
        not found rather than served empty. This is the only place that rejects,
        and the only place a bad `ref_key` is reported, because it is the only
        one every public request passes through. `serve_preview()` renders the
        page without coming through here, so CMS preview is unaffected and still
        shows an empty invite URL.
        """
        ref_key = request.GET.get("ref_key", "")
        try:
            # The referral ID arrives already-canonical from Firefox, so this is
            # deliberately strict: exactly REFERRAL_ID_LENGTH characters of
            # uppercase Crockford base32, with no case- or glyph-folding.
            validate_referral_id(ref_key)
        except ValueError:
            # Only a correctly sized `ref_key` is reported, because this is a
            # public page and anything can land in the query string. At the right
            # length it plausibly came from the referral flow, so a spike is worth
            # seeing. The value itself is masked out of the event by
            # `SENSITIVE_FIELDS_TO_MASK_ENTIRELY`.
            if len(ref_key) == REFERRAL_ID_LENGTH:
                with new_scope() as scope:
                    scope.fingerprint = ["referral-hub-invalid-ref-key"]
                    capture_message(
                        "ReferralHubPage received a ref_key that is not a valid referral ID",
                        level="warning",
                    )
            # Without this, CMSLocaleFallbackMiddleware would see the 404, find
            # this very page live at the same path, and redirect to it forever.
            mark_locale_fallback_exempt(request)
            raise Http404("Referral Hub URL is missing a well-formed ref_key") from None

        response = super().serve(request, *args, **kwargs)
        return response


class ReferralGetFirefoxPage(AbstractSpringfieldCMSPage):
    """Landing page for an invitee, from which they can download Firefox.

    Will use custom, privacy-respecting attribution so we can tally up
    how many people install via the invite code used to open this page.

    A visitor arriving without a usable invitation, or from outside the
    applicable geographic territory, is not served this page.
    """

    parent_page_types = ["cms.HomePage"]
    template = "cms/referral_get_firefox_page.html"

    upper_content = StreamField(
        [
            ("intro", KitIntroBlock(allow_referral_download=True)),
            ("showcase", ShowcaseBlock(allow_tabs=True)),
            ("cards_list", CardsListBlock(template="cms/blocks/sections/cards-list-section.html")),
            ("carousel", CarouselBlock()),
        ],
        null=True,
        blank=True,
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
        verbose_name = "Referral Program: Invitee / Get Firefox Page"

    def clean(self):
        super().clean()
        count = sum(
            1
            for block in (self.upper_content or [])
            if block.block_type == "intro"
            for btn in block.value.get("buttons", [])
            if btn.block_type == "referral_download"
        )
        if count > 1:
            raise ValidationError({"upper_content": "Only one Referral Download CTA block is allowed per page. Remove the duplicate before saving."})

    def get_context(self, request, *args, **kwargs):
        """
        Adds an `invitation_code` code (from the URL) to the context, which is
        carried as `fxrefer<invitation code>` in utm_content by the referral
        attribution JS.

        Also adds `utm_parameters` with the referral campaign so that the
        download-firefox-button component builds an attributed Android Play Store
        URL for the server-rendered badge (the JS checkbox module further modifies
        this href when toggled).
        """
        context = super().get_context(request, *args, **kwargs)

        # self.serve() already validated that the invitation code is legit and valid
        context["invitation_code"] = request.GET.get("invitation")
        # Provide the referral utm_campaign so play_store_url() includes a referrer
        # on the server-rendered Android badge. Must match REFERRAL_CAMPAIGN in
        # media/js/firefox/referral/referral-attribution.es6.js.
        context["utm_parameters"] = {
            "utm_source": "www.firefox.com",
            "utm_medium": "referral",
            "utm_campaign": "firefox-referral",
        }

        # QA-only override: forces the download CTA to Nightly instead of Release. See WT-1281.
        context["channel"] = "nightly" if switch("REFERRAL_FORCE_NIGHTLY_QA") else "release"
        return context

    @referral_geo_check
    def serve(self, request, *args, **kwargs):
        invite_code = request.GET.get("invitation")
        if not invite_code:
            mark_locale_fallback_exempt(request)
            raise Http404("Referral invitee page is missing an invitation code") from None

        try:
            # verify syntax and decryptability of the invitation code
            crypto.invite_code_to_referral_id(invite_code)
        except ValueError:
            mark_locale_fallback_exempt(request)
            raise Http404("Referral invitee page did not get a well-formed invitation code") from None

        return super().serve(request, *args, **kwargs)
