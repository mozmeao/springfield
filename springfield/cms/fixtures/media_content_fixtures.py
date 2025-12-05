# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants, get_cta_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage


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
                            "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        },
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Content Before, Media After</p>',
                "tags": tags[:3],
                "content": '<p data-block-key="4fkrh">The block is composed of text and media. '
                "You can also add tags between the Headline and the Content.</p>",
                "buttons": [
                    buttons["primary"],
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
                            "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        },
                        "id": "a086ca43-5ad4-4888-bf07-5b925b92ea77",
                    }
                ],
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Content <sup>After</sup>, Media <sub>Before</sub></p>',
                "tags": tags[3:6],
                "content": '<p data-block-key="4fkrh">More tag variations and some <b>richtext</b> formatting examples.</p>',
                "buttons": [
                    buttons["secondary"],
                ],
            },
            "id": "0b474f02-d3fd-4d86-83cd-c1bc4d7eadf0",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [videos["youtube"]],
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Video + Content</p>',
                "tags": tags[6:9],
                "content": '<p data-block-key="4fkrh">Add a Video instead of an image as the media element.</p>',
                "buttons": [
                    buttons["tertiary"],
                ],
            },
            "id": "6e56b431-f30f-43c9-8fed-3b74f50873f2",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
                "media": [videos["cdn"]],
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Video + Content Before</p>',
                "tags": tags[9:12],
                "content": '<p data-block-key="4fkrh">Add a Video instead of an image as the media element.</p>',
                "buttons": [
                    buttons["ghost"],
                ],
            },
            "id": "6e56b431-f30f-43c9-8fed-3b74f50873f2",
        },
    ]


def get_section_with_media_content_variants() -> dict:
    ctas = get_cta_variants()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
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
