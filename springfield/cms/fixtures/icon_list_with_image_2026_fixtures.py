# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _section(heading_text, content_blocks, section_id, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="il2026h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="il2026s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def _list_item(icon, text, item_id):
    return {
        "type": "item",
        "value": {
            "icon": icon,
            "text": f'<p data-block-key="{item_id}">{text}</p>',
        },
        "id": item_id,
    }


def get_icon_list_with_image_variants() -> list[dict]:
    return [
        {
            "type": "icon_list_with_image",
            "value": {
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "list_items": [
                    _list_item("checkmark", "Block harmful trackers automatically", "il2026i1a"),
                    _list_item("lock", "Keep your passwords safe and synced", "il2026i1b"),
                    _list_item("shield", "Browse without leaving a trace", "il2026i1c"),
                ],
            },
            "id": "2026il01-0000-0000-0000-000000000001",
        },
        {
            "type": "icon_list_with_image",
            "value": {
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "list_items": [
                    _list_item("bookmark", "Save pages and sync across devices", "il2026i2a"),
                    _list_item("history", "Access your browsing history anywhere", "il2026i2b"),
                    _list_item("tab", "Manage tabs with ease", "il2026i2c"),
                    _list_item("extension", "Add extensions to customize your experience", "il2026i2d"),
                    _list_item("themes", "Personalize with themes", "il2026i2e"),
                ],
            },
            "id": "2026il01-0000-0000-0000-000000000002",
        },
    ]


def get_icon_list_with_image_sections() -> list[dict]:
    variants = get_icon_list_with_image_variants()
    return [
        _section(
            heading_text="Icon List with Image - 3 Items",
            subheading_text="The image is displayed alongside a list of icon and text items.",
            content_blocks=[variants[0]],
            section_id="2026ils1-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Icon List with Image - 5 Items",
            subheading_text="The list can contain any number of items.",
            content_blocks=[variants[1]],
            section_id="2026ils1-0000-0000-0000-000000000002",
        ),
    ]


def get_icon_list_with_image_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-icon-list-with-image-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Icon List with Image 2026")
        index_page.add_child(instance=page)

    sections = get_icon_list_with_image_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page
