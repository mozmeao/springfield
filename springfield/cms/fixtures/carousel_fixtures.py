# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import image_value
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026


def get_carousel_variants() -> list[dict]:
    placeholder_images = get_placeholder_images()
    buttons = get_button_variants()
    return [
        # Minimal: no buttons, 2 slides
        {
            "type": "carousel",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="ca26h1">Carousel with two slides</p>',
                    "subheading_text": '<p data-block-key="ca26b1">The minimum number of slides is two.</p>',
                },
                "buttons": [],
                "slides": [
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl1">First slide</p>',
                            "image": image_value(image_id=placeholder_images.image.id, dark_mode_image_id=placeholder_images.dark_image.id),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000011",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl2">Second slide</p>',
                            "image": image_value(image_id=placeholder_images.dark_image.id),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000012",
                    },
                ],
            },
            "id": "2026ca01-0000-0000-0000-000000000001",
        },
        # With buttons, 3 slides
        {
            "type": "carousel",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL},
                "heading": {
                    "superheading_text": '<p data-block-key="ca26s2">Step by step</p>',
                    "heading_text": '<p data-block-key="ca26h2">Carousel with three slides and buttons</p>',
                    "subheading_text": "",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
                "slides": [
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl3">Step one</p>',
                            "image": image_value(image_id=placeholder_images.image.id, dark_mode_image_id=placeholder_images.dark_image.id),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000021",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl4">Step two</p>',
                            "image": image_value(image_id=placeholder_images.mobile_image.id),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000022",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl5">Step three</p>',
                            "image": image_value(image_id=placeholder_images.dark_image.id),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000023",
                    },
                ],
            },
            "id": "2026ca01-0000-0000-0000-000000000002",
        },
    ]


def get_carousel_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-carousel"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Carousel",
        },
    )

    variants = get_carousel_variants()
    page.upper_content = variants
    page.content = variants
    page.docs = (
        "<p>The Carousel block displays a sequence of slides, each with media and a short heading. "
        "Use it for testimonials, feature highlights, or any set of equal-weight items where the user benefits from controlled pacing.</p>"
        "<p>Avoid putting critical CTAs inside carousel slides &mdash; users often skip past them. Limit slides to 3&ndash;4; longer "
        "carousels lose engagement. Always provide alt text on slide media so the block remains accessible.</p>"
    )
    page.save_revision().publish()
    return page
