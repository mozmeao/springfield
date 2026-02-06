# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_banner_snippet, get_pre_footer_cta_form_snippet
from springfield.cms.models import ThanksPage


def get_step_cards():
    return [
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": None,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": "",
                "headline": '<p data-block-key="p1j6l">Open Firefox.dmg from your Downloads folder. </p>',
                "content": "",
                "buttons": [],
            },
            "id": "08a500f3-b13d-40ed-a212-01920cad2539",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": None,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": "",
                "headline": '<p data-block-key="p1j6l">Drag the Firefox icon into your Applications folder.</p>',
                "content": "",
                "buttons": [],
            },
            "id": "1521a9ad-8edd-4541-a9ca-af7dcfe63823",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": None,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": "",
                "headline": '<p data-block-key="p1j6l">Open your Applications folder and drag Firefox to your dock.</p>',
                "content": "",
                "buttons": [],
            },
            "id": "d9bb2e92-34d1-40a2-9b2d-bd4df9e53f49",
        },
    ]


def get_windows_section():
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "windows"},
            "heading": {
                "superheading_text": "Windows Users",
                "heading_text": '<p data-block-key="x4k4z">Thank you for downloading Firefox!</p>',
                "subheading_text": '<p data-block-key="hablc">This sections will only show to Windows users.</p>',
            },
            "content": [],
            "cta": [],
        },
        "id": "9304b845-491a-4a12-8be3-42c783504a4d",
    }


def get_linux_section():
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "linux"},
            "heading": {
                "superheading_text": "Linux Users",
                "heading_text": '<p data-block-key="x4k4z">Almost there!</p>',
                "subheading_text": '<p data-block-key="hablc">This sections will only show to Linux users.</p>',
            },
            "content": [],
            "cta": [],
        },
        "id": "9304b845-491a-4a12-8be3-42c783504a4d",
    }


def get_unsupported_section():
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "unsupported"},
            "heading": {
                "superheading_text": "Unsupported OS Users",
                "heading_text": '<p data-block-key="x4k4z">Your download was interrupted. But all is not lost.</p>',
                "subheading_text": '<p data-block-key="hablc">This sections will only show to Unsupported OS users.</p>',
            },
            "content": [],
            "cta": [],
        },
        "id": "9304b845-491a-4a12-8be3-42c783504a4d",
    }


def get_other_os_section():
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "other-os"},
            "heading": {
                "superheading_text": "Other OS Users",
                "heading_text": '<p data-block-key="x4k4z">Thank you for downloading Firefox!</p>',
                "subheading_text": '<p data-block-key="hablc">This sections will only show to Other OS users.</p>',
            },
            "content": [],
            "cta": [],
        },
        "id": "9304b845-491a-4a12-8be3-42c783504a4d",
    }


def get_mac_section():
    buttons = get_button_variants()

    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "osx"},
            "heading": {
                "superheading_text": "Mac Users",
                "heading_text": '<p data-block-key="x4k4z">Thank you for downloading Firefox!</p>',
                "subheading_text": '<p data-block-key="hablc">Follow these steps to get Firefox set up. </p>',
            },
            "content": [
                {
                    "type": "step_cards",
                    "value": {
                        "cards": get_step_cards(),
                    },
                    "id": "6c4804d1-4129-43cc-aba9-d9500c8e6b97",
                }
            ],
            "cta": [buttons["link"]],
        },
        "id": "9304b845-491a-4a12-8be3-42c783504a4d",
    }


def get_banner():
    banner = get_banner_snippet()
    return {
        "type": "banner_snippet",
        "value": banner.id,
        "id": "06205a14-6232-4fa6-bdf6-8899f15b1dbf",
    }


def get_download_support():
    return {"type": "download_support", "value": None, "id": "d3f5e8c4-3f4e-4c2e-9f4a-1c2b5e6d7f8a"}


def get_thanks_page() -> ThanksPage:
    index_page = get_2026_test_index_page()

    image, _, _, _ = get_placeholder_images()

    get_pre_footer_cta_form_snippet()

    content = [
        get_windows_section(),
        get_mac_section(),
        get_linux_section(),
        get_unsupported_section(),
        get_other_os_section(),
        get_download_support(),
        get_banner(),
    ]

    page = ThanksPage.objects.filter(slug="test-thanks-page").first()
    if not page:
        page = ThanksPage(
            slug="test-thanks-page",
            title="Thanks Page Test",
            content=content,
        )
        index_page.add_child(instance=page)

    page.platform = "linux"
    page.subheading = (
        '<p data-block-key="0b474f02">Every other major browser is owned by a company that makes money from your data. Firefox sets you free.</p>'
    )
    page.intro_footer_text = '<p data-block-key="intro-footer-text">Some note about the OS version.</p>'
    page.featured_image = image
    page.content = content
    page.save_revision().publish()
    return page
