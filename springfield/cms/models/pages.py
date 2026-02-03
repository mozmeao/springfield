# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models
from django.shortcuts import redirect

from wagtail.admin.panels import FieldPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.blocks import RichTextBlock
from wagtail.fields import RichTextField
from wagtail.models import Page as WagtailBasePage
from wagtail.snippets.blocks import SnippetChooserBlock

from lib.l10n_utils.fluent import ftl
from springfield.cms.blocks import (
    HEADING_TEXT_FEATURES,
    ArticleItemBlock,
    BannerBlock,
    CardGalleryBlock,
    CardsListBlock2026,
    FeaturedArticleBlock,
    HomeCarouselBlock,
    HomeIntroBlock,
    HomeKitBannerBlock,
    InlineNotificationBlock,
    IntroBlock,
    KitBannerBlock,
    SectionBlock,
    SectionBlock2026,
    ShowcaseBlock,
    SubscriptionBlock,
)
from springfield.cms.fields import StreamField

from .base import AbstractSpringfieldCMSPage

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


class UTMParamsMixin:
    def get_utm_campaign(self):
        return self.slug

    def get_utm_parameters(self):
        return {
            **BASE_UTM_PARAMETERS,
            "utm_campaign": self.get_utm_campaign(),
        }

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["utm_parameters"] = self.get_utm_parameters()
        return context


class HomePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    upper_content = StreamField(
        [
            ("intro", HomeIntroBlock()),
            ("cards_list", CardsListBlock2026(template="cms/blocks/sections/cards-list-section.html")),
            ("carousel", HomeCarouselBlock()),
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


class DownloadPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    ftl_files = ["firefox/download/download"]

    PLATFORM_CHOICES = (
        ("windows", ftl("platform-windows", ftl_files=["firefox/download/download"])),
        ("mac", ftl("platform-macos", ftl_files=["firefox/download/download"])),
        ("linux", ftl("platform-linux", ftl_files=["firefox/download/download"])),
        ("android", ftl("platform-android", ftl_files=["firefox/download/download"])),
        ("ios", ftl("platform-ios", ftl_files=["firefox/download/download"])),
        ("chromebook", ftl("platform-chromebook", ftl_files=["firefox/download/download"])),
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
    content = StreamField(
        [
            ("section", SectionBlock2026()),
            (
                "banner_snippet",
                SnippetChooserBlock(
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
    pre_footer = StreamField(
        [
            (
                "pre_footer_cta_form_snippet",
                SnippetChooserBlock(
                    target_model="cms.PreFooterCTAFormSnippet",
                    template="cms/snippets/pre-footer-cta-form-snippet.html",
                    label="Pre-Footer CTA Form Snippet",
                ),
            )
        ],
        use_json_field=True,
        min_num=0,
        max_num=1,
        null=True,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("platform"),
        FieldPanel("subheading"),
        FieldPanel("intro_footer_text"),
        FieldPanel("featured_image"),
        FieldPanel("content"),
        FieldPanel("pre_footer"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["platforms"] = self.PLATFORM_CHOICES
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

    class Meta:
        verbose_name = "Download Page"
        verbose_name_plural = "Download Pages"


class ThanksPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A thank you page displayed after the user downloads Firefox."""

    content = StreamField(
        [
            ("section", SectionBlock2026(allow_uitour=False)),
            (
                "banner_snippet",
                SnippetChooserBlock(
                    target_model="cms.BannerSnippet",
                    template="cms/snippets/banner-snippet.html",
                    label="Banner Snippet",
                ),
            ),
        ]
    )
    pre_footer = StreamField(
        [
            (
                "pre_footer_cta_form_snippet",
                SnippetChooserBlock(
                    target_model="cms.PreFooterCTAFormSnippet",
                    template="cms/snippets/pre-footer-cta-form-snippet.html",
                    label="Pre-Footer CTA Form Snippet",
                ),
            )
        ],
        use_json_field=True,
        min_num=0,
        max_num=1,
        null=True,
        blank=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
        FieldPanel("pre_footer"),
    ]


class ArticleIndexPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    subpage_types = ["cms.ArticleDetailPage", "cms.ArticleThemePage"]

    sub_title = models.CharField(
        max_length=255,
        blank=True,
    )
    other_articles_heading = RichTextField(features=HEADING_TEXT_FEATURES)
    other_articles_subheading = RichTextField(features=HEADING_TEXT_FEATURES, blank=True)

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("sub_title"),
        FieldPanel("other_articles_heading"),
        FieldPanel("other_articles_subheading"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)

        all_articles = [
            page.specific
            for page in self.get_children().live().public().order_by("-first_published_at")
            if isinstance(page.specific, ArticleDetailPage)
        ]

        featured_articles = [page for page in all_articles if isinstance(page, ArticleDetailPage) and page.featured]
        list_articles = [page for page in all_articles if isinstance(page, ArticleDetailPage) and not page.featured]

        context["featured_articles"] = featured_articles
        context["list_articles"] = list_articles
        context["tags"] = {article.tag.slug: article.tag.name for article in all_articles if article.tag}
        return context


class ArticleDetailPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    parent_page_types = ["cms.ArticleIndexPage"]

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
    icon = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="An icon used for listing articles on the index page.",
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
    content = StreamField(
        [
            ("text", RichTextBlock(features=settings.WAGTAIL_RICHTEXT_FEATURES_FULL)),
        ],
        use_json_field=True,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("featured"),
                FieldPanel("tag"),
                FieldPanel("featured_image"),
                FieldPanel("icon"),
                FieldPanel("link_text"),
                FieldPanel("description"),
            ],
            heading="Index Page Settings",
        ),
        FieldPanel("image"),
        FieldPanel("content"),
    ]


class ArticleThemePage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays articles related to a specific theme."""

    heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
    )
    subheading = RichTextField(
        features=HEADING_TEXT_FEATURES,
        blank=True,
    )
    featured_articles = StreamField(
        [
            ("article", FeaturedArticleBlock()),
        ],
        use_json_field=True,
        min_num=2,
        max_num=4,
    )
    other_articles_heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
    )
    other_articles_subheading = RichTextField(
        features=HEADING_TEXT_FEATURES,
        blank=True,
    )
    other_articles = StreamField(
        [
            ("article", ArticleItemBlock()),
        ],
        use_json_field=True,
        min_num=2,
    )

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("heading"),
                FieldPanel("subheading"),
                FieldPanel("featured_articles"),
            ],
            heading="Featured Articles Section",
        ),
        MultiFieldPanel(
            [
                FieldPanel("other_articles_heading"),
                FieldPanel("other_articles_subheading"),
                FieldPanel("other_articles"),
            ],
            heading="Other Articles Section",
        ),
    ]


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


FREEFORM_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=False)
WHATS_NEW_PAGE_BLOCKS = _get_freeform_page_blocks(allow_uitour=True)


class FreeFormPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A flexible page type that allows a variety of content blocks to be added."""

    content = StreamField(FREEFORM_PAGE_BLOCKS, use_json_field=True)

    content_panels = AbstractSpringfieldCMSPage.content_panels + [
        FieldPanel("content"),
    ]


class WhatsNewIndexPage(AbstractSpringfieldCMSPage):
    """Index page for the Whats New pages that redirect to the latest version's What's New Page."""

    # Empty parent page types will prevent this page from being created from the Wagtail admin
    # Only one instance of this page should exist
    # When a HomePage is implemented, this page should be moved to be a child of HomePage
    # parent_page_types = []
    subpage_types = ["cms.WhatsNewPage"]

    class Meta:
        verbose_name = "What's New Index Page"
        verbose_name_plural = "What's New Index Pages"

    def serve(self, request):
        latest_whats_new = self.get_children().live().public().order_by("-whatsnewpage__version").first()
        if latest_whats_new:
            return redirect(request.build_absolute_uri(latest_whats_new.get_url()))
        else:
            return redirect("/")


class WhatsNewPage(UTMParamsMixin, AbstractSpringfieldCMSPage):
    """A page that displays the latest Firefox updates and changes."""

    parent_page_types = ["cms.WhatsNewIndexPage"]
    subpage_types = []

    ftl_files = ["firefox/whatsnew/evergreen"]

    version = models.CharField(
        max_length=10,
        help_text="The version of Firefox this What's New page refers to.",
    )
    content = StreamField(WHATS_NEW_PAGE_BLOCKS, use_json_field=True)

    content_panels = [
        FieldPanel("title"),
        TitleFieldPanel("version", placeholder="123"),
        FieldPanel("content"),
    ]

    class Meta:
        indexes = [
            models.Index(fields=["version"]),
        ]
        verbose_name = "What's New Page"
        verbose_name_plural = "What's New Pages"

    def get_utm_campaign(self):
        return f"whatsnew-{self.version}"
