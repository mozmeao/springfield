# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_2026_variants
from springfield.cms.models import FreeFormPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_kit_banner_variants():
    buttons = get_button_variants()
    tags = get_tag_2026_variants()
    return [
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-without-kit-image",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner without Kit Image</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a centered layout.</p>',
                },
                "tags": [tags["purple"]],
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "12a807da-2838-44b6-8a65-d9243059de02",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled",
                    "background_theme": "dark-purple-gradient",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "dark-purple-gradient-filled-banner-without-kit-image",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Dark Purple Gradient - Filled Banner without Kit Image</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a centered layout.</p>',
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "a7cc50a9-c4e4-4049-b9e4-c5f38c0644b2",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled-small",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-small-curious-kit",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner with Small Curious Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a centered layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "tags": [tags["orange"]],
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "1bc90319-cce6-4052-b181-5bff4c4a42c0",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled-large",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-large-curious-kit",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner with Large Curious Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "tags": [tags["purple"], tags["green"]],
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "607bd5fd-c2a8-41ef-a323-cf18da478ec4",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled-face",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-sitting-kit",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner with Sitting Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "tags": [tags["red"], tags["orange"]],
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "456a6d24-7ff7-4024-9f98-14bbbeae9e60",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled-tail",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-kit-tail",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner with Kit Tail</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "tags": [tags["green"]],
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "54ea6d6a-6490-4946-8caf-b5fba56d5a10",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {
                    "theme": "filled-curious-animation",
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "filled-banner-curious-animation",
                },
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner with Curious Kit Animation</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit animation is '
                    "placed on the right corner.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "54ea6d6a-6490-4946-8caf-b5fba56d5a10",
        },
    ]


def get_kit_banner_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    page = FreeFormPage2026.objects.filter(slug="test-kit-banner-2026-page").first()
    if not page:
        page = FreeFormPage2026(
            slug="test-kit-banner-2026-page",
            title="Test Kit Banner 2026 Page",
        )
        index_page.add_child(instance=page)

    variants = get_kit_banner_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
