# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.models import FreeFormPage2026


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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif01">With no color or icon, the notification uses the neutral default style.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif02">Purple signals general info; closable adds a dismiss button.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif03">Stacked places the icon above the message instead of beside it.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif04">Green signals success or confirmation; closable lets the user dismiss it.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif05">Green for success, stacked with the icon above the message.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif06">Orange signals a warning; leave it non-closable when the user must read it.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif07">Closable is ignored in stacked layout, so no close button appears.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif08">Red signals an error; closable lets the user dismiss it.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "message": '<p data-block-key="notif09">Red for errors, stacked with the icon above the message.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "headline": '<p data-block-key="notif10h">Important update</p>',
                "message": '<p data-block-key="notif10">Add a headline above the message to emphasize the alert.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "headline": '<p data-block-key="notif11h">Sign in to continue</p>',
                "message": '<p data-block-key="notif11">A headline plus a purple closable body the user can dismiss.</p>',
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
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                },
                "headline": '<p data-block-key="notif12h">Download complete</p>',
                "message": '<p data-block-key="notif12">A headline with a green stacked success message.</p>',
            },
            "id": "notif012-0000-0000-0000-000000000012",
        },
    ]


def get_notification_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-notifications-page",
        parent=index_page,
        defaults={
            "title": "Notifications",
        },
    )

    variants = get_notification_variants()
    page.upper_content = variants
    page.content = variants
    page.docs = (
        "<p>The Notification block displays a contextual alert &mdash; informational, success, warning, or error &mdash; with an "
        "optional icon, color, headline, and closability. Use it for time-sensitive messages, system status, or in-page guidance.</p>"
        "<p>Pick the color to match severity: purple for general info, green for success / confirmation, orange for warnings, red "
        "for errors. Mark &ldquo;closable&rdquo; when the message is dismissible per session; leave it false when the user must act on it "
        "before continuing.</p>"
    )
    page.save_revision().publish()
    return page
