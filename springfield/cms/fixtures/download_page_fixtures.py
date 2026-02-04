# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet
from springfield.cms.models import DownloadPage


def get_illustration_cards():
    buttons = get_button_variants()
    return [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": '<p data-block-key="4cj6k">AI</p>',
                "headline": '<p data-block-key="9elvq">Your favorite AI chatbot in your sidebar. </p>',
                "content": '<p data-block-key="hz26f">Conversations stay between you and your AI. </p>',
                "buttons": [buttons["link"]],
            },
            "id": "ff4dd11d-fdab-42ec-aab5-0f96984e401a",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": '<p data-block-key="4cj6k">Privacy</p>',
                "headline": '<p data-block-key="9elvq">Your data stays where it belongs — with you. </p>',
                "content": '<p data-block-key="hz26f">Firefox doesn’t exploit your data and is backed by a people-first foundation. </p>',
                "buttons": [buttons["link"]],
            },
            "id": "0d6a3510-a4ff-48b4-8c09-7c9d8bfb649e",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": '<p data-block-key="4cj6k">Independence</p>',
                "headline": '<p data-block-key="9elvq">Billionaire-free and open source for over 20 years. </p>',
                "content": '<p data-block-key="hz26f">Since 2004, Firefox has been the independent choice.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "3959911e-e9fa-40d6-a988-29c1b5e9fba8",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": "all", "image_after": False},
                "image": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "settings": {
                        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "eyebrow": '<p data-block-key="4cj6k">Organization</p>',
                "headline": '<p data-block-key="9elvq">Get organized. Stay organized.</p>',
                "content": '<p data-block-key="hz26f">Browse smarter with vertical tabs, tab groups, sidebar access, PDF editing, and AI chat.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "e659f716-d33d-4109-adb4-38dd0ac73257",
        },
    ]


def get_cards_list_section():
    buttons = get_button_variants()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="7tmxz">Work confidently. </p><p data-block-key="4tohn">Browse privately.</p>',
                "subheading_text": "",
            },
            "content": [
                {
                    "type": "cards_list",
                    "value": {
                        "cards": get_illustration_cards(),
                    },
                    "id": "94800c97-3058-4d91-97fc-e46b068c291c",
                }
            ],
            "cta": [buttons["ghost"]],
        },
        "id": "f69a5551-fe4c-4c06-be14-ae4f90e65d01",
    }


def get_pre_footer():
    snippet = get_pre_footer_cta_form_snippet()
    return {
        "type": "pre_footer_cta_form_snippet",
        "value": snippet.id,
        "id": "a02a8fd6-8195-43f1-a77d-ed6a652386b0",
    }


def get_download_page(platform) -> DownloadPage:
    index_page = get_2026_test_index_page()

    image, _, _, _ = get_placeholder_images()

    slug = f"test-download-page-{platform}"
    page = DownloadPage.objects.filter(slug=slug).first()
    if not page:
        page = DownloadPage(
            slug=slug,
            title=f"Download Page Test - {platform.capitalize()}",
        )
        index_page.add_child(instance=page)

    page.platform = platform
    page.subheading = (
        '<p data-block-key="0b474f02">Every other major browser is owned by a company that makes money from your data. Firefox sets you free.</p>'
    )
    page.intro_footer_text = '<p data-block-key="intro-footer-text">Some note about the OS version.</p>'
    page.featured_image = image
    page.content = [get_cards_list_section()]
    page.pre_footer = [get_pre_footer()]
    page.save_revision().publish()
    return page


def get_download_pages() -> dict:
    pages = {}
    for platform, _ in DownloadPage.PLATFORM_CHOICES:
        page = get_download_page(platform)
        pages[platform] = page
    return pages
