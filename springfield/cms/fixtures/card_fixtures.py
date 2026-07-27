# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images, with_fresh_ids
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}

_EMPTY_IMAGE_VARIANTS = {
    "image": None,
    "settings": {
        "dark_mode_image": None,
        "mobile_image": None,
        "dark_mode_mobile_image": None,
    },
}

_SETTINGS_DEFAULT = {"variant": "", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL}
_SETTINGS_OUTLINE = {"variant": "outline", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL}
_SETTINGS_FILLED = {"variant": "filled", "align": "center", "expand_link": False, "show_to": _SHOW_TO_ALL}
_SETTINGS_CENTER = {"variant": "", "align": "center", "expand_link": False, "show_to": _SHOW_TO_ALL}
_SETTINGS_END = {"variant": "", "align": "end", "expand_link": False, "show_to": _SHOW_TO_ALL}


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
                "heading_text": f'<p data-block-key="ch">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="cs">{subheading_text}</p>' if subheading_text else "",
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


def get_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        # Default variant — icon + heading + text + button
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_DEFAULT,
                "media": [{"type": "icon", "value": "globe", "id": "card0001-0000-0000-0000-000000000011"}],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="c01h1">Default Card with Icon</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000012",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c01c1">Default variant, start alignment, icon and button.</p>',
                        "id": "card0001-0000-0000-0000-000000000013",
                    },
                    {
                        "type": "buttons",
                        "value": {
                            "spacing": "",
                            "buttons": [buttons["primary"]],
                            "help_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000014",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000001",
        },
        # Outline variant — pictogram + heading + text
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_OUTLINE,
                "media": [],
                "content": [
                    {
                        "type": "pictogram",
                        "value": _IMAGE_VARIANTS,
                        "id": "card0001-0000-0000-0000-000000000021",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="c02h1">Outline Card with Pictogram</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000022",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c02c1">Outline variant with a pictogram displayed in a sticker-sized media area.</p>',
                        "id": "card0001-0000-0000-0000-000000000023",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000002",
        },
        # Filled variant — heading + pictogram + text + buttons (replaces sticker card use case)
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_FILLED,
                "media": [],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": '<p data-block-key="c03s1">Firefox</p>',
                            "heading_text": '<p data-block-key="c03h1">Filled Card</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000031",
                    },
                    {
                        "type": "pictogram",
                        "value": _IMAGE_VARIANTS,
                        "id": "card0001-0000-0000-0000-000000000035",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c03c1">Filled variant with superheading, pictogram, and buttons.</p>',
                        "id": "card0001-0000-0000-0000-000000000032",
                    },
                    {
                        "type": "buttons",
                        "value": {
                            "spacing": "",
                            "buttons": [buttons["primary"], buttons["secondary"]],
                            "help_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000033",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000003",
        },
        # Center alignment — media + heading + text
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_CENTER,
                "media": [
                    {
                        "type": "media",
                        "value": [{"type": "image", "value": _IMAGE_VARIANTS, "id": "card0001-0000-0000-0000-000000000041"}],
                        "id": "card0001-0000-0000-0000-000000000042",
                    }
                ],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="c04h1">Center-Aligned Card with Media</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000043",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c04c1">Center alignment with an image in the media block.</p>',
                        "id": "card0001-0000-0000-0000-000000000044",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000004",
        },
        # Testimonial content block — outlined card with a testimonial inside
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_OUTLINE,
                "media": [],
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="c05q1">Firefox gives me confidence that my browsing stays private.</p>',
                            "attribution": '<p data-block-key="c05a1">Jane Smith</p>',
                            "attribution_role": '<p data-block-key="c05r1">Head of Privacy, Mozilla</p>',
                            "attribution_image": _IMAGE_VARIANTS,
                        },
                        "id": "card0001-0000-0000-0000-000000000051",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000005",
        },
        # End alignment — tags + heading + text
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_END,
                "media": [],
                "content": [
                    {
                        "type": "tags_list",
                        "value": [
                            {"title": "Privacy", "icon": "eye-false", "icon_position": "before", "color": "purple"},
                            {"title": "Security", "icon": "lock", "icon_position": "before", "color": "green"},
                        ],
                        "id": "card0001-0000-0000-0000-000000000061",
                    },
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="c06h1">End-Aligned Card with Tags</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000062",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c06c1">End alignment with tags displayed above the heading.</p>',
                        "id": "card0001-0000-0000-0000-000000000063",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000006",
        },
        # Testimonial — no attribution image, no role
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_OUTLINE,
                "media": [],
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="c08q1">Switching to Firefox was the best decision I made for my online security.</p>',
                            "attribution": '<p data-block-key="c08a1">Alex Johnson</p>',
                            "attribution_role": "",
                            "attribution_image": _EMPTY_IMAGE_VARIANTS,
                        },
                        "id": "card0001-0000-0000-0000-000000000081",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000008",
        },
        # Testimonial — with image and role
        {
            "type": "card",
            "value": {
                "settings": _SETTINGS_OUTLINE,
                "media": [],
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="c09q1">The performance improvements in Firefox have'
                            " made it my go-to browser. Fast, private, and open source.</p>",
                            "attribution": '<p data-block-key="c09a1">Sam Rivera</p>',
                            "attribution_role": '<p data-block-key="c09r1">Software Engineer</p>',
                            "attribution_image": _IMAGE_VARIANTS,
                        },
                        "id": "card0001-0000-0000-0000-000000000091",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000009",
        },
        # Expand link — default with expand_link enabled
        {
            "type": "card",
            "value": {
                "settings": {"variant": "", "align": "start", "expand_link": True, "show_to": _SHOW_TO_ALL},
                "media": [{"type": "icon", "value": "shield", "id": "card0001-0000-0000-0000-000000000071"}],
                "content": [
                    {
                        "type": "heading",
                        "value": {
                            "superheading_text": "",
                            "heading_text": '<p data-block-key="c07h1">Clickable Card</p>',
                            "subheading_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000072",
                    },
                    {
                        "type": "content",
                        "value": '<p data-block-key="c07c1">Expand link enabled — the entire card is clickable.</p>',
                        "id": "card0001-0000-0000-0000-000000000073",
                    },
                    {
                        "type": "buttons",
                        "value": {
                            "spacing": "",
                            "buttons": [buttons["link"]],
                            "help_text": "",
                        },
                        "id": "card0001-0000-0000-0000-000000000074",
                    },
                ],
            },
            "id": "card0001-0000-0000-0000-000000000007",
        },
    ]


