# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage


def get_banner_variants():
    buttons = get_button_variants()
    return [
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": False, "show_to": "all"},
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Simple Outlined Banner</p>',
                    "subheading_text": '<p data-block-key="bu3eb">A banner only needs the heading text. '
                    "If no media is provided, it uses the centered layout.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "2c12cf36-8c18-4033-9a76-d65d6103f7d9",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple", "media_after": False, "show_to": "all"},
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Simple Purple Banner</p>',
                    "subheading_text": '<p data-block-key="bu3eb">A banner only needs the heading text. '
                    "If no media is provided, it uses the centered layout.</p>",
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "a944ae4e-dfe9-44ab-9d7d-e297ff85a642",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": False, "show_to": "all"},
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
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Image</p>',
                    "subheading_text": '<p data-block-key="bu3eb">When media is provided, the banner uses a two column layout. '
                    "Switch between light and dark mode to see the alternative images.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "1ba272fb-9923-4472-821f-eb354571ab7d",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple", "media_after": False, "show_to": "all"},
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        },
                        "id": "d57af46b-c7e5-45cd-8768-a74a7e4b6514",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Image</p>',
                    "subheading_text": '<p data-block-key="bu3eb">When media is provided, the banner uses a two column layout. '
                    "Switch between light and dark mode to see the alternative images.</p>",
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "97eca46f-2bc5-4f6c-94ab-401657db7506",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": True, "show_to": "all"},
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        },
                        "id": "95c07ae8-1003-4e68-97a6-feff15840e57",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Image After</p>',
                    "subheading_text": '<p data-block-key="bu3eb">Check the <i>Media After</i> option to switch the layout.</p>',
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "2d9a535e-f9e9-4ed9-a873-a3dc38f5bb00",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple", "media_after": True, "show_to": "all"},
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "dark_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        },
                        "id": "a68f5e12-9c22-4f5b-ba6a-beb3e8e16bea",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Image After</p>',
                    "subheading_text": '<p data-block-key="bu3eb">Check the <i>Media After</i> option to switch the layout.</p>',
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "543e874d-b7b5-4872-8e0e-c3f99f8930f3",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": True, "show_to": "all"},
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "365c114f-b4da-4a55-a6a7-97e04b9ad1ae",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with QR Code</p>',
                    "subheading_text": '<p data-block-key="bu3eb">Add the QR code data and an image to use as the QR background.</p>',
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "798a2376-6a92-453e-a434-aee1fce1ee68",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple", "media_after": False, "show_to": "all"},
                "media": [
                    {
                        "type": "qr_code",
                        "value": {"data": "https://mozilla.org", "background": settings.PLACEHOLDER_IMAGE_ID},
                        "id": "5484df65-86c5-4fa4-b835-5870f6ca05ee",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with QR Code</p>',
                    "subheading_text": '<p data-block-key="bu3eb">Add the QR code data and an image to use as the QR background.</p>',
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "fc024170-e13d-462e-b626-1cfa55766486",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "outlined", "media_after": False, "show_to": "all"},
                "media": [
                    {
                        "type": "video",
                        "value": {
                            "video_url": "https://www.youtube.com/watch?v=F-nFQryDB0s&list=PLFlAJDI87Jg3WeEerUpaKQNaYoDlIwPbG",
                            "alt": "Describe the video here.",
                            "poster": settings.PLACEHOLDER_IMAGE_ID,
                        },
                        "id": "5d272340-402a-4f4c-9a4f-b4c308207452",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Outlined Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Outlined Banner with Video</p>',
                    "subheading_text": '<p data-block-key="bu3eb">You can add a video from YouTube or <a href="https://assets.mozilla.net">'
                    "Mozilla CDN</a>. The poster image will be displayed and swapped with the video once the user clicks the play button.</p>",
                },
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "83071a7f-253b-42ba-b3a2-70e52a83675e",
        },
        {
            "type": "banner",
            "value": {
                "settings": {"theme": "purple", "media_after": True, "show_to": "all"},
                "media": [
                    {
                        "type": "video",
                        "value": {
                            "video_url": "https://www.youtube.com/watch?v=F-nFQryDB0s&list=PLFlAJDI87Jg3WeEerUpaKQNaYoDlIwPbG",
                            "alt": "Describe the video here.",
                            "poster": settings.PLACEHOLDER_IMAGE_ID,
                        },
                        "id": "5bd338e8-aa03-4a03-8506-68124b4ad724",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="9gmqf">Purple Theme</p>',
                    "heading_text": '<p data-block-key="hhifz">Purple Banner with Video</p>',
                    "subheading_text": '<p data-block-key="bu3eb">You can add a video from YouTube or <a href="https://assets.mozilla.net">'
                    "Mozilla CDN</a>. The poster image will be displayed and swapped with the video once the user clicks the play button.</p>",
                },
                "buttons": [buttons["tertiary"], buttons["ghost"]],
            },
            "id": "e5bda829-e447-4398-b9d6-2228959ec021",
        },
    ]


def get_banner_test_page() -> FreeFormPage:
    get_placeholder_images()
    index_page = get_test_index_page()

    page = FreeFormPage.objects.filter(slug="test-banner-page").first()
    if not page:
        page = FreeFormPage(
            slug="test-banner-page",
            title="Test Banner Page",
        )
        index_page.add_child(instance=page)

    page.content = get_banner_variants()
    page.save_revision().publish()
    return page
