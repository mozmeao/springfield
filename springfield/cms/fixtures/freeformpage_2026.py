# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026


def get_mobile_store_qr_code_variants():
    return {
        "with_heading": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="h1wh">Firefox on your phone</p>',
                    "subheading_text": '<p data-block-key="sh1wh">The browser you trust, built for life on the go.</p>',
                },
                "qr_code_data": "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        },
        "without_heading": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": "",
                    "subheading_text": "",
                },
                "qr_code_data": "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
            },
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        },
        "with_superheading_only": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="suph3">Firefox Mobile</p>',
                    "heading_text": "",
                    "subheading_text": "",
                },
                "qr_code_data": "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
            },
            "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        },
        "with_all_fields": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="suph4">Firefox Mobile</p>',
                    "heading_text": '<p data-block-key="h1h4">Firefox on your phone</p>',
                    "subheading_text": '<p data-block-key="sh1h4">The browser you trust, built for life on the go.</p>',
                },
                "qr_code_data": "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
            },
            "id": "d4e5f6a7-b8c9-0123-def0-234567890123",
        },
    }


def get_mobile_browsers_cards():
    image, _, _, _ = get_placeholder_images()
    image_value = {
        "image": image.id,
        "settings": {
            "dark_mode_image": None,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }
    link_button_settings = {
        "theme": "link",
        "icon": None,
        "icon_position": "right",
        "analytics_id": "",
    }
    return [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": image_value,
                "eyebrow": "",
                "headline": '<p data-block-key="android-h">Firefox for Android</p>',
                "content": '<p data-block-key="android-c">Private by default, with more ways to make Firefox your own on Android.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "11111111-1111-1111-1111-111111111111"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/android/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "11111111-1111-1111-1111-111111111112",
                    }
                ],
            },
            "id": "11111111-1111-1111-1111-111111111113",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": image_value,
                "eyebrow": "",
                "headline": '<p data-block-key="ios-h">Firefox for iOS</p>',
                "content": '<p data-block-key="ios-c">A more private way to browse on iPhone and iPad, with built-in tracking protection.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "22222222-2222-2222-2222-222222222221"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/ios/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "22222222-2222-2222-2222-222222222222",
                    }
                ],
            },
            "id": "22222222-2222-2222-2222-222222222223",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": image_value,
                "eyebrow": "",
                "headline": '<p data-block-key="focus-h">Firefox Focus</p>',
                "content": '<p data-block-key="focus-c">A fast, minimal browser that clears your history when you\'re done.</p>',
                "buttons": [
                    {
                        "type": "button",
                        "value": {
                            "settings": {**link_button_settings, "analytics_id": "33333333-3333-3333-3333-333333333331"},
                            "label": "Learn more",
                            "link": {
                                "link_to": "custom_url",
                                "page": None,
                                "file": None,
                                "custom_url": "/browsers/mobile/focus/",
                                "anchor": "",
                                "email": "",
                                "phone": "",
                                "new_window": False,
                            },
                        },
                        "id": "33333333-3333-3333-3333-333333333332",
                    }
                ],
            },
            "id": "33333333-3333-3333-3333-333333333333",
        },
    ]


def get_mobile_store_qr_code_test_page() -> FreeFormPage2026:
    index_page = get_2026_test_index_page()
    variants = get_mobile_store_qr_code_variants()

    slug = "mobile-store-qr-code"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Mobile Store QR Code Test",
        )
        index_page.add_child(instance=page)

    page.upper_content = [variants["with_heading"]]
    page.content = [
        variants["without_heading"],
        variants["with_superheading_only"],
        variants["with_all_fields"],
    ]
    page.save_revision().publish()
    return page


def get_freeform_page_2026_test_page() -> FreeFormPage2026:
    index_page = get_2026_test_index_page()
    variants = get_mobile_store_qr_code_variants()

    slug = "freeform-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(
            slug=slug,
            title="Free Form 2026 Test",
        )
        index_page.add_child(instance=page)

    page.upper_content = [variants["with_heading"]]
    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": "all", "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="sh1ff">Find the Firefox that fits you.</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "cards_list",
                        "value": {"cards": get_mobile_browsers_cards()},
                        "id": "44444444-4444-4444-4444-444444444444",
                    }
                ],
                "cta": [],
            },
            "id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
        },
    ]
    page.save_revision().publish()
    return page
