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

from springfield.base.templatetags.helpers import css_bundle


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
        "icon": [
            "M1.136 1024.5H.557V.5h.579zm47.456-276.319c30.256 0 48.092-18.472 48.092-50.002v-136.95h151.282c25.16 0 "
            "41.085-14.332 41.085-38.219 0-23.568-16.243-37.9-41.085-37.9H96.684V362.173H263.57c26.117 0 43.633-14.968"
            " 43.633-39.81s-17.198-39.812-43.633-39.812H48.591C18.336 282.551.5 301.024.5 332.554V698.18c0 31.53 17.835"
            " 50.002 48.092 50.002Zm284.085.637c16.561 0 25.797-5.414 38.537-25.16l66.564-100.006h1.91l67.839 101.598c10.51"
            " 15.924 19.428 23.568 37.581 23.568 25.161 0 44.27-15.924 44.27-41.085 0-10.191-3.185-19.11-10.191-28.664l-79.304-109.56"
            " 78.03-104.145c8.917-11.466 12.42-20.702 12.42-32.168 0-23.568-17.516-39.492-43.632-39.492-17.198 0-27.072 "
            "7.643-39.493 27.071l-62.423 95.228h-1.911l-63.698-95.865c-12.421-19.746-22.294-26.434-41.085-26.434-25.48 "
            "0-44.588 17.517-44.588 40.766 0 10.829 3.185 20.065 9.873 28.983l79.622 108.604-79.94 107.012c-8.918 11.784-12.422"
            " 20.702-12.422 31.849 0 22.294 17.517 37.9 42.04 37.9Zm328.527-.637c25.48 0 39.811-12.74 "
            "48.729-43.314l24.205-71.66h165.933l24.205 72.615c8.599 29.938 22.93 42.36 50.002 42.36 28.027 0 "
            "48.092-18.792 48.092-45.226 0-9.555-1.592-18.154-6.051-30.575L890.197 330.325c-13.695-37.582-35.989-54.143-73.57-54.143-36.308"
            " 0-58.92 17.198-72.297 54.461L618.845 672.381c-4.14 11.784-6.37 22.613-6.37 30.575 0 27.708 18.791 45.225 48.73 "
            "45.225Zm93.954-189.5 59.558-188.227h2.229l60.831 188.227z"
        ],
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
