# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from django.http import HttpRequest

    from springfield.cms.models.pages import QRCodeFloatingSnippetMixin

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property

from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet
from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail_localize.fields import SynchronizedField

from lib.l10n_utils import fluent_l10n, get_locale
from springfield.cms.blocks import EXPANDED_TEXT_FEATURES, HEADING_TEXT_FEATURES, ButtonBlock
from springfield.cms.fields import StreamField
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.rich_text import RichTextField


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


register_snippet(PreFooterCTASnippet)


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
        from springfield.cms.templatetags.cms_tags import remove_tags

        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/pre-footer-cta-form-snippet-preview.html"


register_snippet(PreFooterCTAFormSnippet)


class DownloadFirefoxCallToActionSnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
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

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Download Firefox Call To Action Snippet"
        verbose_name_plural = "Download Firefox Call To Action Snippets"

    def __str__(self):
        from springfield.cms.templatetags.cms_tags import remove_tags

        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/download-firefox-cta-snippet-preview.html"


register_snippet(DownloadFirefoxCallToActionSnippet)


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
        from springfield.cms.templatetags.cms_tags import remove_tags

        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/banner-snippet-preview.html"


register_snippet(BannerSnippet)


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

    def __str__(self):
        return f"{self.name} – {self.locale}"


register_snippet(Tag)


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
        from springfield.cms.templatetags.cms_tags import remove_tags

        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/qr-code-snippet-preview.html"

    def serve_preview(self, request, mode_name):
        """Make sure the the snippet is always shown in preview mode, even if the cookie to hide it is set."""
        response = super().serve_preview(request, mode_name)
        response.delete_cookie("moz-qr-snippet-dismissed")
        return response


register_snippet(QRCodeSnippet)


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


register_snippet(SetAsDefaultSnippet)


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
    default_open = models.BooleanField(default=True)

    panels = [FieldPanel("heading"), FieldPanel("content"), FieldPanel("url"), FieldPanel("image"), FieldPanel("default_open")]

    override_translatable_fields = [SynchronizedField("url"), SynchronizedField("image")]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "QR Code Floating Snippet"
        verbose_name_plural = "QR Code Floating Snippets"

    def __str__(self):
        from springfield.cms.templatetags.cms_tags import remove_tags

        return f"{remove_tags(richtext(self.heading))} – {self.locale}"

    @classmethod
    def get_live(cls, locale) -> QRCodeFloatingSnippet | None:
        """Return the live QRCodeFloatingSnippet for the given locale, or None."""
        return cls.objects.filter(locale=locale).live().first()

    def resolve_qr_source(self, page: QRCodeFloatingSnippetMixin | None = None, request: HttpRequest | None = None) -> dict | None:
        """Resolve the QR code source from page overrides or snippet fields."""
        resolved_image = getattr(page, "floating_qr_image", None) or self.image
        resolved_url = getattr(page, "floating_qr_url", None) or self.url
        floating_qr_default_open = getattr(page, "floating_qr_default_open", None)

        hide = bool(request and request.COOKIES.get("moz-qr-snippet-dismissed"))

        resolved_default_open = floating_qr_default_open if floating_qr_default_open is not None else self.default_open
        open = not hide and resolved_default_open

        if resolved_image:
            return {"type": "image", "value": resolved_image.file.url, "open": open}
        if resolved_url:
            return {"type": "qr", "value": resolved_url, "open": open}
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


register_snippet(QRCodeFloatingSnippet)
