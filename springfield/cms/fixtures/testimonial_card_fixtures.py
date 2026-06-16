# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}

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


def get_testimonial_card_variants() -> list[dict]:
    return [
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _IMAGE_VARIANTS,
                "attribution": '<p data-block-key="2026tc1a">Jane Smith</p>',
                "attribution_role": '<p data-block-key="2026tc1r">Head of Privacy, Mozilla</p>',
                "content": '<p data-block-key="2026tc1c">Firefox gives me confidence that my browsing stays private. '
                "I've recommended it to everyone on my team.</p>",
            },
            "id": "2026tc01-0000-0000-0000-000000000001",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _EMPTY_IMAGE_VARIANTS,
                "attribution": '<p data-block-key="2026tc2a">Alex Johnson</p>',
                "attribution_role": "",
                "content": '<p data-block-key="2026tc2c">Switching to Firefox was the best decision I made for my online security. '
                "The built-in protections are outstanding.</p>",
            },
            "id": "2026tc01-0000-0000-0000-000000000002",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _IMAGE_VARIANTS,
                "attribution": '<p data-block-key="2026tc3a">Sam Rivera</p>',
                "attribution_role": '<p data-block-key="2026tc3r">Software Engineer</p>',
                "content": '<p data-block-key="2026tc3c">The performance improvements in Firefox have made it my go-to browser for development work.'
                " Fast, private, and open source.</p>",
            },
            "id": "2026tc01-0000-0000-0000-000000000003",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _EMPTY_IMAGE_VARIANTS,
                "attribution": '<p data-block-key="2026tc4a">Morgan Lee</p>',
                "attribution_role": '<p data-block-key="2026tc4r">Journalist</p>',
                "content": '<p data-block-key="2026tc4c">I cover privacy and tech policy, and Firefox continues to lead the industry in respecting '
                "user rights. It's the standard I measure others against.</p>",
            },
            "id": "2026tc01-0000-0000-0000-000000000004",
        },
    ]


def _cards_list(cards, settings=None, block_id=""):
    return {
        "type": "cards_list",
        "value": {
            "settings": settings or {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
            "cards": cards,
        },
        "id": block_id,
    }


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
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Testimonial Cards")
        index_page.add_child(instance=page)

    sections = get_testimonial_cards_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page