def get_card_sections() -> list[dict]:
    cards = get_card_variants()
    return [
        _section(
            heading_text="Card — Default, Outline, Filled Variants",
            subheading_text="Three variant options side by side.",
            content_blocks=[
                _cards_list(cards[:3], block_id="card0002-0000-0000-0000-000000000001"),
            ],
            section_id="card0003-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Card — Alignments and Expand Link",
            subheading_text="Center alignment, end alignment, and clickable card.",
            content_blocks=[
                _cards_list(
                    [cards[3], cards[5], cards[8]],
                    block_id="card0002-0000-0000-0000-000000000002",
                ),
            ],
            section_id="card0003-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Card — Testimonial Content Block",
            subheading_text="Outlined cards with a testimonial inside.",
            content_blocks=[
                _cards_list(
                    [cards[4], cards[6], cards[7]],
                    settings={"container_width": "", "cards_per_row": "3", "two_wide_xs": False},
                    block_id="card0002-0000-0000-0000-000000000003",
                ),
            ],
            section_id="card0003-0000-0000-0000-000000000003",
        ),
    ]


def get_card_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-card"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Card",
        },
    )

    sections = get_card_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>The Card block is a flexible, composable card that replaces most existing card types. "
        "Its content is built from a free-form stream of blocks (heading, icon, pictogram, media, "
        "tags, rich text, testimonial, buttons).</p>"
        "<p>Use the <strong>variant</strong> setting to choose between the default, outline, or filled appearance. "
        "Use <strong>align</strong> to control content alignment (start, center, end). "
        "Enable <strong>expand link</strong> to make the entire card clickable.</p>"
    )
    page.save_revision().publish()
    return page
