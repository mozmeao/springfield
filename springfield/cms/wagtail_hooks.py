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

from springfield.base.templatetags.helpers import css_bundle


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


class FXLogoEntityElementHandler(InlineEntityElementHandler):
    """
    Database HTML to Draft.js ContentState.
    Converts the <span class="fl-fx-logo"> tag into an FX-LOGO entity.
    """

    mutability = "IMMUTABLE"

    def get_attribute_data(self, attrs):
        """
        Return a minimal data dict. Returning completely empty dict might cause issues.
        """
        return {"logo": True}


def fx_logo_entity_decorator(props):
    """
    Draft.js ContentState to database HTML.
    Converts the FX-LOGO entities into a <span class="fl-fx-logo"> tag.
    The entity will contain a space character as placeholder text.
    """
    return DOM.create_element("span", {"class": "fl-fx-logo"}, props["children"])


@hooks.register("register_rich_text_features")
def register_firefox_logo_feature(features):
    """
    Registering the `fx-logo` feature, which adds a span with the Firefox logo to the text.
    Uses an entity approach since it's a standalone inline element without user text content.
    """
    feature_name = "fx-logo"
    type_ = "FX-LOGO"

    control = {
        "type": type_,
        "description": "Firefox Logo",
        "icon": [
            (
                "M 952.053 342.265 c -21.4912 -51.692 -65.0189 -107.503 -99.197 -125.141 c "
                "27.8182 54.5253 43.9186 109.242 50.0707 150.068 c 0 0.0823 0.0309 0.2798 0.0967 "
                "0.823 c -55.9141 -139.363 -150.724 -195.565 -228.155 -317.917 c -3.9093 -6.1891 "
                "-7.829 -12.3906 -11.6479 -18.9295 c -1.9453 -3.339 -3.7613 -6.7516 -5.4443 "
                "-10.2302 c -3.209 -6.2073 -5.6844 -12.767 -7.3763 -19.5468 c 0.0256 -0.6661 -0.4621"
                " -1.2413 -1.1234 -1.3251 c -0.3029 -0.089 -0.625 -0.089 -0.9279 0 c -0.0679 0.0226 "
                "-0.1729 0.1049 -0.2448 0.1337 c -0.1091 0.0412 -0.2469 0.142 -0.3621 0.1955 c "
                "0.0535 -0.0741 0.1708 -0.2407 0.2058 -0.2778 c -109.95 64.4016 -155.525 177.141 "
                "-167.243 248.903 c -33.9713 1.9299 -67.2471 10.4214 -97.9892 25.0055 c -5.7911 2.8652"
                " -8.4898 9.6361 -6.257 15.6992 c 2.2405 6.4804 9.3102 9.9175 15.7906 7.6771 c 0.3613 "
                "-0.1249 0.7167 -0.2665 1.0649 -0.4242 c 26.8217 -12.6554 55.7642 -20.2091 85.3496 "
                "-22.2751 c 0.9629 -0.0679 1.9279 -0.1276 2.8909 -0.2058 c 4.0642 -0.2474 8.134 "
                "-0.3921 12.2055 -0.4341 c 24.0062 -0.1672 47.9102 3.1434 70.9673 9.8289 c 1.3456 "
                "0.3951 2.6646 0.8518 4.004 1.2675 c 3.8291 1.1708 7.6291 2.4346 11.3968 3.79 c 2.7566 "
                "1.0244 5.495 2.0972 8.2138 3.218 c 2.2098 0.893 4.4197 1.786 6.5965 2.7386 c 3.3964 "
                "1.5052 6.758 3.0879 10.082 4.7468 c 1.5288 0.7572 3.0554 1.5123 4.5616 2.2983 c 3.2453 "
                "1.703 6.4524 3.4777 9.6191 5.3229 c 2.044 1.1856 4.0688 2.4039 6.0739 3.6542 c 35.819 "
                "22.1595 65.5419 52.9072 86.475 89.4565 c -26.4047 -18.5489 -73.6812 -36.8673 -119.229 "
                "-28.9457 c 177.857 88.9153 130.108 395.107 -116.345 383.545 c -21.9473 -0.8943 -43.6362 "
                "-5.0773 -64.3419 -12.4091 c -4.8974 -1.8395 -9.7409 -3.8197 -14.5243 -5.9381 c -2.7901 "
                "-1.2716 -5.578 -2.5576 -8.3352 -3.9814 c -60.3873 -31.209 -110.25 -90.1889 -116.48 "
                "-161.813 c 0 0 22.8245 -85.0491 163.438 -85.0491 c 15.2012 0 58.6569 -42.4145 59.4635 "
                "-54.7166 c -0.1852 -4.0184 -86.2467 -38.25 -119.797 -71.3067 c -17.9296 -17.6641 "
                "-26.4417 -26.1783 -33.9785 -32.5691 c -4.0908 -3.4535 -8.3666 -6.6818 -12.8083 -9.6705 "
                "c -11.272 -39.4316 -11.7516 -81.1663 -1.3889 -120.847 c -50.7949 23.1311 -90.3062 59.6918 "
                "-119.028 91.9728 h -0.2284 c -19.6044 -24.8286 -18.2197 -106.732 -17.1024 -123.832 c "
                "-0.2346 -1.0617 -14.6231 7.4689 -16.5099 8.7528 c -17.2967 12.348 -33.4676 26.2013 "
                "-48.3238 41.3981 c -16.9049 17.1428 -32.351 35.6653 -46.1778 55.375 c 0 0.0247 -0.0144 "
                "0.0514 -0.0226 0.0761 c 0 -0.0247 0.0144 -0.0514 0.0226 -0.0782 c -31.7959 45.0629 -54.345 "
                "95.9808 -66.3439 149.811 c -0.1193 0.5453 -4.7118 20.6867 -8.0656 45.5687 c -0.569 3.87 "
                "-1.0964 7.746 -1.5823 11.6273 c -1.1481 7.4813 -2.0411 15.6375 -2.9217 28.3264 c -0.0391 "
                "0.4918 -0.0638 0.9753 -0.0988 1.465 c -0.367 5.4811 -0.6969 10.9646 -0.9897 16.4502 c 0 "
                "0.8456 -0.0514 1.679 -0.0514 2.5246 c 0 273.056 221.393 494.411 494.481 494.411 c 244.572 "
                "0 447.64 -177.543 487.399 -410.75 c 0.8375 -6.327 1.5061 -12.691 2.2469 -19.0735 c 9.829 "
                "-84.7919 -1.0905 -173.915 -32.0732 -248.444 h 0 Z"
            ),
        ],
    }

    # Register the Draftail plugin as an entity feature
    # Using js parameter to provide custom source for insertion without text selection
    features.register_editor_plugin(
        "draftail",
        feature_name,
        draftail_features.EntityFeature(
            control,
            js=["js/wagtailadmin-fx-logo.js"],
        ),
    )

    # Configure the content transform from the DB to the editor and back.
    db_conversion = {
        "from_database_format": {
            "span[class=fl-fx-logo]": FXLogoEntityElementHandler(type_),
        },
        "to_database_format": {
            "entity_decorators": {
                type_: fx_logo_entity_decorator,
            }
        },
    }

    # Register the content transformation conversion.
    features.register_converter_rule("contentstate", feature_name, db_conversion)

    # Add the feature to the default features list to make it available
    # on rich text fields that do not specify an explicit 'features' list
    features.default_features.append(feature_name)
