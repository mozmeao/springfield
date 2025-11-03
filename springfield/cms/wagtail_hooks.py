# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.urls import reverse
from django.utils.safestring import mark_safe

import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from draftjs_exporter.dom import DOM
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineEntityElementHandler,
)
from wagtail.admin.widgets.button import Button

from springfield.base.templatetags.helpers import css_bundle, js_bundle


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


@hooks.register("insert_global_admin_js")
def global_admin_js():
    return js_bundle("wagtail-admin")


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


class FXAEntityElementHandler(InlineEntityElementHandler):
    """
    Database HTML to Draft.js ContentState.
    Converts the <fxa> tag into an FXA entity, with the right data.
    """

    mutability = "MUTABLE"

    def get_attribute_data(self, attrs):
        return {"uid": attrs.get("data-cta-uid")}


def fxa_entity_decorator(props):
    """
    Draft.js ContentState to database HTML.
    Converts the FXA entities into an <fxa> tag.
    """
    return DOM.create_element(
        "fxa",
        {
            "data-cta-uid": props.get("uid", str(uuid4())),
        },
        props["children"],
    )


@hooks.register("register_rich_text_features")
def register_fxa(features):
    """
    Register the FXA rich text feature, which adds support for the <fxa> tag.
    Since the Firefox Account link requires the request context (like UTM parameters) to be
    rendered correctly, the tag itself does not contain a URL. Instead, the URL is
    constructed by the `richtext` template filter (springfield/cms/templatetags/cms_tags.py),
    which replaces the <fxa> tag with the appropriate <a> tag.
    """
    feature = "fxa"
    type_ = "FXA"
    tag = "fxa"

    control = {
        "type": type_,
        "label": "FXA 🔗",
        "description": "Firefox Account link",
        "element": "fxa",
    }

    features.register_editor_plugin(
        "draftail",
        feature,
        draftail_features.EntityFeature(control, js=["js/wagtailadmin-fxa.js"]),
    )

    db_conversion = {
        "from_database_format": {tag: FXAEntityElementHandler(type_)},
        "to_database_format": {"entity_decorators": {type_: fxa_entity_decorator}},
    }
    features.register_converter_rule("contentstate", feature, db_conversion)

    if feature not in features.default_features:
        features.default_features.append(feature)
