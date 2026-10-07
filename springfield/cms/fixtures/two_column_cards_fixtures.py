# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import (
    heading_block,
    icon_list,
    numbered_list,
    pricing_heading_block,
    section,
    timeline,
    two_column_card,
    two_column_cards,
)
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026


def _media(block_id):
    placeholder_images = get_placeholder_images()
    image_variants = {
        "image": placeholder_images.image.id,
        "image_alt": "A numbered grid, standing in for a real image",
        "alt_text": "",
        "variants": {
            "dark_mode_image": placeholder_images.dark_image.id,
            "mobile_image": placeholder_images.mobile_image.id,
            "dark_mode_mobile_image": placeholder_images.dark_mobile_image.id,
        },
    }
    return {
        "type": "media",
        "value": [{"type": "image", "value": image_variants, "id": f"{block_id}-img"}],
        "id": block_id,
    }


def get_two_column_cards_variants() -> list[dict]:
    get_placeholder_images()
    buttons = get_button_variants()
    return [
        section(
            heading_text="Light/Dark Theme",
            subheading_text="First card uses the light theme, second card uses the dark theme.",
            section_id="2026tcc-sec1-0000-0000-000000000001",
            content_blocks=[
                two_column_cards(
                    anchor_id="plans",
                    theme="light-dark",
                    cards=[
                        two_column_card(
                            tag="Light theme",
                            content_blocks=[
                                heading_block(
                                    heading_text="Heading Block", block_id="tcc1-h1", superheading_text="Superheading", subheading_text="Subheading"
                                ),
                                icon_list(
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
                            block_id="tcc1-card1",
                        ),
                        two_column_card(
                            tag="Dark theme",
                            content_blocks=[
                                heading_block(
                                    heading_text="Heading Block", block_id="tcc1-h2", superheading_text="Superheading", subheading_text="Subheading"
                                ),
                                icon_list(
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
                            block_id="tcc1-card2",
                        ),
                    ],
                    block_id="2026tcc1-0000-0000-0000-000000000001",
                ),
            ],
        ),
        section(
            heading_text="Light/Light Theme",
            subheading_text="Both cards use the light theme.",
            section_id="2026tcc-sec1-0000-0000-000000000002",
            content_blocks=[
                two_column_cards(
                    theme="light-light",
                    cards=[
                        two_column_card(
                            content_blocks=[
                                pricing_heading_block(
                                    heading_text="$ Heading",
                                    block_id="tcc2-ph1",
                                    superheading_text="Light theme",
                                    subheading_text="Pricing heading block with a large font size and a border bottom",
                                ),
                                numbered_list(
                                    items=[
                                        {"heading": "Numbered List", "text": "Each item has a heading and a body text field."},
                                        {"heading": "Step Two", "text": "Items are displayed as a stylized ordered list."},
                                        {"heading": "Step Three", "text": "Use it to walk users through a sequence of steps."},
                                    ],
                                    block_id="tcc2-nl1",
                                ),
                            ],
                            block_id="tcc2-card1",
                        ),
                        two_column_card(
                            content_blocks=[
                                pricing_heading_block(
                                    heading_text="$ Heading",
                                    block_id="tcc2-ph2",
                                    superheading_text="Also light theme",
                                    subheading_text="The heading has a large font size and a border bottom",
                                ),
                                timeline(
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
                            block_id="tcc2-card2",
                        ),
                    ],
                    block_id="2026tcc1-0000-0000-0000-000000000002",
                ),
            ],
        ),
        section(
            heading_text="Image Positions",
            subheading_text="Cards with full-top and bottom-right image positions.",
            section_id="2026tcc-sec1-0000-0000-000000000003",
            content_blocks=[
                two_column_cards(
                    cards=[
                        two_column_card(
                            tag="Full-top image",
                            image_position="full-top",
                            content_blocks=[
                                _media("tcc3-m1"),
                                heading_block(
                                    heading_text="Media Block",
                                    block_id="tcc3-h1",
                                    superheading_text="Image position: full-top",
                                    subheading_text="The media block must be the first block when using a top position",
                                ),
                                icon_list(
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
                            block_id="tcc3-card1",
                        ),
                        two_column_card(
                            tag="Bottom-right image",
                            image_position="bottom-right",
                            content_blocks=[
                                heading_block(
                                    heading_text="Media Block",
                                    block_id="tcc3-h2",
                                    superheading_text="Image position: bottom-right",
                                    subheading_text="The media block must be the last block when using a bottom position",
                                ),
                                icon_list(
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
                            block_id="tcc3-card2",
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
        "<p>The Two Column Cards block lays out cards in a two-column grid. Use it when you want a deliberate side-by-side comparison or pairing. "
        "Besides the common heading, text, image, and button elements, it supports inner blocks appropriate for listing features: "
        "Numbered List, Timeline, and Icons List.</p>"
    )
    page.save_revision().publish()
    return page
