# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026


def get_kit_intro_2026_variants() -> list[dict]:
    buttons = get_button_variants()
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
            "buttons": [],
        },
        "id": "2026int1-0000-0000-0000-000000000001",
    }


def get_kit_intro_2026_test_page() -> FreeFormPage2026:
    index_page = get_2026_test_index_page()

    slug = "test-kit-intro-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Kit Intro 2026")
        index_page.add_child(instance=page)

    content = [*get_kit_intro_2026_variants(), get_bottom_section()]
    page.upper_content = content
    page.content = content
    page.save_revision().publish()
    return page
