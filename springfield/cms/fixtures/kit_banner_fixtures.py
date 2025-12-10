# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage


def get_kit_banner_variants():
    buttons = get_button_variants()
    return [
        {
            "type": "kit_banner",
            "value": {
                "settings": {"theme": "filled", "show_to": "all"},
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner without Kit Image</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a centered layout.</p>',
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "12a807da-2838-44b6-8a65-d9243059de02",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {"theme": "filled-small", "show_to": "all"},
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner Small Curious Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a centered layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "1bc90319-cce6-4052-b181-5bff4c4a42c0",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {"theme": "filled-large", "show_to": "all"},
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner Large Curious Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "607bd5fd-c2a8-41ef-a323-cf18da478ec4",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {"theme": "filled-face", "show_to": "all"},
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner Sitting Kit</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "456a6d24-7ff7-4024-9f98-14bbbeae9e60",
        },
        {
            "type": "kit_banner",
            "value": {
                "settings": {"theme": "filled-tail", "show_to": "all"},
                "heading": {
                    "superheading_text": '<p data-block-key="zg8yr">Kit Banner</p>',
                    "heading_text": '<p data-block-key="xgfrq">Filled Banner Kit Tail</p>',
                    "subheading_text": '<p data-block-key="84om5">The banner uses a left aligned layout and the Kit image is '
                    "placed on the right corner.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "54ea6d6a-6490-4946-8caf-b5fba56d5a10",
        },
    ]


def get_kit_banner_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-kit-banner-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-kit-banner-page",
            title="Test Kit Banner Page",
        )
        index_page.add_child(instance=page)

    page.content = get_kit_banner_variants()
    page.save_revision().publish()
    return page
