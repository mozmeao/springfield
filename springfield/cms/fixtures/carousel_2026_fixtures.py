# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _image(image_id, dark_mode_image_id=None):
    return {
        "image": image_id,
        "settings": {
            "dark_mode_image": dark_mode_image_id,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }


def get_carousel_2026_variants() -> list[dict]:
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
                            "image": _image(settings.PLACEHOLDER_IMAGE_ID, settings.PLACEHOLDER_DARK_IMAGE_ID),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000011",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl2">Second slide</p>',
                            "image": _image(settings.PLACEHOLDER_DARK_IMAGE_ID),
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
                            "image": _image(settings.PLACEHOLDER_IMAGE_ID, settings.PLACEHOLDER_DARK_IMAGE_ID),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000021",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl4">Step two</p>',
                            "image": _image(settings.PLACEHOLDER_MOBILE_IMAGE_ID),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000022",
                    },
                    {
                        "type": "item",
                        "value": {
                            "headline": '<p data-block-key="ca26sl5">Step three</p>',
                            "image": _image(settings.PLACEHOLDER_DARK_IMAGE_ID),
                        },
                        "id": "2026ca01-0000-0000-0000-000000000023",
                    },
                ],
            },
            "id": "2026ca01-0000-0000-0000-000000000002",
        },
    ]


def get_carousel_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-carousel-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Carousel 2026")
        index_page.add_child(instance=page)

    variants = get_carousel_2026_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
