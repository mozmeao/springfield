# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage2026


def get_intro_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        {
            "type": "intro",
            "value": {
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="i26s1">Firefox 2026</p>',
                    "heading_text": '<p data-block-key="i26h1">Intro without media</p>',
                    "subheading_text": '<p data-block-key="i26b1">Media isn\'t required on the intro block.</p>',
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000001",
        },
        {
            "type": "intro",
            "value": {
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                                "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
                            },
                        },
                        "id": "2026int1-0000-0000-0000-000000000002",
                    }
                ],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h2">Intro with image</p>',
                    "subheading_text": '<p data-block-key="i26b2">Switch to Dark Mode to see the alternative image.</p>',
                },
                "buttons": [buttons["secondary"], buttons["ghost"]],
            },
            "id": "2026int1-0000-0000-0000-000000000003",
        },
        {
            "type": "intro",
            "value": {
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h3">Intro with YouTube video</p>',
                    "subheading_text": "",
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000004",
        },
    ]


def get_intro_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-intro-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Intro 2026")
        index_page.add_child(instance=page)

    variants = get_intro_2026_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
