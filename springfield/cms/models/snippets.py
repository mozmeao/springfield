# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

if TYPE_CHECKING:
    from django.http import HttpRequest

    from springfield.cms.models.pages import QRCodeFloatingSnippetMixin

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.utils.functional import cached_property

from wagtail.admin.panels import FieldPanel, HelpPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail_localize.fields import SynchronizedField

from lib.l10n_utils import fluent_l10n, get_locale
from springfield.cms.blocks import (
    EXPANDED_TEXT_FEATURES,
    HEADING_TEXT_FEATURES,
    ButtonBlock,
    ConditionalDisplayBlock,
    MixedButtonsBlock,
    NavFolderBlock,
    SpringfieldLinkBlock,
    TopLevelLinkBlock,
    get_button_types,
)
from springfield.cms.fields import StreamField
from springfield.cms.models.base import QROpenBehavior
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.rich_text import RichTextField
from springfield.cms.templatetags.cms_tags import remove_tags


class FluentPreviewableMixin(PreviewableMixin):
    """
    A PreviewableMixin that renders templates with localized Fluent strings.
    """

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        locale = get_locale(request)
        context["fluent_l10n"] = fluent_l10n([locale, "en"], settings.FLUENT_DEFAULT_FILES)
        context["is_preview"] = True
        return context


class BaseDraftQueryset(models.QuerySet):
    def live(self):
        return self.filter(live=True)

    def not_live(self):
        return self.filter(live=False)


class BaseDraftTranslatableSnippetMixin(TranslatableMixin, DraftStateMixin, RevisionMixin):
    """A base mixin for snippets that are translatable and have draft state and revision history."""

    objects = BaseDraftQueryset.as_manager()

    class Meta(TranslatableMixin.Meta, DraftStateMixin.Meta, RevisionMixin.Meta):
        abstract = True

    @cached_property
    def active_locale(self):
        return SpringfieldLocale.get_active()

    def get_localized(self):
        """Get the localized instance of this snippet for the active locale or for the fallback locale,
        or None if not available in the active locale."""
        localized = self.localized

        active_lang_code = self.active_locale.language_code

        if localized.locale.language_code != active_lang_code:
            fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})
            if fallback_code := fallback_locales.get(active_lang_code):
                if fallback_locale := SpringfieldLocale.objects.filter(language_code=fallback_code).first():
                    if fallback_snippet := self.get_translation_or_none(fallback_locale):
                        localized = fallback_snippet
            else:
                return None

        if localized.live:
            return localized
        return None


class PreFooterCTASnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet for the big Get Firefox button at the bottom of pages."""

    label = models.CharField(max_length=255, default="Get Firefox")
    analytics_id = models.CharField(default=uuid4)

    panels = [
        FieldPanel("label"),
        FieldPanel("analytics_id"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Pre Footer Call to Action"
        verbose_name_plural = "Pre Footer Call to Action"

    def __str__(self):
        return f"{self.label} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pre-footer-cta-snippet-preview.html"


class PreFooterCTAFormSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet for the Newsletter sign-up form at the bottom of pages."""

    heading = RichTextField(features=HEADING_TEXT_FEATURES)
    subheading = RichTextField(features=HEADING_TEXT_FEATURES)
    analytics_id = models.UUIDField(default=uuid4)

    panels = [
        FieldPanel("heading"),
        FieldPanel("subheading"),
        FieldPanel("analytics_id"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Pre Footer Call To Action Form"
        verbose_name_plural = "Pre Footer Call To Action Forms"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def heading_plain(self):
        """
        Plain-text rendering of `heading` for the snippet listing column.

        `heading` is a RichTextField; Wagtail's listing renders its raw value as
        HTML markup, which is hard to read in a table. This strips tags for a
        cleaner column display.
        """
        return remove_tags(richtext(self.heading))

    heading_plain.short_description = "Heading"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pre-footer-cta-form-snippet-preview.html"


class BannerSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
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

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Banner Snippet"
        verbose_name_plural = "Banner Snippets"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def heading_plain(self):
        """Plain-text rendering of `heading` for the snippet listing column.

        `heading` is a RichTextField; Wagtail's listing renders its raw value as
        HTML markup, which is hard to read in a table. This strips tags for a
        cleaner column display.
        """
        return remove_tags(richtext(self.heading))

    heading_plain.short_description = "Heading"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/banner-snippet-preview.html"


class Tag(BaseDraftTranslatableSnippetMixin, models.Model):
    """A tag for categorizing articles."""

    name = models.CharField()
    slug = models.SlugField()

    panels = [
        TitleFieldPanel("name"),
        FieldPanel("slug"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        unique_together = [*TranslatableMixin.Meta.unique_together, ("slug", "locale")]

    def __str__(self):
        return f"{self.name} – {self.locale}"


class QRCodeSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet to render a floating QR code."""

    heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
        blank=True,
    )
    qr_code = models.CharField(blank=True)
    closable = models.BooleanField(default=False, help_text="Whether the QR code can be closed by the user.")

    content = RichTextField(
        features=EXPANDED_TEXT_FEATURES,
        blank=True,
    )

    panels = [
        FieldPanel("heading"),
        FieldPanel("content"),
        FieldPanel("qr_code"),
        FieldPanel("closable"),
    ]

    override_translatable_fields = [
        SynchronizedField("qr_code"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "QR Code Snippet"
        verbose_name_plural = "QR Code Snippets"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def heading_plain(self):
        """Plain-text rendering of `heading` for the snippet listing column.

        `heading` is a RichTextField; Wagtail's listing renders its raw value as
        HTML markup, which is hard to read in a table. This strips tags for a
        cleaner column display.
        """
        return remove_tags(richtext(self.heading))

    heading_plain.short_description = "Heading"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/qr-code-snippet-preview.html"

    def serve_preview(self, request, mode_name):
        """Make sure the the snippet is always shown in preview mode, even if the cookie to hide it is set."""
        response = super().serve_preview(request, mode_name)
        response.delete_cookie("moz-qr-snippet-dismissed")
        return response


class ScrollToSeeMoreSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet to render the 'Scroll to see more' text."""

    text = models.CharField(default="Scroll to see more")

    panels = [
        FieldPanel("text"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Scroll to see more Snippet"
        verbose_name_plural = "Scroll to see more Snippets"

    def __str__(self):
        return f"{self.text} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/scroll-to-see-more-snippet-preview.html"


class SetAsDefaultSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet to render the modal content for the 'set as default' button."""

    heading_text = models.CharField()
    copy_to_clipboard_label = models.CharField(
        max_length=255, default="Copy link to page", help_text="Label for the button that copies the page link to the clipboard."
    )
    copy_success_label = models.CharField(
        max_length=255, default="Copied", help_text="Label displayed when the link is successfully copied to the clipboard."
    )
    not_firefox_content = RichTextField(
        features=EXPANDED_TEXT_FEATURES, help_text="Content shown for non-Firefox users. A download button will be shown below it."
    )
    not_default_desktop_content = RichTextField(
        features=EXPANDED_TEXT_FEATURES, help_text="Content shown for desktop users that haven't set the browser as default yet with instructions."
    )
    not_default_android_content = RichTextField(
        features=EXPANDED_TEXT_FEATURES, help_text="Content shown for android users that haven't set the browser as default yet with instructions."
    )
    not_default_ios_content = RichTextField(
        features=EXPANDED_TEXT_FEATURES, help_text="Content shown for ios users that haven't set the browser as default yet with instructions."
    )
    success_content = RichTextField(
        features=EXPANDED_TEXT_FEATURES, help_text="Content shown after user has successfully set Firefox as default browser."
    )

    panels = [
        FieldPanel("heading_text"),
        FieldPanel("not_firefox_content"),
        FieldPanel("not_default_desktop_content"),
        FieldPanel("not_default_android_content"),
        FieldPanel("not_default_ios_content"),
        FieldPanel("success_content"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Set as Default Snippet"
        verbose_name_plural = "Set as Default Snippets"

    def __str__(self):
        return f"{self.heading_text} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/set-as-default-snippet-preview.html"


class QRCodeFloatingSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet to render a floating QR code."""

    heading = RichTextField(
        features=HEADING_TEXT_FEATURES,
        blank=True,
    )
    content = RichTextField(
        features=EXPANDED_TEXT_FEATURES,
        blank=True,
    )
    url = models.CharField(blank=True, help_text="A QR code will be generated from this URL. Not used if an image is uploaded.")
    image = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Upload a QR code image. If set, this is used instead of generating one from the URL.",
    )
    # Deprecated: superseded by `open_behavior`, which is now backfilled and the
    # only field read (see `resolve_open_behavior`). Kept temporarily so the
    # column can be dropped in a separate, deploy-safe follow-up migration
    # instead of alongside the schema changes here.
    default_open = models.BooleanField(default=True)
    open_behavior = models.CharField(
        max_length=16,
        choices=QROpenBehavior.choices,
        default=QROpenBehavior.OPEN,
        help_text="How the snippet starts.",
    )
    open_delay_ms = models.PositiveIntegerField(
        default=3000,
        help_text="Delay before the snippet opens, in milliseconds (3000 = 3 seconds). Only used for the auto-open behavior.",
    )

    panels = [
        FieldPanel("heading"),
        FieldPanel("content"),
        FieldPanel("url"),
        FieldPanel("image"),
        FieldPanel("open_behavior"),
        FieldPanel("open_delay_ms"),
    ]

    override_translatable_fields = [
        SynchronizedField("url"),
        SynchronizedField("image"),
        SynchronizedField("open_behavior"),
        SynchronizedField("open_delay_ms"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "QR Code Floating Snippet"
        verbose_name_plural = "QR Code Floating Snippets"

    def __str__(self):
        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def heading_plain(self):
        """Plain-text rendering of `heading` for the snippet listing column.

        `heading` is a RichTextField; Wagtail's listing renders its raw value as
        HTML markup, which is hard to read in a table. This strips tags for a
        cleaner column display.
        """
        return remove_tags(richtext(self.heading))

    heading_plain.short_description = "Heading"

    @classmethod
    def get_live(cls, locale) -> QRCodeFloatingSnippet | None:
        """Return the live QRCodeFloatingSnippet for the given locale, or None."""
        return cls.objects.filter(locale=locale).live().first()

    def resolve_open_behavior(self, page: QRCodeFloatingSnippetMixin | None = None) -> str:
        """Resolve the starting behavior: the page override if set, otherwise the snippet's own."""
        page_behavior = getattr(page, "floating_qr_open_behavior", "")
        return page_behavior or self.open_behavior

    def resolve_qr_source(self, page: QRCodeFloatingSnippetMixin | None = None, request: HttpRequest | None = None) -> dict | None:
        """Resolve the QR code source from page overrides or snippet fields.

        A page override (image or URL) replaces the snippet's source entirely, so
        a page URL override wins over a snippet image.
        """
        page_image = getattr(page, "floating_qr_image", None)
        page_url = getattr(page, "floating_qr_url", None)
        if page_image or page_url:
            resolved_image, resolved_url = page_image, page_url
        else:
            resolved_image, resolved_url = self.image, self.url

        behavior = self.resolve_open_behavior(page)

        hide = bool(request and request.COOKIES.get("moz-qr-snippet-dismissed"))
        if hide:
            behavior = QROpenBehavior.CLOSED

        page_delay = getattr(page, "floating_qr_open_delay_ms", None)
        delay_ms = page_delay if page_delay is not None else self.open_delay_ms

        # `open` == render with the `is-open` class server-side. DELAYED renders
        # collapsed; the JS opens it after `delay_ms`.
        open = behavior == QROpenBehavior.OPEN

        # Normalize to a plain str: `behavior` may be an enum member (fallback /
        # hide paths) or a stored field string, and the value is consumed as a
        # DOM data attribute.
        result = {"open": open, "behavior": str(behavior), "delay_ms": delay_ms}
        if resolved_image:
            return {"type": "image", "value": resolved_image.file.url, **result}
        if resolved_url:
            return {"type": "qr", "value": resolved_url, **result}
        return None

    def build_context(self, page: QRCodeFloatingSnippetMixin | None = None, request: HttpRequest | None = None) -> dict:
        """Build the floating_qr_snippet context dict for template rendering."""
        return {
            "heading": self.heading,
            "content": self.content,
            "qr": self.resolve_qr_source(page, request),
        }

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        context["floating_qr_snippet"] = self.build_context(request=request)
        return context

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/qr-code-floating-snippet-preview.html"

    def clean(self):
        if not self.url and not self.image:
            raise ValidationError("Missing url or image")
        return super().clean()


class PencilBannerSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet to render a banner above the header."""

    title = RichTextField(features=HEADING_TEXT_FEATURES, help_text="Use italic text to insert a yellow pill.")
    description = RichTextField(
        features=EXPANDED_TEXT_FEATURES,
    )
    link = models.URLField(blank=True)
    dismissable = models.BooleanField(default=False, help_text="Whether the banner can be dismissed by the user.")
    settings = StreamField(
        [
            ("show_to", ConditionalDisplayBlock(include_sample_rate=False)),
        ],
        blank=True,
        use_json_field=True,
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("link"),
        FieldPanel("dismissable"),
        FieldPanel("settings"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Pencil Banner Snippet"
        verbose_name_plural = "Pencil Banner Snippets"

    def __str__(self):
        return f"{remove_tags(richtext(self.title))} – {self.locale}"

    def title_plain(self):
        """
        Plain-text rendering of `title` for the snippet listing column.

        `title` is a RichTextField; Wagtail's listing renders its raw value as
        HTML markup, which is hard to read in a table. This strips tags for a
        cleaner column display.
        """
        return remove_tags(richtext(self.title))

    title_plain.short_description = "Title"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pencil-banner-snippet-preview.html"


class NavigationSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet defining a site navigation menu, editable in the CMS.

    The ``items`` stream holds top-level links (a label + link rendered directly
    in the nav bar) and folders (a label + a dropdown of grouped links).
    """

    name = models.CharField(max_length=255, help_text="Internal name for this navigation menu.")
    is_default = models.BooleanField(default=False, help_text="Whether this is the default navigation menu for the site.")
    items = StreamField(
        [
            ("top_level_link", TopLevelLinkBlock()),
            ("folder", NavFolderBlock()),
        ],
        blank=True,
        use_json_field=True,
    )
    logo = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Override the header logo. Falls back to the default Firefox logo if unset.",
    )
    logo_dark = models.ForeignKey(
        "cms.SpringfieldImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Dark-mode variant of the header logo. Falls back to the light logo if unset.",
    )
    logo_link = StreamField(
        [("link", SpringfieldLinkBlock())],
        blank=True,
        max_num=1,
        use_json_field=True,
        help_text="Where the logo links to. Falls back to the site home page if empty.",
    )
    cta_button = StreamField(
        [("button", MixedButtonsBlock(button_types=get_button_types(), min_num=0, max_num=1))],
        blank=True,
        max_num=1,
        use_json_field=True,
        help_text="Override the header download button. Falls back to the default Firefox download button if empty.",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("is_default"),
        MultiFieldPanel(
            [
                FieldPanel("logo"),
                FieldPanel("logo_dark"),
                FieldPanel("logo_link"),
            ],
            heading="Logo",
        ),
        FieldPanel("items"),
        FieldPanel("cta_button", heading="CTA Button"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Navigation"
        verbose_name_plural = "Navigation"

    def __str__(self):
        return f"{self.name} – {self.locale}"

    @classmethod
    def get_default(cls):
        """Return the site default navigation, localized to the active locale, or None."""
        snippet = cls.objects.filter(is_default=True, locale=SpringfieldLocale.get_default()).live().order_by("-last_published_at").first()
        return snippet.get_localized() if snippet else None

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/navigation-snippet-preview.html"


class PretranslatedPhrase(BaseDraftTranslatableSnippetMixin, models.Model):
    """A reusable, translatable text label."""

    label = models.CharField(max_length=255)

    panels = [FieldPanel("label")]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Pretranslated Phrase"
        verbose_name_plural = "Pretranslated Phrases"

    def __str__(self):
        return f"{self.label} – {self.locale}"


# Partner builds only exist on production, so their links ignore `settings.BOUNCER_URL`.
PARTNER_DOWNLOAD_HOST = "download.mozilla.org"

PARTNER_REPACK_LINKS = {
    "windows64_url": ("windows", "win64", "Windows 64-bit"),
    "windows32_url": ("windows", "win", "Windows 32-bit"),
    "mac_url": ("mac", "osx", "Mac"),
    "linux_url": ("linux", "linux64", "Linux"),
}

PARTNER_REPACK_PLATFORMS = ("windows", "mac", "linux")


class PartnerRepackLinkLabel(models.TextChoices):
    VISIT = "visit", "Visit <display name>"
    LEARN_MORE = "learn_more", "Learn more"


class PartnerRepack(DraftStateMixin, RevisionMixin, models.Model):
    """A partner's Firefox builds, offered to visitors who follow the partner's download link."""

    name = models.CharField(
        "Display name",
        max_length=60,
        help_text='The company name visitors see in messages, e.g. "Acme".',
    )
    slug = models.SlugField(
        "Link name",
        max_length=60,
        unique=True,
        help_text="Used in the link firefox.com/get/?p=<link name>. Changing it breaks links already shared.",
    )
    windows64_url = models.URLField(
        "Windows 64-bit link",
        max_length=500,
        blank=True,
        help_text=(
            "Paste the link exactly as the product team supplied it, "
            "e.g. https://download.mozilla.org/?product=partner-firefox-release-acme-acme-001-latest&os=win64. "
            "Leave it blank if there's no 64-bit build."
        ),
    )
    windows32_url = models.URLField(
        "Windows 32-bit link",
        max_length=500,
        blank=True,
        help_text="Paste the link exactly as the product team supplied it, ending &os=win. Leave it blank if there's no 32-bit build.",
    )
    windows_languages = models.TextField(
        "Windows languages",
        blank=True,
        help_text=(
            "Language codes the Windows builds were made for, separated by commas or spaces, e.g. en-US, de, fr. "
            "Covers both Windows links. Usually the same for every system."
        ),
    )
    mac_url = models.URLField(
        "Mac link",
        max_length=500,
        blank=True,
        help_text="Paste the link exactly as the product team supplied it, ending &os=osx. Leave it blank if there's no Mac build.",
    )
    mac_languages = models.TextField(
        "Mac languages",
        blank=True,
        help_text="Language codes the Mac build was made for, separated by commas or spaces, e.g. en-US, de, fr. Usually the same for every system.",
    )
    linux_url = models.URLField(
        "Linux link",
        max_length=500,
        blank=True,
        help_text="Paste the link exactly as the product team supplied it, ending &os=linux64. Leave it blank if there's no Linux build.",
    )
    linux_languages = models.TextField(
        "Linux languages",
        blank=True,
        help_text=(
            "Language codes the Linux build was made for, separated by commas or spaces, e.g. en-US, de, fr. Usually the same for every system."
        ),
    )
    firefox_user_link_url = models.URLField(
        "Link for current Firefox users",
        blank=True,
        help_text=(
            "Visitors already using desktop Firefox can't get this download, so they see a message instead. "
            "Add a link here to give them a second button, e.g. to the company's own page. Nobody else sees it."
        ),
    )
    firefox_user_link_label = models.CharField(
        "Button label",
        max_length=20,
        choices=PartnerRepackLinkLabel,
        default=PartnerRepackLinkLabel.VISIT,
        help_text="The button text for the link above.",
    )

    objects = BaseDraftQueryset.as_manager()

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        MultiFieldPanel([FieldPanel("windows64_url"), FieldPanel("windows32_url"), FieldPanel("windows_languages")], heading="Windows"),
        MultiFieldPanel([FieldPanel("mac_url"), FieldPanel("mac_languages")], heading="Mac"),
        MultiFieldPanel([FieldPanel("linux_url"), FieldPanel("linux_languages")], heading="Linux"),
        MultiFieldPanel([FieldPanel("firefox_user_link_url"), FieldPanel("firefox_user_link_label")], heading="Current Firefox users"),
        HelpPanel(heading="Test links", template="wagtailadmin/panels/partner_repack_test_links.html"),
    ]

    class Meta:
        verbose_name = "Partner download"
        verbose_name_plural = "Partner downloads"

    def __str__(self):
        return self.name

    def systems(self) -> str:
        """Name the systems this partner has a download link for, e.g. "Windows, Mac"."""
        return ", ".join(platform.capitalize() for platform in PARTNER_REPACK_PLATFORMS if self.has_link(platform))

    systems.short_description = "Systems"

    def has_link(self, platform: str) -> bool:
        """Return whether any download link is set for `platform` ("windows", "mac" or "linux")."""
        return any(getattr(self, link_field) for link_field, (link_platform, _, _) in PARTNER_REPACK_LINKS.items() if link_platform == platform)

    def languages_for(self, platform: str) -> list[str]:
        """Return the language codes listed for `platform`, which editors separate with commas or spaces."""
        return getattr(self, f"{platform}_languages").replace(",", " ").split()

    def download_url(self, link_field: str, lang: str) -> str | None:
        """Return the download URL for `link_field` in `lang`, or None if there's no such build."""
        platform = PARTNER_REPACK_LINKS[link_field][0]
        if not getattr(self, link_field) or lang not in self.languages_for(platform):
            return None
        try:
            params = parse_qs(urlsplit(getattr(self, link_field)).query)
        except ValueError:
            return None
        product, link_os = params.get("product", [""])[0], params.get("os", [""])[0]
        # The download server's Mac Japanese build uses its own code.
        download_lang = "ja-JP-mac" if platform == "mac" and lang == "ja" else lang
        return f"https://{PARTNER_DOWNLOAD_HOST}/?{urlencode({'product': product, 'os': link_os, 'lang': download_lang})}"

    def download_options(self, lang: str) -> dict[str, dict]:
        """Return each platform's state ("available", "language" or "device") and its URLs for `lang`."""
        options = {}
        for platform in PARTNER_REPACK_PLATFORMS:
            urls = {}
            for link_field, (link_platform, link_os, _) in PARTNER_REPACK_LINKS.items():
                if link_platform == platform and (url := self.download_url(link_field, lang)):
                    urls[link_os] = url
            if urls:
                state = "available"
            elif self.has_link(platform):
                state = "language"
            else:
                state = "device"
            options[platform] = {"state": state, "urls": urls}
        return options

    def test_links(self) -> list[tuple[str, str, str]]:
        """Return (system, language, URL) for every link and listed language."""
        return [
            (system, lang, url)
            for link_field, (platform, _, system) in PARTNER_REPACK_LINKS.items()
            for lang in self.languages_for(platform)
            if (url := self.download_url(link_field, lang))
        ]

    def clean(self):
        super().clean()
        # The view lowercases `p`, so lowercase slugs also stay unique ignoring case.
        self.slug = self.slug.lower()
        errors = {}

        for link_field in PARTNER_REPACK_LINKS:
            if getattr(self, link_field) and (error := self.link_error(link_field)):
                errors[link_field] = error

        if not any(self.has_link(platform) for platform in PARTNER_REPACK_PLATFORMS):
            errors[NON_FIELD_ERRORS] = "Add a download link for at least one system."

        for platform in PARTNER_REPACK_PLATFORMS:
            if error := self.normalize_languages(platform):
                errors[f"{platform}_languages"] = error

        if errors:
            raise ValidationError(errors)

    def link_error(self, link_field: str) -> str | None:
        """Return the problem with the link in `link_field`, or None if it's usable."""
        _, expected_os, system = PARTNER_REPACK_LINKS[link_field]
        try:
            link = urlsplit(getattr(self, link_field))
            hostname = link.hostname
        except ValueError:
            hostname = None
        if hostname != PARTNER_DOWNLOAD_HOST:
            return f"Use the {PARTNER_DOWNLOAD_HOST} link supplied by the product team."
        params = parse_qs(link.query)
        link_os = params.get("os", [""])[0]
        if not params.get("product"):
            return "This link has no product. Paste the full link supplied by the product team."
        if link_os == expected_os:
            return None
        if other_system := next((label for _, system_os, label in PARTNER_REPACK_LINKS.values() if system_os == link_os), None):
            return f"This link is for {other_system} (os={link_os}). Paste it in that field."
        return f"This link isn't for {system}."

    def normalize_languages(self, platform: str) -> str | None:
        """Store `platform`'s languages in canonical case without duplicates, or return the problem."""
        entered = self.languages_for(platform)
        if self.has_link(platform) and not entered:
            return "Add the languages this build was made for."
        if entered and not self.has_link(platform):
            return "Add a download link, or clear these languages."

        canonical_codes = {code.lower(): code for code in settings.PROD_LANGUAGES} | {"ja-jp-mac": "ja"}
        if unknown := [code for code in entered if code.lower() not in canonical_codes]:
            return f"Not a Firefox download language: {', '.join(dict.fromkeys(unknown))}."
        setattr(self, f"{platform}_languages", ", ".join(dict.fromkeys(canonical_codes[code.lower()] for code in entered)))
        return None
