# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage


def get_intro_variants() -> list[dict]:
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Simple Intro with text and button</p>',
                    "subheading_text": '<p data-block-key="png3s">When no image is provided, the Intro component gets a centralized layout.</p>',
                },
                "buttons": [
                    buttons["primary"],
                ],
            },
            "id": "a95b0d6d-861a-4a93-826b-f5db992e766e",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
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
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with image</p>',
                    "subheading_text": '<p data-block-key="png3s">Switch your browser to Dark Mode to see the alternative image.</p>',
                },
                "buttons": [
                    buttons["secondary"],
                ],
            },
            "id": "6e8994ca-1437-4f97-80e0-7e82d40e64d9",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "before"},
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
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with image before</p>',
                    "subheading_text": '<p data-block-key="png3s">Change the Intro layout in the settings field to position '
                    "the image before the content.</p>",
                },
                "buttons": [
                    buttons["tertiary"],
                ],
            },
            "id": "92d2e6a1-6116-4416-a449-e02cda310afb",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with YouTube Video</p>',
                    "subheading_text": '<p data-block-key="png3s">Add a Video instead of the image. '
                    "Use a YouTube video URL or a link to assets.mozilla.net.</p>",
                },
                "buttons": [buttons["ghost"]],
            },
            "id": "98b08efa-ddd2-4feb-b070-6a50781fc253",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "before"},
                "media": [videos["cdn"]],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with CDN Video</p>',
                    "subheading_text": '<p data-block-key="png3s">Add a Video instead of the image. '
                    "Use a YouTube video URL or a link to assets.mozilla.net.</p>",
                },
                "buttons": [buttons["primary"]],
            },
            "id": "98856064-26db-45eb-862f-e0e87a9c9736",
        },
        {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
                "media": [videos["animation"]],
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with Animation</p>',
                    "subheading_text": '<p data-block-key="png3s">Add an animation instead of the image. Use a link to assets.mozilla.net.</p>',
                },
                "buttons": [buttons["primary"]],
            },
            "id": "gbjweiof-26db-45eb-862f-e0e87a9c9736",
        },
    ]


def get_intro_test_page():
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-intro-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-intro-page",
            title="Test Intro Page",
        )
        index_page.add_child(instance=page)

    page.content = get_intro_variants()
    page.save_revision().publish()
    return page
