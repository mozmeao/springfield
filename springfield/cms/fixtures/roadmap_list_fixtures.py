# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_test_index_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_variants
from springfield.cms.fixtures.whats_new_page_fixtures import get_whatsnew_index_page
from springfield.cms.models.pages import RoadmapPage

EMPTY_LINK = {
    "link_to": "",
    "page": None,
    "file": None,
    "custom_url": "",
    "anchor": "",
    "email": "",
    "phone": "",
    "new_window": False,
    "relative_url": "",
}


def make_link(url):
    return {
        "link_to": "custom_url",
        "page": None,
        "file": None,
        "custom_url": url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": False,
        "relative_url": "",
    }


def make_button(label, url, theme="", icon="", icon_position="right", analytics_id=""):
    """Create a button value for the buttons ListBlock."""
    return {
        "settings": {
            "theme": theme,
            "icon": icon,
            "icon_position": icon_position,
            "analytics_id": analytics_id,
        },
        "label": label,
        "link": make_link(url) if url else EMPTY_LINK,
    }


def get_roadmap_item_variants() -> list[dict]:
    return [
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - No icon, no buttons",
                "icon": "",
                "description": (
                    '<p data-block-key="rm01d">The description field accepts rich text. '
                    "This item uses the Exploring status, two platform tags (Android and iOS), "
                    "and no buttons — the minimal layout.</p>"
                ),
                "status": None,
                "tags": ["android", "ios"],
                "buttons": [],
            },
            "id": "rm0001-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - Icon and status",
                "icon": "activity",
                "description": (
                    '<p data-block-key="rm02d">The icon field is optional. When set, it appears above the title. '
                    "This item has a Learn More button and a primary button.</p>"
                ),
                "status": "exploring",
                "tags": ["desktop"],
                "buttons": [
                    make_button(
                        "Download Firefox",
                        "https://mozilla.org/download/",
                        theme="",
                        icon="forward",
                    ),
                    make_button(
                        "Learn more",
                        "https://mozilla.org/privacy/",
                        theme="ghost",
                        icon="forward",
                        analytics_id="rm0001-0000-0000-0000-000000000012",
                    ),
                ],
            },
            "id": "rm0001-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - Learn More button only",
                "icon": "shield",
                "description": (
                    '<p data-block-key="rm02d">The icon field is optional. When set, it appears above the title. '
                    "This item has a single Learn More button.</p>"
                ),
                "status": "in-progress",
                "tags": ["desktop"],
                "buttons": [
                    make_button(
                        "Learn more",
                        "https://mozilla.org/privacy/",
                        theme="ghost",
                        icon="forward",
                        analytics_id="rm0001-0000-0000-0000-000000000012",
                    )
                ],
            },
            "id": "rm0001-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - All three buttons",
                "icon": "sparkles",
                "description": (
                    '<p data-block-key="rm03d">This item has three buttons: a primary button, a secondary ghost button, and a Learn More button.</p>'
                ),
                "status": "testing",
                "tags": ["desktop", "android"],
                "buttons": [
                    make_button(
                        "Download Firefox",
                        "https://mozilla.org/download/",
                        theme="",
                        icon="forward",
                        analytics_id="rm0001-0000-0000-0000-000000000023",
                    ),
                    make_button(
                        "Secondary Button",
                        "https://mozilla.org/about/",
                        theme="ghost",
                    ),
                    make_button(
                        "Learn more",
                        "https://mozilla.org/features/ai/",
                        theme="ghost",
                        icon="forward",
                        analytics_id="rm0001-0000-0000-0000-000000000013",
                    ),
                ],
            },
            "id": "rm0001-0000-0000-0000-000000000004",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - All three platform tags, no buttons",
                "icon": "",
                "description": (
                    '<p data-block-key="rm04d">Tags are multi-select checkboxes: Android, iOS, and Desktop. '
                    "All three can be selected simultaneously. Buttons are fully optional.</p>"
                ),
                "status": "coming-soon",
                "tags": ["android", "ios", "desktop"],
                "buttons": [],
            },
            "id": "rm0001-0000-0000-0000-000000000005",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - No tags, Learn More button",
                "icon": "passkey",
                "description": (
                    '<p data-block-key="rm05d">Tags are optional — leaving them empty omits the tags list entirely. '
                    "The Learn More link is the only button here.</p>"
                ),
                "status": "recently-shipped",
                "tags": [],
                "buttons": [
                    make_button(
                        "Learn more",
                        "https://mozilla.org/security/passkeys/",
                        theme="ghost",
                        icon="forward",
                        analytics_id="rm0001-0000-0000-0000-000000000015",
                    )
                ],
            },
            "id": "rm0001-0000-0000-0000-000000000006",
        },
    ]


def get_roadmap_list_section_variants() -> list[dict]:
    items = get_roadmap_item_variants()
    return [
        {
            "type": "roadmap_list_section",
            "value": {
                "headline": "Roadmap List Section 1",
                "subheadline": "The subheadline field is optional. When set it renders as a paragraph beside the section headline.",
                "list_items": items,
            },
            "id": "rm0002-0000-0000-0000-000000000001",
        },
        {
            "type": "roadmap_list_section",
            "value": {
                "headline": "Roadmap List Section 2",
                "subheadline": "",
                "list_items": [items[0], items[2], items[3]],
            },
            "id": "rm0002-0000-0000-0000-000000000002",
        },
    ]


def get_roadmap_page_intro() -> list[dict]:
    return [
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "vertical",
                    "slim": True,
                    "anchor_id": "",
                },
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="rm00sh">Firefox Roadmap</p>',
                    "heading_text": '<p data-block-key="rm00h1">What\'s Next</p>',
                    "subheading_text": '<p data-block-key="rm00su">A transparent view into what we\'re building and why.</p>',
                },
                "content": [
                    {
                        "type": "buttons",
                        "id": "rm0000-0000-0000-0000-000000000002",
                        "value": [
                            {
                                "type": "button",
                                "value": {
                                    "settings": {
                                        "theme": "",
                                        "icon": "",
                                        "icon_position": "right",
                                        "analytics_id": "rm0000-0000-0000-0000-000000000002",
                                    },
                                    "label": "What's New",
                                    "link": {
                                        "link_to": "page",
                                        "page": get_whatsnew_index_page().id,
                                        "file": None,
                                        "custom_url": "",
                                        "anchor": "",
                                        "email": "",
                                        "phone": "",
                                        "new_window": False,
                                        "relative_url": "",
                                    },
                                },
                                "id": "rm0000-0000-0000-0000-000000000003",
                            }
                        ],
                    }
                ],
            },
            "id": "rm0000-0000-0000-0000-000000000001",
        }
    ]


def get_roadmap_list_test_page() -> RoadmapPage:
    index_page = get_test_index_page()
    slug = "test-roadmap-list"
    page = RoadmapPage.objects.filter(slug=slug).first()
    if not page:
        page = RoadmapPage(slug=slug, title="Test Roadmap List")
        index_page.add_child(instance=page)

    sections = get_roadmap_list_section_variants()
    page.intro = get_roadmap_page_intro()
    page.content = sections + [get_kit_banner_variants()[2]]
    page.save_revision().publish()
    page.refresh_from_db()
    return page
