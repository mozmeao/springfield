# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Sample pages demonstrating icon-style Cards. These are not a separate card type —
# they are built on top of CardBlock with icon content inside the card media area.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images, with_fresh_ids
from springfield.cms.fixtures.button_fixtures import get_button_variants
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
                "heading_text": f'<p data-block-key="ic26h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="ic26s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def _cards_list(cards, settings=None, block_id=""):
    return {
        "type": "cards_list",
        "value": {
            "settings": settings or {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
            "cards": cards,
        },
        "id": block_id,
    }


def get_icon_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "icon",
                        "value": {"icon": "activity"},
                        "id": "2026kc01-0001-0000-0000-000000000001",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="2026kc1h">Icon Card 2026</p>',
                            "subheading_text": "",
                        },
                        "id": "2026kc01-0001-0000-0000-000000000002",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="2026kc1c">Without buttons, activity icon.</p>',
                        "id": "2026kc01-0001-0000-0000-000000000003",
                    },
                ],
            },
            "id": "2026kc01-0000-0000-0000-000000000001",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "icon",
                        "value": {"icon": "android"},
                        "id": "2026kc01-0002-0000-0000-000000000001",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="2026kc2h">Icon Card with Link Button</p>',
                            "subheading_text": "",
                        },
                        "id": "2026kc01-0002-0000-0000-000000000002",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="2026kc2c">With a link button and android icon.</p>',
                        "id": "2026kc01-0002-0000-0000-000000000003",
                    },
                    {
                        "type": "buttons",
                        "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                        "id": "2026kc01-0002-0000-0000-000000000004",
                    },
                ],
            },
            "id": "2026kc01-0000-0000-0000-000000000002",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": True, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "icon",
                        "value": {"icon": "apple"},
                        "id": "2026kc01-0003-0000-0000-000000000001",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="2026kc3h">Clickable Icon Card</p>',
                            "subheading_text": "",
                        },
                        "id": "2026kc01-0003-0000-0000-000000000002",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="2026kc3c">With expand link enabled - the entire card is clickable.</p>',
                        "id": "2026kc01-0003-0000-0000-000000000003",
                    },
                    {
                        "type": "buttons",
                        "value": {"spacing": "", "buttons": [buttons["ghost"]], "help_text": ""},
                        "id": "2026kc01-0003-0000-0000-000000000004",
                    },
                ],
            },
            "id": "2026kc01-0000-0000-0000-000000000003",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": True, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "icon",
                        "value": {"icon": "add-circle-fill"},
                        "id": "2026kc01-0004-0000-0000-000000000001",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="2026kc4h">All Icon Card Fields</p>',
                            "subheading_text": "",
                        },
                        "id": "2026kc01-0004-0000-0000-000000000002",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="2026kc4c">With all fields filled, expand link enabled, and primary button.</p>',
                        "id": "2026kc01-0004-0000-0000-000000000003",
                    },
                    {
                        "type": "buttons",
                        "value": {"spacing": "", "buttons": [buttons["primary"]], "help_text": ""},
                        "id": "2026kc01-0004-0000-0000-000000000004",
                    },
                ],
            },
            "id": "2026kc01-0000-0000-0000-000000000004",
        },
    ]


def get_icon_cards_sections() -> list[dict]:
    cards = get_icon_card_variants()
    return [
        _section(
            heading_text="Icon Cards 2026 - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                _cards_list(cards[:3], block_id="2026kcs1-0000-0000-0000-000000000001"),
            ],
            section_id="2026ks01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Icon Cards 2026 - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                _cards_list(cards, block_id="2026kcs1-0000-0000-0000-000000000002"),
            ],
            section_id="2026ks01-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Icon Cards 2026 - Narrow Container, 2 Columns",
            subheading_text="Narrow container (725px) with 2 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:2],
                    settings={"container_width": "narrow", "cards_per_row": "2", "two_wide_xs": False},
                    block_id="2026kcs1-0000-0000-0000-000000000003",
                ),
            ],
            section_id="2026ks01-0000-0000-0000-000000000003",
        ),
        _section(
            heading_text="Icon Cards 2026 - Scroll",
            subheading_text="Horizontally scrollable card row.",
            content_blocks=[
                _cards_list(
                    cards * 2,
                    settings={"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
                    block_id="2026kcs1-0000-0000-0000-000000000004",
                ),
            ],
            section_id="2026ks01-0000-0000-0000-000000000004",
        ),
    ]


def get_icon_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-icon-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Card - Icon",
        },
    )

    sections = get_icon_cards_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>Sample of the <strong>Card block</strong> configured as an icon card. "
        "Add an <em>Icon</em> content block as the first item inside the card to produce this layout.</p>"
        "<p>Icon Cards present a small icon, a headline, and a short description. They&rsquo;re ideal for feature roundups, "
        "value-prop lists, and at-a-glance sections where you have many short items to surface.</p>"
        "<p>Stick to the supplied icon set so visual weight stays consistent. Keep descriptions to one or two short sentences so "
        "cards align visually in a grid.</p>"
    )
    page.save_revision().publish()
    return page
