# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_test_index_page
from springfield.cms.models import FreeFormPage


def get_inline_notification_variants() -> list[dict]:
    return [
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "",
                    "color": "",
                    "inverted": False,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="ilmnr">This is a simple inline notification.</p>',
            },
            "id": "3028c4f3-729f-4c68-b8fd-398340b2ce07",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "white",
                    "inverted": False,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="qhyuj">White closable inline notification with icon.</p>',
            },
            "id": "6ea433a2-b06b-475e-a9ca-7b705769fc5a",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "black",
                    "inverted": False,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="qcsmr">Black closable inline notification with icon.</p>',
            },
            "id": "734c84a1-2ffc-49fe-8adf-25b1652061ee",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "blue",
                    "inverted": False,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="rdbst">Blue closable inline notification with icon.</p>',
            },
            "id": "721f74b1-da23-4dc5-9164-a65dbb19780d",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "purple",
                    "inverted": False,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="tx306">Purple inline notification with icon.</p>',
            },
            "id": "f3e02954-dbca-478b-9961-091ba5183a85",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "orange",
                    "inverted": False,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="gfhb3">Orange inline notification with icon.</p>',
            },
            "id": "d8118354-b7d8-47f2-ac0b-341694e176b4",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "yellow",
                    "inverted": False,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="cskk1">Yellow inline notification with icon.</p>',
            },
            "id": "3f3d0898-0f1a-4480-a257-eed2f694cab1",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "white",
                    "inverted": True,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="6mwr0">Inverted white inline notification with icon.</p>',
            },
            "id": "ebb81b57-25c3-419b-a722-6e37430650af",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "black",
                    "inverted": True,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="hjvwe">Black inverted inline notification with icon.</p>',
            },
            "id": "6da10bb3-ec21-4b19-8db8-472ba82394fb",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "blue",
                    "inverted": True,
                    "closable": False,
                    "show_to": "all",
                },
                "message": '<p data-block-key="n6fwc">Blue inverted inline notification with icon.</p>',
            },
            "id": "5eaef08e-9d5a-4bfa-a306-2051eef5b330",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "purple",
                    "inverted": True,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="lip62">Purple inverted closable inline notification with icon.</p>',
            },
            "id": "b7695df4-dcfd-4e8e-a834-b5ef32dcbf31",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "orange",
                    "inverted": True,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="c9os3">Inverted orange closable inline notification with icon.</p>',
            },
            "id": "94df6cc2-4c17-4244-a601-893afe2c9382",
        },
        {
            "type": "inline_notification",
            "value": {
                "settings": {
                    "icon": "user",
                    "color": "yellow",
                    "inverted": True,
                    "closable": True,
                    "show_to": "all",
                },
                "message": '<p data-block-key="q6e5n">Inverted yellow closable inline notification with icon.</p>',
            },
            "id": "d3029923-e6a7-40c2-9b87-e2f54b4cd975",
        },
    ]


def get_inline_notification_test_page() -> FreeFormPage:
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-inline-notifications-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-inline-notifications-page",
            title="Test Inline Notifications Page",
        )
        index_page.add_child(instance=page)

    page.content = get_inline_notification_variants()
    page.save_revision().publish()
    return page
