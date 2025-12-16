# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.models import DraftStateMixin, PreviewableMixin, RevisionMixin, TranslatableMixin
from wagtail.snippets.models import register_snippet

from lib import l10n_utils
from springfield.cms.blocks import MenuItemBlock
from springfield.cms.fields import StreamField


class SpringfieldPreviewableSnippetMixin(PreviewableMixin):
    """
    Mixin to add preview support to snippets so they can be rendered outside a page context.
    Similar to AbstractSpringfieldCMSPage
    """

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        locale = l10n_utils.get_locale(request)
        context["fluent_l10n"] = l10n_utils.fluent_l10n([locale, "en"], settings.FLUENT_DEFAULT_FILES)
        context["is_preview"] = True
        return context


class MenuSnippet(TranslatableMixin, DraftStateMixin, RevisionMixin, SpringfieldPreviewableSnippetMixin, models.Model):
    """A snippet representing a menu, which can be reused across the site."""

    title = models.CharField(max_length=255, help_text="Title of the menu")
    items = StreamField(
        [
            ("item", MenuItemBlock()),
        ],
        verbose_name="Menu Items",
        help_text="Items in the menu",
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("items"),
    ]

    class Meta(TranslatableMixin.Meta, DraftStateMixin.Meta, RevisionMixin.Meta):
        verbose_name = "Menu Snippet"
        verbose_name_plural = "Menu Snippets"

    def __str__(self):
        return self.title

    def get_preview_template(self, request, mode_name):
        return "cms/snippets/menu-snippet-preview.html"


register_snippet(MenuSnippet)
