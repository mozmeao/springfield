# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import template
from django.urls import reverse
from django.utils.html import format_html

from wagtail.models import Page
from wagtaildraftsharing.wagtail_hooks import DraftsharingPageActionMenuItem

from springfield.cms.draftsharing import has_shareable_translation_draft

register = template.Library()


class TranslationDraftsharingMenuItem(DraftsharingPageActionMenuItem):
    """The `wagtaildraftsharing` action menu button for translated pages."""

    template_name = "wagtaildraftsharing/translation_action_menu_item.html"

    def __init__(self, translation, **kwargs):
        super().__init__(**kwargs)
        self.translation = translation

    def get_context_data(self, parent_context):
        context = super().get_context_data(parent_context)
        context["create_url"] = reverse("cms_translation_draftsharing_create", args=[self.translation.id])
        return context


@register.simple_tag(takes_context=True)
def translation_draftsharing_button(context, translation, instance):
    """
    Returns the draft sharing button for a translated page inside a `<template>`
    element. Returns an empty string when there is nothing unpublished and for
    snippets (which share this editor but have no page to share).

    The translation editor's action menu is rendered by React, so the button is moved
    into place by `wagtailadmin-translation-draftsharing.es6.js`.
    """
    if not isinstance(instance, Page):
        return ""
    if not has_shareable_translation_draft(translation, instance):
        return ""

    menu_item = TranslationDraftsharingMenuItem(translation=translation)
    button = menu_item.render_html({"request": context["request"], "page": instance})
    return format_html('<template id="translation-draftsharing-button">{}</template>', button)
