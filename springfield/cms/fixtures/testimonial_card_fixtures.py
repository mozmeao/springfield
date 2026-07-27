# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Sample pages demonstrating testimonial-style Cards. These are not a separate card type —
# they are built on top of CardBlock (outline variant) with a card-testimonial content block inside.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images, with_fresh_ids
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
                "heading_text": f'<p data-block-key="tc26h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="tc26s">{subheading_text}</p>' if subheading_text else "",
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


def get_testimonial_card_variants() -> list[dict]:
    return [
        {
            "type": "card",
            "value": {
                "settings": {"variant": "outline", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="2026tc1c">Firefox gives me confidence that my browsing stays private. '
                            "I've recommended it to everyone on my team.</p>",
                            "attribution": '<p data-block-key="2026tc1a">Jane Smith</p>',
                            "attribution_role": '<p data-block-key="2026tc1r">Head of Privacy, Mozilla</p>',
                            "attribution_image": _IMAGE_VARIANTS,
                        },
                        "id": "2026tc01-0001-0000-0000-000000000001",
                    },
                ],
            },
            "id": "2026tc01-0000-0000-0000-000000000001",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "outline", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="2026tc2c">Switching to Firefox was the best decision I made for my online security. '
                            "The built-in protections are outstanding.</p>",
                            "attribution": '<p data-block-key="2026tc2a">Alex Johnson</p>',
                            "attribution_role": "",
                            "attribution_image": _EMPTY_IMAGE_VARIANTS,
                        },
                        "id": "2026tc01-0002-0000-0000-000000000001",
                    },
                ],
            },
            "id": "2026tc01-0000-0000-0000-000000000002",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "outline", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="2026tc3c">The performance improvements in Firefox'
                            " have made it my go-to browser for development work. Fast, private, and open source.</p>",
                            "attribution": '<p data-block-key="2026tc3a">Sam Rivera</p>',
                            "attribution_role": '<p data-block-key="2026tc3r">Software Engineer</p>',
                            "attribution_image": _IMAGE_VARIANTS,
                        },
                        "id": "2026tc01-0003-0000-0000-000000000001",
                    },
                ],
            },
            "id": "2026tc01-0000-0000-0000-000000000003",
        },
        {
            "type": "card",
            "value": {
                "settings": {"variant": "outline", "align": "start", "expand_link": False, "show_to": _SHOW_TO_ALL},
                "content": [
                    {
                        "type": "testimonial",
                        "value": {
                            "content": '<p data-block-key="2026tc4c">I cover privacy and tech policy, and Firefox'
                            " continues to lead the industry in respecting user rights. It's the standard I measure others against.</p>",
                            "attribution": '<p data-block-key="2026tc4a">Morgan Lee</p>',
                            "attribution_role": '<p data-block-key="2026tc4r">Journalist</p>',
                            "attribution_image": _EMPTY_IMAGE_VARIANTS,
                        },
                        "id": "2026tc01-0004-0000-0000-000000000001",
                    },
                ],
            },
            "id": "2026tc01-0000-0000-0000-000000000004",
        },
    ]


def get_testimonial_cards_sections() -> list[dict]:
    cards = get_testimonial_card_variants()
    return [
        _section(
            heading_text="Testimonial Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                _cards_list(cards[:3], block_id="2026tcs1-0000-0000-0000-000000000001"),
            ],
            section_id="2026ts01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Testimonial Cards - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                _cards_list(cards, block_id="2026tcs1-0000-0000-0000-000000000002"),
            ],
            section_id="2026ts01-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Testimonial Cards - Wide Container, 2 Columns",
            subheading_text="Wide container (1170px) with 2 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:2],
                    settings={"container_width": "wide", "cards_per_row": "2", "two_wide_xs": False},
                    block_id="2026tcs1-0000-0000-0000-000000000003",
                ),
            ],
            section_id="2026ts01-0000-0000-0000-000000000003",
        ),
        _section(
            heading_text="Testimonial Cards - Scroll",
            subheading_text="Horizontally scrollable card row.",
            content_blocks=[
                _cards_list(
                    cards * 2,
                    settings={"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
                    block_id="2026tcs1-0000-0000-0000-000000000004",
                ),
            ],
            section_id="2026ts01-0000-0000-0000-000000000004",
        ),
    ]


def get_testimonial_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-testimonial-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Card - Testimonial",
        },
    )

    sections = get_testimonial_cards_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>Sample of the <strong>Card block</strong> configured as a testimonial card. "
        "Use <code>variant=outline</code> and add a <em>Testimonial</em> content block inside the card to produce this layout.</p>"
        "<p>Testimonial Cards display user or critic quotes with attribution, optional avatars, and optional star ratings. Use them "
        "to surface social proof on product pages, plans pages, or the homepage.</p>"
        "<p>Use real quotes with verifiable attribution. Keep quotes short (1&ndash;2 sentences); long quotes get scanned past.</p>"
    )
    page.save_revision().publish()
    return page
