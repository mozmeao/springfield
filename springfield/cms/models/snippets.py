# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from wagtail.admin.panels import FieldPanel, TitleFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet
from wagtail.templatetags.wagtailcore_tags import richtext
from wagtail_localize.fields import SynchronizedField

from lib.l10n_utils import fluent_l10n, get_locale
from lib.l10n_utils.fluent import ftl
from springfield.cms.blocks import EXPANDED_TEXT_FEATURES, FLUENT_TEXT_CUSTOM, FLUENT_TEXT_PRESET_CHOICES, HEADING_TEXT_FEATURES, ButtonBlock
from springfield.cms.fields import StreamField
from springfield.cms.models.locale import SpringfieldLocale


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
        """Get the localized instance of this snippet for the active locale, or None if not available in the active locale."""
        instance = self.localized
        if instance and (instance.locale_id != self.active_locale.id or not instance.live):
            return None
        return instance


class PreFooterCTASnippet(FluentPreviewableMixin, BaseDraftTranslatableSnippetMixin, models.Model):
    """A snippet for the big Get Firefox button at the bottom of pages."""

    # DEPRECATED: label_old is the pre-migration label field (renamed from
    # "label" in migration 0057). Remove this field and add a RemoveField
    # migration once migrate_download_button_labels has been run in all
    # environments.
    label_old = models.CharField(max_length=255, default="Get Firefox")

    pretranslated_label = models.CharField(
        max_length=255,
        choices=FLUENT_TEXT_PRESET_CHOICES,
        default="navigation-get-firefox",
        help_text=(
            "Choose a pre-translated label. If 'Custom text' is selected, fill in the custom label below. "
            "Note: if you choose one of the pre-translated choices, then translations of this snippet "
            "will inherit the translation for this text (and not be able to set it on their own)."
        ),
    )
    custom_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Only used when 'Custom text' is selected above. Will be sent for translation.",
    )
    analytics_id = models.CharField(default=uuid4)

    override_translatable_fields = [
        SynchronizedField("pretranslated_label"),
    ]

    panels = [
        FieldPanel("pretranslated_label"),
        FieldPanel("custom_label"),
        FieldPanel("analytics_id"),
    ]

    class Meta(BaseDraftTranslatableSnippetMixin.Meta):
        verbose_name = "Pre Footer Call to Action"
        verbose_name_plural = "Pre Footer Call to Action"

    def __str__(self):
        return f"{self.resolve_label()} – {self.locale}"

    def resolve_label(self):
        if self.pretranslated_label == FLUENT_TEXT_CUSTOM:
            return self.custom_label
        return ftl(self.pretranslated_label, ftl_files=["navigation-firefox", "download_button"])

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
