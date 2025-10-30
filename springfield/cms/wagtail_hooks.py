# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse
from django.utils.safestring import mark_safe

import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.admin.widgets.button import Button

from springfield.base.templatetags.helpers import css_bundle


@hooks.register("register_rich_text_features")
def register_fxa(features):
    feature = "fxa"
    type_ = "FXA"
    tag = "fxa"

    control = {
        "type": type_,
        "label": "FXA 🔗",
        "description": "Firefox Account link",
        "element": "fxa",
        "style": {"textDecoration": "underline"},
    }

    features.register_editor_plugin("draftail", feature, draftail_features.InlineStyleFeature(control))

    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {"style_map": {type_: tag}},
    }
    features.register_converter_rule("contentstate", feature, db_conversion)

    if feature not in features.default_features:
        features.default_features.append(feature)


@hooks.register("register_admin_menu_item")
def register_pages_list_link():
    return MenuItem(
        "Translations List",
        reverse("cms:translations_list"),
        icon_name="wagtail-localize-language",
        order=101,
    )


@hooks.register("register_admin_menu_item")
def register_task_queue_link():
    return MenuItem(
        "Task Queue",
        reverse("rq_home"),
        icon_name="tasks",
        order=80000,
    )


@hooks.register("register_admin_menu_item")
def register_django_admin_link():
    return MenuItem(
        "Django Admin",
        reverse("admin:index"),
        icon_name="tasks",
        order=80001,
    )


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return mark_safe(css_bundle("wagtail-admin"))


@hooks.register("construct_page_listing_buttons")
def add_custom_link_button(buttons, page, user, context=None):
    """
    Add a custom 'See Translations' button to pages in the explorer.

    Note: since home pages (and the root page) are not visible on the translations
    list page, we do not show a 'See Translations' link for the home pages (or
    the root page).
    """
    if page.depth > 2:  # Only show the button for descendants of home pages
        translations_button = Button(
            label="See Translations",
            classname="button",
            attrs={"target": "_blank"},
            url=f"{reverse('cms:translations_list')}?translation_key={page.translation_key}",
        )
        buttons.append(translations_button)
    return buttons
