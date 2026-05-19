# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_notification_variants() -> list[dict]:
    return [
        # Minimal: no icon, no color, not closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "",
                    "color": "",
                    "stacked": False,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif01">Simple notification with no color or icon.</p>',
            },
            "id": "notif001-0000-0000-0000-000000000001",
        },
        # Purple with icon, closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "single-user",
                    "color": "purple",
                    "stacked": False,
                    "closable": True,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif02">Purple closable notification with icon.</p>',
            },
            "id": "notif002-0000-0000-0000-000000000002",
        },
        # Purple stacked with icon
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "single-user",
                    "color": "purple",
                    "stacked": True,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif03">Purple stacked notification with icon.</p>',
            },
            "id": "notif003-0000-0000-0000-000000000003",
        },
        # Green with icon, closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "checkmark-circle-fill",
                    "color": "green",
                    "stacked": False,
                    "closable": True,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif04">Green closable notification with icon.</p>',
            },
            "id": "notif004-0000-0000-0000-000000000004",
        },
        # Green stacked with icon
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "checkmark-circle-fill",
                    "color": "green",
                    "stacked": True,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif05">Green stacked notification with icon.</p>',
            },
            "id": "notif005-0000-0000-0000-000000000005",
        },
        # Orange with icon, not closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "warning",
                    "color": "orange",
                    "stacked": False,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif06">Orange notification with warning icon.</p>',
            },
            "id": "notif006-0000-0000-0000-000000000006",
        },
        # Orange stacked with icon, closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "warning",
                    "color": "orange",
                    "stacked": True,
                    "closable": True,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif07">Orange stacked closable notification with warning icon.</p>',
            },
            "id": "notif007-0000-0000-0000-000000000007",
        },
        # Red with icon, closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "warning",
                    "color": "red",
                    "stacked": False,
                    "closable": True,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif08">Red closable notification with icon.</p>',
            },
            "id": "notif008-0000-0000-0000-000000000008",
        },
        # Red stacked with icon
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "warning",
                    "color": "red",
                    "stacked": True,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "message": '<p data-block-key="notif09">Red stacked notification with icon.</p>',
            },
            "id": "notif009-0000-0000-0000-000000000009",
        },
        # With headline, no color or icon
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "",
                    "color": "",
                    "stacked": False,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "headline": '<p data-block-key="notif10h">Important update</p>',
                "message": '<p data-block-key="notif10">Notification with headline and no color or icon.</p>',
            },
            "id": "notif010-0000-0000-0000-000000000010",
        },
        # With headline, purple, icon, closable
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "single-user",
                    "color": "purple",
                    "stacked": False,
                    "closable": True,
                    "show_to": _SHOW_TO_ALL,
                },
                "headline": '<p data-block-key="notif11h">Sign in to continue</p>',
                "message": '<p data-block-key="notif11">Purple closable notification with headline and icon.</p>',
            },
            "id": "notif011-0000-0000-0000-000000000011",
        },
        # With headline, stacked
        {
            "type": "notification",
            "value": {
                "settings": {
                    "icon": "checkmark-circle-fill",
                    "color": "green",
                    "stacked": True,
                    "closable": False,
                    "show_to": _SHOW_TO_ALL,
                },
                "headline": '<p data-block-key="notif12h">Download complete</p>',
                "message": '<p data-block-key="notif12">Green stacked notification with headline and icon.</p>',
            },
            "id": "notif012-0000-0000-0000-000000000012",
        },
    ]


def get_notification_test_page() -> FreeFormPage2026:
    index_page = get_2026_test_index_page()

    page = FreeFormPage2026.objects.filter(slug="test-notifications-page").first()
    if not page:
        page = FreeFormPage2026(
            slug="test-notifications-page",
            title="Test Notifications Page",
        )
        index_page.add_child(instance=page)

    variants = get_notification_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
