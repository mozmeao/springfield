# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.expressions import Case, F, Value, When
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

from wagtail.admin.panels import FieldPanel, FieldRowPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.blocks import RichTextBlock
from wagtail.fields import RichTextField
from wagtail.models import Page as WagtailBasePage
from wagtail_localize.fields import SynchronizedField
from wagtail_thumbnail_choice_block import ThumbnailRadioSelect

from lib.l10n_utils.fluent import ftl
from springfield.base.geo import get_country_from_request
from springfield.cms.blocks import (
    HEADING_TEXT_FEATURES,
    ICON_CHOICES,
    UI_TOUR_CLASSES,
    UITOUR_BUTTON_SMART_WINDOW,
    BannerBlock,
    CardGalleryBlock,
    CardsListBlock2026,
    CarouselBlock,
    DownloadSupportBlock,
    HomeKitBannerBlock,
    InlineNotificationBlock,
    IntroBlock,
    IntroBlock2026,
    KitBannerBlock,
    KitIntroBlock,
    LineCardsBlock,
    LocalizedLiveSnippetChooserBlock,
    MediaContentBlock,
    MobileStoreQRCodeBlock,
    NotificationBlock,
    RelatedArticlesListBlock,
    SectionBlock,
    SectionBlock2026,
    ShowcaseBlock,
    SlidingCarouselBlock,
    SubscriptionBlock,
    TopicListBlock,
    VideoBlock,
    validate_animation_url,
)
from springfield.cms.fields import StreamField

from .base import AbstractSpringfieldCMSPage, PromotedPageMixin

if TYPE_CHECKING:
    from springfield.cms.models import Tag


BASE_UTM_PARAMETERS = {
    "utm_source": "www.firefox.com",
    "utm_medium": "referral",
}


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
            ("cards_list", CardsListBlock2026(template="cms/blocks/sections/cards-list-section.html")),
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
    ]

    class Meta:
        verbose_name = "Home Page"
        verbose_name_plural = "Home Pages"

    def __str__(self):
        return f"HomePage: {self.title} - {self.locale}"


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
            ("section", SectionBlock2026()),
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
            ("section", SectionBlock2026(allow_uitour=False)),
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
            return "cms/thanks_page__direct.html"

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

    def __str__(self):
        return f"ArticleIndexPage: {self.title} - {self.locale}"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)

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
    ]

    if TYPE_CHECKING:
        tag: Tag | None

    def __str__(self):
        return f"ArticleDetailPage: {self.title} - {self.locale}"

    def get_tag(self) -> Tag | None:
        if self.tag:
            return self.tag.get_localized()
        return None


class ArticleThemePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays articles related to a specific theme."""

    upper_content = StreamField(
        [
            ("intro", IntroBlock2026()),
        ],
        use_json_field=True,
        blank=True,
        null=True,
    )

    content = StreamField(
        [
            ("intro", IntroBlock2026()),
            ("section", SectionBlock2026(require_heading=False)),
        ],
        use_json_field=True,
        default=list(),
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    def __str__(self):
        return f"ArticleThemePage: {self.title} - {self.locale}"


def _get_freeform_page_blocks(allow_uitour=False):
    """Factory function to create block list with appropriate button types.

    Args:
        allow_uitour: If True, allows both regular buttons and UI Tour buttons in blocks.
                      If False, only allows regular buttons.

    Returns:
        List of tuples containing block names and instances configured
        with the appropriate button types.
    """
    return [
        ("inline_notification", InlineNotificationBlock(group="Notifications")),
        ("intro", IntroBlock(allow_uitour=allow_uitour)),
        ("section", SectionBlock(allow_uitour=allow_uitour)),
        ("subscription", SubscriptionBlock(group="Banners")),
        ("banner", BannerBlock(allow_uitour=allow_uitour, group="Banners")),
        ("kit_banner", KitBannerBlock(allow_uitour=allow_uitour, group="Banners")),
    ]


def _get_freeform_page_blocks_2026(allow_uitour=True, allow_kit_intro=False):
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
        ("intro", IntroBlock2026(allow_uitour=allow_uitour, group="Intro")),
        ("section", SectionBlock2026(allow_uitour=allow_uitour, group="Main")),
        ("showcase", ShowcaseBlock(group="Media")),
        ("carousel", CarouselBlock(group="Media")),
        ("sliding_carousel", SlidingCarouselBlock(group="Media")),
        ("card_gallery", CardGalleryBlock(group="Media")),
        ("media_content", MediaContentBlock(group="Media", is_2026=True, template="cms/blocks/sections/media-content-section.html")),
        ("cards_list", CardsListBlock2026(template="cms/blocks/sections/cards-list-section.html", allow_uitour=allow_uitour, group="Main")),
        ("mobile_store_qr_code", MobileStoreQRCodeBlock(group="Media")),
        ("banner", BannerBlock(allow_uitour=allow_uitour, group="Banners")),
        ("topic_list", TopicListBlock(allow_uitour=allow_uitour, group="Main")),
        ("line_cards", LineCardsBlock(allow_uitour=allow_uitour, template="cms/blocks/sections/line-cards-section.html", group="Main")),
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


FREEFORM_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=False)
WHATS_NEW_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=True)
UPPER_FREEFORM_PAGE_BLOCKS_2026 = _get_freeform_page_blocks_2026(allow_uitour=True, allow_kit_intro=True)
LOWER_FREEFORM_PAGE_BLOCKS_2026 = _get_freeform_page_blocks_2026(allow_uitour=True, allow_kit_intro=False)


class FreeFormPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A flexible page type that allows a variety of content blocks to be added."""

    content = StreamField(FREEFORM_PAGE_BLOCKS, use_json_field=True)

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
    ]

    def __str__(self):
        return f"FreeFormPage: {self.title} - {self.locale}"


