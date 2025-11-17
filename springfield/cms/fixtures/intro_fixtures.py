# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.models import FreeFormPage


def get_intro_variants():
    return {
        "basic": {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
                "image": None,
                "dark_image": None,
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Simple Intro with text and button</p>',
                    "subheading_text": '<p data-block-key="png3s">When no image is provided, the Intro component gets a centralized layout.</p>',
                },
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "",
                                "icon": "",
                                "icon_position": "right",
                                "analytics_id": "0d8d632a-7edb-42d1-98fa-cd10971288a2",
                            },
                            "label": "Click me",
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
                        "id": "91fb01ff-f5ee-4bbc-a3dd-0bdedbd7df51",
                    }
                ],
            },
            "id": "a95b0d6d-861a-4a93-826b-f5db992e766e",
        },
        "media_after": {
            "type": "intro",
            "value": {
                "settings": {"media_position": "after"},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with image</p>',
                    "subheading_text": '<p data-block-key="png3s">Switch your browser to Dark Mode to see the alternative image.</p>',
                },
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "",
                                "icon": "",
                                "icon_position": "right",
                                "analytics_id": "35eaf34f-cc36-4640-954e-63d371fade55",
                            },
                            "label": "Click me",
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
                        "id": "fe729072-77ce-40fd-b4c4-a01ecb470c9f",
                    }
                ],
            },
            "id": "6e8994ca-1437-4f97-80e0-7e82d40e64d9",
        },
        "media_before": {
            "type": "intro",
            "value": {
                "settings": {"media_position": "before"},
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "heading": {
                    "superheading_text": '<p data-block-key="ybdoh">Superheading text</p>',
                    "heading_text": '<p data-block-key="uzief">Intro with image before</p>',
                    "subheading_text": '<p data-block-key="png3s">Change the Intro layout in the settings field to position '
                    "the image before the content.</p>",
                },
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {
                                "theme": "",
                                "icon": "",
                                "icon_position": "right",
                                "analytics_id": "f62792df-ef80-4029-96fb-38d02053f2ea",
                            },
                            "label": "Click me",
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
                        "id": "638c4691-feee-4eaf-a314-42373138152d",
                    }
                ],
            },
            "id": "92d2e6a1-6116-4416-a449-e02cda310afb",
        },
    }


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

    page.content = list(get_intro_variants().values())
    page.save_revision().publish()
    return page
