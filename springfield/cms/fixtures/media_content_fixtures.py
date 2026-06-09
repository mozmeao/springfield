# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants, get_cta_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_media_content_variants() -> list[dict]:
    tags = list(get_tag_variants().values())
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
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
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Content Before, Media After</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010001-0000-0000-0000-000000000001", "value": tags[:3]},
                    {
                        "type": "rich_text",
                        "id": "c1a2b3c4-d5e6-7890-abcd-ef1234567890",
                        "value": '<p data-block-key="4fkrh">The block is composed of text and media. '
                        "You can also add tags between the Headline and the Content.</p>",
                    },
                    {"type": "buttons", "id": "00010001-0000-0000-0000-000000000002", "value": [buttons["primary"]]},
                ],
            },
            "id": "e3320867-b02a-460d-8bab-492bfcaf1bd3",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
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
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Content <sup>After</sup>, Media <sub>Before</sub></p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010002-0000-0000-0000-000000000001", "value": tags[3:6]},
                    {
                        "type": "rich_text",
                        "id": "d2b3c4d5-e6f7-8901-bcde-f12345678901",
                        "value": '<p data-block-key="4fkrh">More tag variations and some <b>richtext</b> formatting examples.</p>',
                    },
                    {"type": "buttons", "id": "00010002-0000-0000-0000-000000000002", "value": [buttons["secondary"]]},
                ],
            },
            "id": "0b474f02-d3fd-4d86-83cd-c1bc4d7eadf0",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Video + Content</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010003-0000-0000-0000-000000000001", "value": tags[6:9]},
                    {
                        "type": "rich_text",
                        "id": "e3c4d5e6-f7a8-9012-cdef-123456789012",
                        "value": '<p data-block-key="4fkrh">Add a Video instead of an image as the media element.</p>',
                    },
                    {"type": "buttons", "id": "00010003-0000-0000-0000-000000000002", "value": [buttons["tertiary"]]},
                ],
            },
            "id": "6e56b431-f30f-43c9-8fed-3b74f50873f2",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
                "media": [videos["cdn"]],
                "heading": {
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Video + Content Before</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010004-0000-0000-0000-000000000001", "value": tags[9:12]},
                    {
                        "type": "rich_text",
                        "id": "f4d5e6f7-a8b9-0123-defa-234567890123",
                        "value": '<p data-block-key="4fkrh">Add a Video instead of an image as the media element.</p>',
                    },
                    {"type": "buttons", "id": "00010004-0000-0000-0000-000000000002", "value": [buttons["ghost"]]},
                ],
            },
            "id": "98b08efa-ddd2-4feb-b070-6a50781fc253",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [videos["animation"]],
                "heading": {
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Animation Autoplay Loop</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010005-0000-0000-0000-000000000001", "value": tags[:3]},
                    {
                        "type": "rich_text",
                        "id": "a5e6f7a8-b9c0-1234-efab-345678901234",
                        "value": '<p data-block-key="4fkrh">Animation with autoplay loop (default). Plays continuously.</p>',
                    },
                    {"type": "buttons", "id": "00010005-0000-0000-0000-000000000002", "value": [buttons["ghost"]]},
                ],
            },
            "id": "7e56b431-f30f-43c9-8fed-3b74f50873f2",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [videos["animation_autoplay_once"]],
                "heading": {
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">Animation Autoplay Once</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010006-0000-0000-0000-000000000001", "value": tags[:3]},
                    {
                        "type": "rich_text",
                        "id": "b6f7a8b9-c0d1-2345-fabc-456789012345",
                        "value": '<p data-block-key="4fkrh">Animation with autoplay once. Plays on load then shows poster and play button.</p>',
                    },
                    {"type": "buttons", "id": "00010006-0000-0000-0000-000000000002", "value": [buttons["ghost"]]},
                ],
            },
            "id": "a7262a66-eefb-4ae1-90ae-ab85a1e4acf5",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "5484df65-86c5-4fa4-b835-5870f6ca05ee",
                    },
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="jqkbk">Eyebrow</p>',
                    "heading_text": '<p data-block-key="4h9nd">QR Code + Content Before</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "00010007-0000-0000-0000-000000000001", "value": tags[3:6]},
                    {
                        "type": "rich_text",
                        "id": "c7a8b9c0-d1e2-3456-abcd-567890123456",
                        "value": '<p data-block-key="4fkrh">Add a QR Code instead of an image as the media element.</p>',
                    },
                    {"type": "buttons", "id": "00010007-0000-0000-0000-000000000002", "value": [buttons["primary"]]},
                ],
            },
            "id": "38b08efa-ddd2-4feb-b070-6a50781fc253",
        },
    ]


def get_section_with_media_content_variants() -> dict:
    ctas = get_cta_variants()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": "section-with-media-content"},
            "heading": {
                "superheading_text": '<p data-block-key="d2q88">Media + Content</p>',
                "heading_text": '<p data-block-key="w8raa">Section with Media + Content Blocks and Call To Action</p>',
                "subheading_text": '<p data-block-key="0t2wn">Alternate the block settings with the media after and before.</p>',
            },
            "content": get_media_content_variants(),
            "cta": [ctas["basic"]],
        },
        "id": "48e69298-3f9b-4233-ad0b-b67b0fd14149",
    }


def get_media_content_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-media-content-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-media-content-page",
            title="Test Media Content Page",
        )
        index_page.add_child(instance=page)

    page.content = [get_section_with_media_content_variants()]
    page.save_revision().publish()
    return page
