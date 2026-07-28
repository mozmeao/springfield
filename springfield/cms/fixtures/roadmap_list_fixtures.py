# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page
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


def get_roadmap_item_variants() -> list[dict]:
    return [
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - No icon, no buttons, no status",
                "icon": "",
                "description": (
                    '<p data-block-key="rm01d">The description field accepts rich text. '
                    "This item uses the Exploring status, two platform tags (Android and iOS), "
                    "and no buttons — the minimal layout.</p>"
                ),
                "status": None,
                "tags": ["android", "ios"],
                "learn_more_link": EMPTY_LINK,
                "learn_more_analytics_id": "",
                "secondary_button_link": EMPTY_LINK,
                "secondary_button_icon": "",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "",
                "secondary_button_analytics_id": "",
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
                    "The Learn More button uses the localized ui-learn-more FTL string; "
                    "only the URL is provided here.</p>"
                ),
                "status": "exploring",
                "tags": ["desktop"],
                "learn_more_link": make_link("https://mozilla.org/privacy/"),
                "learn_more_analytics_id": "rm0001-0000-0000-0000-000000000012",
                "secondary_button_link": make_link("https://mozilla.org/download/"),
                "secondary_button_icon": "forward",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "Secondary Button Label",
                "secondary_button_analytics_id": "",
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
                    "The Learn More button uses the localized ui-learn-more FTL string; "
                    "only the URL is provided here.</p>"
                ),
                "status": "in-progress",
                "tags": ["desktop"],
                "learn_more_link": make_link("https://mozilla.org/privacy/"),
                "learn_more_analytics_id": "rm0001-0000-0000-0000-000000000012",
                "secondary_button_link": EMPTY_LINK,
                "secondary_button_icon": "",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "",
                "secondary_button_analytics_id": "",
            },
            "id": "rm0001-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "title": "Roadmap Item - Both buttons, secondary button has icon",
                "icon": "sparkles",
                "description": (
                    '<p data-block-key="rm03d">The secondary button has its own URL, label, icon, and icon position. '
                    "The icon position field controls whether it appears to the left or right of the label.</p>"
                ),
                "status": "testing",
                "tags": ["desktop", "android"],
                "learn_more_link": make_link("https://mozilla.org/features/ai/"),
                "learn_more_analytics_id": "rm0001-0000-0000-0000-000000000013",
                "secondary_button_link": make_link("https://mozilla.org/download/"),
                "secondary_button_icon": "forward",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "Secondary Button Label",
                "secondary_button_analytics_id": "rm0001-0000-0000-0000-000000000023",
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
                "learn_more_link": EMPTY_LINK,
                "learn_more_analytics_id": "",
                "secondary_button_link": EMPTY_LINK,
                "secondary_button_icon": "",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "",
                "secondary_button_analytics_id": "",
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
                    "The Learn More link is the only button here; the secondary button fields are left blank.</p>"
                ),
                "status": "recently-shipped",
                "tags": [],
                "learn_more_link": make_link("https://mozilla.org/security/passkeys/"),
                "learn_more_analytics_id": "rm0001-0000-0000-0000-000000000015",
                "secondary_button_link": EMPTY_LINK,
                "secondary_button_icon": "",
                "secondary_button_icon_position": "right",
                "secondary_button_label": "",
                "secondary_button_analytics_id": "",
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
                                    "pretranslated_label": None,
                                    "custom_label": "What's New",
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
    index_page = get_flare_pages_docs_page()
    slug = "test-roadmap-list"
    page = get_or_create_page(
        RoadmapPage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Roadmap List",
        },
    )

    sections = get_roadmap_list_section_variants()
    page.intro = get_roadmap_page_intro()
    page.content = sections + [get_kit_banner_variants()[2]]
    page.save_revision().publish()
    page.refresh_from_db()
    return page