class FreeFormPage2026(PromotedPageMixin, UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
    """A flexible 2026 page type with optional upper/lower split layout."""

    upper_content = StreamField(
        UPPER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Optional upper content. If present, the page will use a split layout.",
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
        blank=True,
        null=True,
    )
    show_pre_footer = models.BooleanField(
        default=True,
        help_text="If true, the page will display the default pre-footer section.",
    )
    show_nav_cta = models.BooleanField(
        default=True,
        help_text="If true, the download button will appear in the navigation bar for this page.",
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
        FieldPanel("show_pre_footer"),
        FieldPanel("show_nav_cta"),
        *QRCodeFloatingSnippetMixin.floating_qr_panels,
    ]

    promote_panels = AbstractSpringfieldCMSPage.promote_panels + [
        FieldPanel("enable_marketing_attribution"),
    ]

    class Meta:
        verbose_name = "Free Form 2026 Page"
        verbose_name_plural = "Free Form 2026 Pages"

    def __str__(self):
        return f"FreeFormPage2026: {self.title} - {self.locale}"

    @property
    def noindex(self):
        return self.enable_marketing_attribution


class WhatsNewIndexPage(AbstractSpringfieldCMSPage):
    """Index page for the Whats New pages that redirect to the latest version's What's New Page."""

    # Empty parent page types will prevent this page from being created from the Wagtail admin
    # Only one instance of this page should exist
    # When a HomePage is implemented, this page should be moved to be a child of HomePage
    # parent_page_types = []
    subpage_types = ["cms.WhatsNewPage", "cms.WhatsNewPage2026"]

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
            .annotate(
                version=Case(
                    When(whatsnewpage__version__isnull=False, then=F("whatsnewpage__version")),
                    When(whatsnewpage2026__version__isnull=False, then=F("whatsnewpage2026__version")),
                    default=Value(None),
                    output_field=models.CharField(),
                )
            )
            .order_by("-version")
            .specific()
            .first()
        )
        if latest_whats_new:
            return redirect(request.build_absolute_uri(latest_whats_new.get_url()))
        return redirect("/")


class WhatsNewPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays the latest Firefox updates and changes."""

    parent_page_types = ["cms.WhatsNewIndexPage"]
    subpage_types = []

    ftl_files = ["firefox/whatsnew/evergreen"]

    version = models.CharField(
        max_length=10,
        help_text="The version of Firefox this What's New page refers to, or 'general' for a non-version-specific page.",
    )
    content = StreamField(WHATS_NEW_PAGE_BLOCKS, use_json_field=True)
    show_qr_code_snippet = models.BooleanField(
        default=False,
        help_text="If true, a floating QR code snippet will be displayed on the page.",
    )

    content_panels = [
        FieldPanel("title"),
        TitleFieldPanel("version", placeholder="123"),
        FieldPanel("content"),
        FieldPanel("show_qr_code_snippet"),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["version"]),
        ]
        verbose_name = "What's New Page"
        verbose_name_plural = "What's New Pages"

    def __str__(self):
        return f"WhatsNewPage: {self.title} - {self.locale}"

    def get_utm_campaign(self):
        return self.get_stub_attribution_utm_campaign() or f"whatsnew-{self.version}"

    @property
    def noindex(self):
        return True


class WhatsNewPage2026(UTMParamsMixin, QRCodeFloatingSnippetMixin, AbstractSpringfieldCMSPage):
    """A 2026 version of the What's New page with optional upper/lower split layout."""

    parent_page_types = ["cms.WhatsNewIndexPage"]
    subpage_types = []

    ftl_files = ["firefox/whatsnew/evergreen"]

    version = models.CharField(
        max_length=10,
        help_text="The version of Firefox this What's New page refers to, or 'general' for a non-version-specific page.",
    )
    upper_content = StreamField(
        UPPER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
        blank=True,
        null=True,
        help_text="Optional upper content. If present, the page will use a split layout.",
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
    )
    content_panels = [
        FieldPanel("title"),
        TitleFieldPanel("version", placeholder="123"),
        FieldPanel("upper_content"),
        FieldPanel("content"),
        *QRCodeFloatingSnippetMixin.floating_qr_panels,
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

    ALLOWED_TERRITORIES = {"US", "CA"}
    ALLOWED_TERRITORIES_OPTION = "allowed_territories"
    ALLOWED_TERRITORIES_LABEL = "US and Canada only"

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
        LOWER_FREEFORM_PAGE_BLOCKS_2026,
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
        LOWER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
    )
    content = StreamField(
        LOWER_FREEFORM_PAGE_BLOCKS_2026,
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("upper_content"),
        FieldPanel("content"),
    ]

    class Meta:
        verbose_name = "Smart Window Explainer Page"
        verbose_name_plural = "Smart Window Explainer Pages"

    def __str__(self):
        return f"SmartWindowExplainerPage: {self.title} - {self.locale}"
