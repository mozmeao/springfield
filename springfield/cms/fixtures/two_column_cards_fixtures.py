# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "alt_text": "",
    "variants": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


def _media(block_id):
    return {
        "type": "media",
        "value": [{"type": "image", "value": _IMAGE_VARIANTS, "id": f"{block_id}-img"}],
        "id": block_id,
    }


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
                "heading_text": f'<p data-block-key="{section_id}h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="{section_id}sub">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def _heading(heading_text, block_id, superheading_text="", subheading_text=""):
    return {
        "type": "heading",
        "value": {
            "superheading_text": f'<p data-block-key="{block_id}s">{superheading_text}</p>' if superheading_text else "",
            "heading_text": f'<p data-block-key="{block_id}h">{heading_text}</p>',
            "subheading_text": f'<p data-block-key="{block_id}sub">{subheading_text}</p>' if subheading_text else "",
        },
        "id": block_id,
    }


def _pricing_heading(heading_text, block_id, subheading_text="", superheading_text=""):
    return {
        "type": "pricing_heading",
        "value": {
            "superheading_text": f'<p data-block-key="{block_id}h">{superheading_text}</p>' if superheading_text else "",
            "heading_text": f'<p data-block-key="{block_id}h">{heading_text}</p>',
            "subheading_text": f'<p data-block-key="{block_id}sub">{subheading_text}</p>' if subheading_text else "",
        },
        "id": block_id,
    }


def _icon_list(items, block_id):
    return {
        "type": "icon_list",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "icon": item["icon"],
                        "text": f'<p data-block-key="{block_id}i{index}">{item["text"]}</p>',
                    },
                    "id": f"{block_id}i{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _numbered_list(items, block_id):
    return {
        "type": "numbered_list",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "heading": f'<p data-block-key="{block_id}h{index}">{item["heading"]}</p>',
                        "text": f'<p data-block-key="{block_id}t{index}">{item["text"]}</p>',
                    },
                    "id": f"{block_id}n{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _timeline(items, block_id):
    return {
        "type": "timeline",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "superheading_text": f'<p data-block-key="{block_id}s{index}">{item["superheading_text"]}</p>',
                        "heading_text": f'<p data-block-key="{block_id}h{index}">{item["heading_text"]}</p>',
                        "subheading_text": f'<p data-block-key="{block_id}sub{index}">{item["subheading_text"]}</p>',
                    },
                    "id": f"{block_id}ti{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _card(content_blocks, card_id, tag="", image_position=""):
    return {
        "type": "card",
        "value": {
            "settings": {"image_position": image_position},
            "tag": tag,
            "content": content_blocks,
        },
        "id": card_id,
    }


def _two_column_cards(cards, block_id, anchor_id="", theme="light-dark", reduce_card_padding=False):
    return {
        "type": "two_column_cards",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": anchor_id,
                "theme": theme,
                "reduce_card_padding": reduce_card_padding,
            },
            "cards": cards,
        },
        "id": block_id,
    }


