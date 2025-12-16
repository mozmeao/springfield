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
    return mark_safe(js_bundle("translatable-link-block"))


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
            (
                "M464.31 577.275c70.336-69.719 183.72-69.719 254.055 0 62.448 62.45 70.848 160.798 19.896 "
                "232.934l-1.225 1.224c-12.447 18.672-37.343 22.447-56.014 9.948-17.447-13.672-22.447-38.618 "
                "-8.724-56.014l1.225-1.276c28.56-40.077 23.804-94.959-11.224-129.526-38.567-39.843-102.08 "
                "-39.843-141.974 0L380.85 774.09c-39.843 38.568-39.843 102.132 0 141.975 34.876 34.365 89.26 "
                "39.078 129.527 11.223l1.224-2.55c18.723-12.448 43.618-8.673 56.117 9.998 12.396 17.447 8.672 "
                "42.343-8.775 56.066l-2.5 1.224c-71.677 50.909-169.663 42.491-231.607-19.896-70.17-69.005-71.114 "
                "-181.828-2.109-251.997q1.045-1.063 2.109-2.108zM831.72 886.17c-69.02 70.155-181.842 71.076-251.998 "
                "2.057q-1.036-1.02-2.056-2.057c-62.432-61.939-70.872-159.959-19.947-231.659l1.224-1.275c12.448-18.671 "
                "37.394-22.396 56.066-9.948 17.838 12.836 21.893 37.702 9.057 55.54q-.19.265-.385.526l-1.224 1.224c-28.524 "
                "40.105-23.772 94.974 11.223 129.578 38.618 39.791 102.132 39.791 141.975 0L915.18 690.63c39.791-39.843 "
                "39.791-103.407 0-141.975-34.604-34.994-89.473-39.747-129.578-11.223l-1.225 1.224c-17.6 13.114-42.498 "
                "9.478-55.611-8.122a41 41 0 0 1-.403-.55c-12.481-18.038-8.672-42.688 8.672-56.116l2.551-1.225c71.69-50.895 "
                "169.676-42.456 231.608 19.947 70.155 69.02 71.076 181.842 2.057 251.998q-1.02 1.036-2.057 2.056L831.771 886.17z"
            ),
            "M0 498.744V0h148.898l103.361 347.672h20.965L376.585 0H526.21v498.744h-82.404V69.388h-20.238 "
            "L297.803 498.744h-73.01L99.748 69.388H79.51v429.356z",
        ],
        "description": "Mozilla Account link",
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
