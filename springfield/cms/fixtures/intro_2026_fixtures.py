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
        # Vertical layout (default), no media
        {
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
                    "heading_text": '<p data-block-key="i26h1">Intro without media</p>',
                    "subheading_text": '<p data-block-key="i26b1">Media isn\'t required on the intro block.</p>',
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000001",
        },
        # Media right layout, with image, anchor_id
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "right",
                    "slim": False,
                    "anchor_id": "intro-image-right",
                },
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
                    "heading_text": '<p data-block-key="i26h2">Intro with image (right)</p>',
                    "subheading_text": '<p data-block-key="i26b2">Switch to Dark Mode to see the alternative image.</p>',
                },
                "buttons": [buttons["secondary"], buttons["ghost"]],
            },
            "id": "2026int1-0000-0000-0000-000000000003",
        },
        # Media left layout, with image, slim
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "left",
                    "slim": True,
                    "anchor_id": "",
                },
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
                        "id": "2026int1-0000-0000-0000-000000000005",
                    }
                ],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h3">Intro with image (left, slim)</p>',
                    "subheading_text": '<p data-block-key="i26b3">Media is positioned to the left in slim layout.</p>',
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000006",
        },
        # Vertical layout with YouTube video and anchor_id
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "vertical",
                    "slim": False,
                    "anchor_id": "intro-video",
                },
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h4">Intro with YouTube video</p>',
                    "subheading_text": "",
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000004",
        },
        # Right layout with animation
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "right",
                    "slim": False,
                    "anchor_id": "",
                },
                "media": [videos["animation"]],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h5">Intro with animation</p>',
                    "subheading_text": '<p data-block-key="i26b5">Use an animation instead of a static image.</p>',
                },
                "buttons": [buttons["primary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000007",
        },
        # Left layout with QR code
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "left",
                    "slim": False,
                    "anchor_id": "intro-qr-code",
                },
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "2026int1-0000-0000-0000-000000000009",
                    }
                ],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="i26h6">Intro with QR code</p>',
                    "subheading_text": '<p data-block-key="i26b6">Scan the QR code to get started.</p>',
                },
                "buttons": [buttons["secondary"]],
            },
            "id": "2026int1-0000-0000-0000-000000000008",
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
