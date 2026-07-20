# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def get_tag_variants():
    return {
        "purple": {
            "type": "item",
            "value": {"title": "Privacy", "icon": "lock", "icon_position": "before", "color": "purple"},
            "id": "2026tag1-0000-0000-0000-000000000001",
        },
        "red": {
            "type": "item",
            "value": {"title": "Security", "icon": "warning", "icon_position": "before", "color": "red"},
            "id": "2026tag1-0000-0000-0000-000000000002",
        },
        "orange": {
            "type": "item",
            "value": {"title": "Mobile", "icon": "android", "icon_position": "before", "color": "orange"},
            "id": "2026tag1-0000-0000-0000-000000000003",
        },
        "green": {
            "type": "item",
            "value": {"title": "Open Source", "icon": "edit-active", "icon_position": "after", "color": "green"},
            "id": "2026tag1-0000-0000-0000-000000000004",
        },
    }