def get_two_column_cards_variants() -> list[dict]:
    get_placeholder_images()
    buttons = get_button_variants()
    return [
        _section(
            "Light/Dark Theme",
            subheading_text="First card uses the light theme, second card uses the dark theme.",
            section_id="2026tcc-sec1-0000-0000-000000000001",
            content_blocks=[
                _two_column_cards(
                    anchor_id="plans",
                    theme="light-dark",
                    cards=[
                        _card(
                            tag="Light theme",
                            content_blocks=[
                                _heading(
                                    heading_text="Heading Block",
                                    block_id="tcc1-h1",
                                    superheading_text="Superheading",
                                    subheading_text="Subheading",
                                ),
                                _icon_list(
                                    items=[
                                        {"icon": "checkmark", "text": "Icon list items have an icon and a text field"},
                                        {"icon": "bookmark", "text": "Pick any icon from the icon library"},
                                        {"icon": "history", "text": "The button block fills the full width of the card"},
                                    ],
                                    block_id="tcc1-il1",
                                ),
                                {
                                    "type": "button_row",
                                    "id": "tcc1-btn1",
                                    "value": {
                                        "buttons": [
                                            dict(buttons["primary"], id="tcc1-btn1-inner"),
                                        ],
                                    },
                                },
                            ],
                            card_id="tcc1-card1",
                        ),
                        _card(
                            tag="Dark theme",
                            content_blocks=[
                                _heading(
                                    heading_text="Heading Block",
                                    block_id="tcc1-h2",
                                    superheading_text="Superheading",
                                    subheading_text="Subheading",
                                ),
                                _icon_list(
                                    items=[
                                        {"icon": "shield", "text": "In a light-dark theme, the second card uses the dark theme"},
                                        {"icon": "lock", "text": "The first card uses the light theme"},
                                        {"icon": "heart", "text": "In other themes, both cards use the same theme"},
                                    ],
                                    block_id="tcc1-il2",
                                ),
                                {
                                    "type": "button_row",
                                    "id": "tcc1-btn2",
                                    "value": {
                                        "buttons": [
                                            dict(buttons["primary"], id="tcc1-btn2-inner"),
                                        ],
                                    },
                                },
                            ],
                            card_id="tcc1-card2",
                        ),
                    ],
                    block_id="2026tcc1-0000-0000-0000-000000000001",
                ),
            ],
        ),
        _section(
            "Light/Light Theme",
            subheading_text="Both cards use the light theme.",
            section_id="2026tcc-sec1-0000-0000-000000000002",
            content_blocks=[
                _two_column_cards(
                    theme="light-light",
                    cards=[
                        _card(
                            content_blocks=[
                                _pricing_heading(
                                    "$ Heading",
                                    "tcc2-ph1",
                                    superheading_text="Light theme",
                                    subheading_text="Pricing heading block with a large font size and a border bottom",
                                ),
                                _numbered_list(
                                    items=[
                                        {"heading": "Numbered List", "text": "Each item has a heading and a body text field."},
                                        {"heading": "Step Two", "text": "Items are displayed as a stylized ordered list."},
                                        {"heading": "Step Three", "text": "Use it to walk users through a sequence of steps."},
                                    ],
                                    block_id="tcc2-nl1",
                                ),
                            ],
                            card_id="tcc2-card1",
                        ),
                        _card(
                            content_blocks=[
                                _pricing_heading(
                                    "$ Heading",
                                    "tcc2-ph2",
                                    superheading_text="Also light theme",
                                    subheading_text="The heading has a large font size and a border bottom",
                                ),
                                _timeline(
                                    items=[
                                        {
                                            "superheading_text": "Timeline",
                                            "heading_text": "Each item has a superheading, heading, and subheading",
                                            "subheading_text": "Items are displayed as a vertical timeline.",
                                        },
                                        {
                                            "superheading_text": "Item Two",
                                            "heading_text": "All three text fields are required",
                                            "subheading_text": "Use it to display a sequence of events or milestones.",
                                        },
                                        {
                                            "superheading_text": "Item Three",
                                            "heading_text": "2026",
                                            "subheading_text": "Last items on the timeline.",
                                        },
                                    ],
                                    block_id="tcc2-tl1",
                                ),
                            ],
                            card_id="tcc2-card2",
                        ),
                    ],
                    block_id="2026tcc1-0000-0000-0000-000000000002",
                ),
            ],
        ),
        _section(
            "Image Positions",
            subheading_text="Cards with full-top and bottom-right image positions.",
            section_id="2026tcc-sec1-0000-0000-000000000003",
            content_blocks=[
                _two_column_cards(
                    cards=[
                        _card(
                            tag="Full-top image",
                            image_position="full-top",
                            content_blocks=[
                                _media("tcc3-m1"),
                                _heading(
                                    heading_text="Media Block",
                                    block_id="tcc3-h1",
                                    superheading_text="Image position: full-top",
                                    subheading_text="The media block must be the first block when using a top position",
                                ),
                                _icon_list(
                                    items=[
                                        {"icon": "checkmark", "text": "Image stretches to the full width at the top of the card"},
                                        {"icon": "bookmark", "text": "Supports light/dark mode and mobile image variants"},
                                    ],
                                    block_id="tcc3-il1",
                                ),
                                {
                                    "type": "button_row",
                                    "id": "tcc3-btn1",
                                    "value": {
                                        "buttons": [
                                            dict(buttons["primary"], id="tcc3-btn1-inner"),
                                        ],
                                    },
                                },
                            ],
                            card_id="tcc3-card1",
                        ),
                        _card(
                            tag="Bottom-right image",
                            image_position="bottom-right",
                            content_blocks=[
                                _heading(
                                    heading_text="Media Block",
                                    block_id="tcc3-h2",
                                    superheading_text="Image position: bottom-right",
                                    subheading_text="The media block must be the last block when using a bottom position",
                                ),
                                _icon_list(
                                    items=[
                                        {"icon": "shield", "text": "Image is inset to the bottom-right corner of the card"},
                                        {"icon": "lock", "text": "Other positions: full-top, bottom-left, right, left"},
                                    ],
                                    block_id="tcc3-il2",
                                ),
                                {
                                    "type": "button_row",
                                    "id": "tcc3-btn2",
                                    "value": {
                                        "buttons": [
                                            dict(buttons["primary"], id="tcc3-btn2-inner"),
                                        ],
                                    },
                                },
                                _media("tcc3-m2"),
                            ],
                            card_id="tcc3-card2",
                        ),
                    ],
                    block_id="2026tcc1-0000-0000-0000-000000000003",
                    reduce_card_padding=True,
                ),
            ],
        ),
    ]


def get_two_column_cards_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    slug = "test-two-column-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Two Column Cards",
        },
    )

    variants = get_two_column_cards_variants()
    page.upper_content = variants
    page.content = variants
    page.docs = (
        "<p>The Two Column Cards block lays out cards in a strict two-column grid (vs. the responsive multi-column behavior of the "
        "Card Gallery). Use it when you want a deliberate side-by-side comparison or pairing.</p>"
        "<p>Provide an even number of cards so columns balance. The block reflows to a single column on small viewports &mdash; "
        "verify that the pairing relationship still reads when stacked.</p>"
    )
    page.save_revision().publish()
    return page
