# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import heading_value, image_block
from springfield.cms.models import FreeFormPage2026


def get_sliding_carousel_slides() -> list[dict]:
    placeholder_images = get_placeholder_images()
    img = placeholder_images.image.id
    dark = placeholder_images.dark_image.id
    return [
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Protect your privacy across the web",
                    superheading_text="Privacy",
                    subheading_text="Control who can see your browsing activity.",
                    block_key="slca",
                ),
                "media": [image_block(image_id=img, dark_mode_image_id=dark, block_id="2026sc01-0000-0000-0000-0000000000a1")],
            },
            "id": "2026sc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Block trackers and ads automatically",
                    superheading_text="Security",
                    subheading_text="Enhanced Tracking Protection works out of the box.",
                    block_key="slca",
                ),
                "media": [image_block(image_id=dark, dark_mode_image_id=img, block_id="2026sc01-0000-0000-0000-0000000000a2")],
            },
            "id": "2026sc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Sync your data across all your devices",
                    superheading_text="Sync",
                    subheading_text="Bookmarks, passwords, and tabs — always with you.",
                    block_key="slca",
                ),
                "media": [image_block(image_id=img, block_id="2026sc01-0000-0000-0000-0000000000a3")],
            },
            "id": "2026sc01-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Browse faster with fewer interruptions",
                    superheading_text="Speed",
                    subheading_text="Firefox is built to be fast so you can get more done.",
                    block_key="slca",
                ),
                "media": [image_block(image_id=dark, dark_mode_image_id=img, block_id="2026sc01-0000-0000-0000-0000000000a4")],
            },
            "id": "2026sc01-0000-0000-0000-000000000004",
        },
        {
            "type": "item",
            "value": {
                "heading": heading_value(
                    heading_text="Make Firefox yours with themes and extensions",
                    superheading_text="Customise",
                    subheading_text="Thousands of add-ons let you tailor your browser experience.",
                    block_key="slca",
                ),
                "media": [image_block(image_id=img, dark_mode_image_id=dark, block_id="2026sc01-0000-0000-0000-0000000000a5")],
            },
            "id": "2026sc01-0000-0000-0000-000000000005",
        },
    ]


def get_sliding_carousel_variants() -> list[dict]:
    slides = get_sliding_carousel_slides()
    return [
        {
            "type": "sliding_carousel",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL},
                "slides": slides,
            },
            "id": "2026sc01-0000-0000-0000-000000000010",
        },
    ]


def get_sliding_carousel_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-sliding-carousel"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Sliding Carousel",
        },
    )

    variants = get_sliding_carousel_variants()
    page.upper_content = variants
    page.content = variants
    page.docs = (
        "<p>The Sliding Carousel block is a continuous-sliding variant of the Carousel. It&rsquo;s well suited for screenshot "
        "galleries, and any visual collection where continuous motion communicates &lsquo;more here&rsquo;.</p>"
        "<p>Keep slide content visually consistent (matching backgrounds, similar dimensions). Don&rsquo;t include CTAs inside "
        "sliding items &mdash; the motion makes them hard to click.</p>"
    )
    page.save_revision().publish()
    return page
