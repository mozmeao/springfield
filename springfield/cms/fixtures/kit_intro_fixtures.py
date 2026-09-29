# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_scroll_to_see_more_snippet
from springfield.cms.models import FreeFormPage2026

IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


def get_kit_intro_variants() -> list[dict]:
    buttons = get_button_variants()
    scroll_to_see_more_snippet = get_scroll_to_see_more_snippet()
    return [
        {
            "type": "kit_intro",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="ki26s3">New</p>',
                    "heading_text": '<p data-block-key="ki26h3">Kit Intro with two buttons</p>',
                    "subheading_text": "",
                },
                "buttons": [buttons["secondary"], buttons["ghost"]],
            },
            "id": "2026ki01-0000-0000-0000-000000000003",
        },
        {
            "type": "kit_intro",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="ki26s4">Media</p>',
                    "heading_text": '<p data-block-key="ki26h4">Kit Intro with media</p>',
                    "subheading_text": '<p data-block-key="ki26b4">The image sits below the buttons, flush with the rounded bottom edge.</p>',
                },
                "buttons": [buttons["primary"], buttons["link"]],
                "media": [
                    {
                        "type": "image",
                        "value": IMAGE_VARIANTS,
                        "id": "2026ki02-0000-0000-0000-000000000010",
                    }
                ],
            },
            "id": "2026ki02-0000-0000-0000-000000000003",
        },
        {
            "type": "kit_intro",
            "value": {
                "scroll_to_see_more_snippet": scroll_to_see_more_snippet.id,
                "heading": {
                    "superheading_text": '<p data-block-key="ki26s5">Media and scroll pill</p>',
                    "heading_text": '<p data-block-key="ki26h5">Kit Intro with media and a scroll pill</p>',
                    "subheading_text": '<p data-block-key="ki26b5">The Scroll To See More snippet sits on the bottom edge, over the image.</p>',
                },
                "buttons": [buttons["primary"]],
                "media": [
                    {
                        "type": "image",
                        "value": IMAGE_VARIANTS,
                        "id": "2026ki03-0000-0000-0000-000000000010",
                    }
                ],
            },
            "id": "2026ki03-0000-0000-0000-000000000003",
        },
    ]


def get_bottom_section() -> list[dict]:
    return {
        "type": "intro",
        "value": {
            "settings": {
                "layout": "vertical",
                "slim": False,
                "anchor_id": "",
            },
            "media": [],
            "heading": {
                "superheading_text": '<p data-block-key="i26s1">Firefox 2026</p>',
                "heading_text": '<p data-block-key="i26h1">Some content to fill out the space</p>',
                "subheading_text": '<p data-block-key="i26b1">The Kit Intro overflows and needs some content underneath.</p>',
            },
            "content": [],
        },
        "id": "2026int1-0000-0000-0000-000000000001",
    }


def get_kit_intro_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-kit-intro"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Kit Intro",
        },
    )

    content = [*get_kit_intro_variants(), get_bottom_section()]
    page.upper_content = content
    # Add the Kit Intro block data to the Content field despite the block not being allowed there
    # to test that it isn't rendered on the page
    page.content = content
    page.docs = (
        "<p>The Kit Intro block is the main component of our home page. We should avoid using it in other pages.</p>"
        "<p>With media, the block closes itself off: the image sits flush on a rounded bottom edge and the gradient "
        "glow stays inside it. A Scroll To See More snippet can be placed on that edge.</p>"
    )
    page.save_revision().publish()
    return page
