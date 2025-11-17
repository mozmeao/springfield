# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.models import FreeFormPage


def get_media_content_variants():
    tags = list(get_tag_variants().values())
    return {
        "media_after": {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Content Before, Media After</p>',
                "tags": tags[:3],
                "content": '<p data-block-key="4fkrh">The block is composed of text and media. '
                "You can also add tags between the Headline and the Content.</p>",
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "secondary",
                                "icon": "arrow-right",
                                "icon_position": "right",
                                "analytics_id": "f37d7ddb-c457-49d2-b84c-3ef391f59d1b",
                            },
                            "label": "Secondary Button",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "https://mozilla.org",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "db648392-d8f9-4645-bbe1-eadfaeae6ba2",
                    }
                ],
            },
            "id": "e3320867-b02a-460d-8bab-492bfcaf1bd3",
        },
        "media_before": {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">Content <sup>After</sup>, Media <sub>Before</sub></p>',
                "tags": tags[3:6],
                "content": '<p data-block-key="4fkrh">More tag variations and some <b>richtext</b> formatting examples.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "tertiary",
                                "icon": "arrow-left",
                                "icon_position": "left",
                                "analytics_id": "6b0b1ae0-79d1-4fd1-9b37-64b8a9d29c90",
                            },
                            "label": "Tertiary Button",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "https://mozilla.org",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "87331f6d-8cc7-4a4f-b34f-d82d9b622e58",
                    }
                ],
            },
            "id": "0b474f02-d3fd-4d86-83cd-c1bc4d7eadf0",
        },
        "more_variations": {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "eyebrow": '<p data-block-key="jqkbk">Eyebrow</p>',
                "headline": '<p data-block-key="4h9nd">More tag and button variations</p>',
                "tags": tags[6:9],
                "content": '<p data-block-key="4fkrh">More tag variations and some <b>richtext</b> formatting examples.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "ghost",
                                "icon": "cloud",
                                "icon_position": "left",
                                "analytics_id": "c355159f-4335-4408-aaf9-bc688c94da3c",
                            },
                            "label": "Ghost Button",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "https://mozilla.org",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "88ec2fb0-a6b0-4d07-9278-c9afa8abadd5",
                    }
                ],
            },
            "id": "6e56b431-f30f-43c9-8fed-3b74f50873f2",
        },
    }


def get_section_with_media_content_variants():
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
            "heading": {
                "superheading_text": '<p data-block-key="d2q88">Media + Content</p>',
                "heading_text": '<p data-block-key="w8raa">Section with Media + Content Blocks and Call To Action</p>',
                "subheading_text": '<p data-block-key="0t2wn">Alternate the block settings with the media after and before.</p>',
            },
            "content": list(get_media_content_variants().values()),
            "cta": [
                {
                    "type": "item",
                    "value": {
                        "settings": {"analytics_id": "6cbbc05e-d7ad-4929-befc-410e1e26e776"},
                        "label": "Call To Action",
                        "link": {
                            "link_to": "custom_url",
                            "page": None,
                            "file": None,
                            "custom_url": "https://mozilla.org",
                            "anchor": "",
                            "email": "",
                            "phone": "",
                            "new_window": False,
                        },
                    },
                    "id": "4fd0adda-42ba-4ade-b63c-0208226696a4",
                }
            ],
        },
        "id": "48e69298-3f9b-4233-ad0b-b67b0fd14149",
    }


def get_media_content_test_page():
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
