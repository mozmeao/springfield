# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.icon_cards_fixtures import get_icon_card_variants
from springfield.cms.fixtures.snippet_fixtures import get_scroll_to_see_more_snippet
from springfield.cms.models import FreeFormPage2026

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _text_section(heading_text: str, subheading_text: str, section_id: str) -> dict:
    """A plain section with only a heading, used to show the Featured Image block's rounded corners against a neighboring block."""
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": _SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="fists1h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="fists1s">{subheading_text}</p>',
            },
            "content": [],
            "cta": [],
        },
        "id": section_id,
    }


def get_featured_image_section_variants() -> list[dict]:
    icon_cards = get_icon_card_variants()
    return [
        {
            "type": "featured_image_section",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="fis1s">Featured</p>',
                    "heading_text": '<p data-block-key="fis1h">Featured Image Section with Cards</p>',
                    "subheading_text": '<p data-block-key="fis1sub">A featured image section with a card list below.</p>',
                },
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "fis00001-0000-0000-0000-000000000010",
                    }
                ],
                "content": [
                    {
                        "type": "cards_list",
                        "value": {
                            "settings": {"scroll": False},
                            "cards": icon_cards[:3],
                        },
                        "id": "fis00001-0000-0000-0000-000000000020",
                    }
                ],
            },
            "id": "fis00001-0000-0000-0000-000000000001",
        },
    ]


def get_featured_image_section_with_scroll_snippet_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()
    snippet = get_scroll_to_see_more_snippet()

    slug = "test-featured-image-section-with-scroll-snippet"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Test Featured Image Section with Scroll Snippet",
        },
    )

    variants = [
        {
            "type": "featured_image_section",
            "value": {
                "scroll_to_see_more_snippet": snippet.id,
                **get_featured_image_section_variants()[0]["value"],
            },
            "id": "fis00002-0000-0000-0000-000000000001",
        }
    ]
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page


def get_featured_image_section_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-featured-image-section"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Featured Image Section",
        },
    )

    featured_image_section = get_featured_image_section_variants()[0]
    page.upper_content = [featured_image_section]
    page.content = [
        _text_section(
            "Something before the block",
            "This shows how the Featured Image block adds the rounded corners to the bottom of the previous block.",
            "fis00003-0000-0000-0000-000000000001",
        ),
        {**featured_image_section, "id": "fis00003-0000-0000-0000-000000000002"},
        _text_section(
            "Something after the block",
            "Another block under the featured image creates this alternating effect on the page layout.",
            "fis00003-0000-0000-0000-000000000003",
        ),
    ]
    page.docs = (
        "<p>The Featured Image Section block pairs a prominent image with a heading and body copy. "
        "It is great for setting the mood and theme for a page, "
        "and emphasizes editorial storytelling over CTA-driven hero treatment.</p>"
        "<p>Choose imagery that adds context to the surrounding copy. The image&rsquo;s aspect ratio drives the section&rsquo;s vertical "
        "rhythm, so test on mobile before publishing.</p>"
        "<p>Use it either as a single block in the upper content section, or alternated with other blocks in the lower "
        "content section &mdash; consecutive Featured Image blocks against a contrasting block create the rounded-corner, "
        "alternating rhythm shown on this page.</p>"
    )
    page.save_revision().publish()
    return page
