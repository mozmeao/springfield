# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}


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
                "heading_text": f'<p data-block-key="ic26h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="ic26s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def get_icon_card_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "icon": "activity",
                "headline": '<p data-block-key="2026kc1h">Icon Card 2026</p>',
                "content": '<p data-block-key="2026kc1c">Without buttons, activity icon.</p>',
                "buttons": [],
            },
            "id": "2026kc01-0000-0000-0000-000000000001",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "icon": "android",
                "headline": '<p data-block-key="2026kc2h">Icon Card with Link Button</p>',
                "content": '<p data-block-key="2026kc2c">With a link button and android icon.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026kc01-0000-0000-0000-000000000002",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "icon": "apple",
                "headline": '<p data-block-key="2026kc3h">Clickable Icon Card</p>',
                "content": '<p data-block-key="2026kc3c">With expand link enabled - the entire card is clickable.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "2026kc01-0000-0000-0000-000000000003",
        },
        {
            "type": "icon_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "icon": "add-circle-fill",
                "headline": '<p data-block-key="2026kc4h">All Icon Card Fields</p>',
                "content": '<p data-block-key="2026kc4c">With all fields filled, expand link enabled, and primary button.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "2026kc01-0000-0000-0000-000000000004",
        },
    ]


def get_icon_cards_2026_sections() -> list[dict]:
    cards = get_icon_card_2026_variants()
    return [
        _section(
            heading_text="Icon Cards 2026 - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards[:3]},
                    "id": "2026kcs1-0000-0000-0000-000000000001",
                }
            ],
            section_id="2026ks01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Icon Cards 2026 - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards},
                    "id": "2026kcs1-0000-0000-0000-000000000002",
                }
            ],
            section_id="2026ks01-0000-0000-0000-000000000002",
        ),
    ]


def get_icon_cards_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-icon-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Icon Cards 2026")
        index_page.add_child(instance=page)

    sections = get_icon_cards_2026_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page
