# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_test_index_page
from springfield.cms.models import FreeFormPage


def get_inline_notification_variants():
    return {
        "basic": {
            "type": "inline_notification",
            "value": {
                "message": "This is a simple inline notification.",
            },
        },
        "white_closable": {
            "type": "inline_notification",
            "value": {
                "message": "White closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "white",
                    "inverted": False,
                    "closable": True,
                },
            },
        },
        "black_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Black closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "black",
                    "inverted": False,
                    "closable": True,
                },
            },
        },
        "blue_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Blue closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "blue",
                    "inverted": False,
                    "closable": True,
                },
            },
        },
        "purple_not_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Purple inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "purple",
                    "inverted": False,
                    "closable": False,
                },
            },
        },
        "orange_not_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Orange inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "orange",
                    "inverted": False,
                    "closable": False,
                },
            },
        },
        "yellow_not_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Yellow inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "yellow",
                    "inverted": False,
                    "closable": False,
                },
            },
        },
        "white_inverted": {
            "type": "inline_notification",
            "value": {
                "message": "Inverted white inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "white",
                    "inverted": True,
                    "closable": False,
                },
            },
        },
        "black_inverted": {
            "type": "inline_notification",
            "value": {
                "message": "Black inverted inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "black",
                    "inverted": True,
                    "closable": False,
                },
            },
        },
        "blue_inverted": {
            "type": "inline_notification",
            "value": {
                "message": "Blue inverted inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "blue",
                    "inverted": True,
                    "closable": False,
                },
            },
        },
        "purple_inverted": {
            "type": "inline_notification",
            "value": {
                "message": "Purple inverted closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "purple",
                    "inverted": True,
                    "closable": True,
                },
            },
        },
        "orange_inverted_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Inverted orange closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "orange",
                    "inverted": True,
                    "closable": True,
                },
            },
        },
        "yellow_inverted_closable": {
            "type": "inline_notification",
            "value": {
                "message": "Inverted yellow closable inline notification with icon.",
                "settings": {
                    "icon": "user",
                    "color": "yellow",
                    "inverted": True,
                    "closable": True,
                },
            },
        },
    }


def get_inline_notification_test_page():
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-inline-notifications-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-inline-notifications-page",
            title="Test Inline Notifications Page",
        )
        index_page.add_child(instance=page)

    page.content = list(get_inline_notification_variants().values())
    page.save_revision().publish()
    return page
