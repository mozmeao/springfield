# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.cards_2026_fixtures import get_illustration_card_2026_variants
from springfield.cms.fixtures.icon_cards_2026_fixtures import get_icon_card_2026_variants
from springfield.cms.fixtures.sliding_carousel_fixtures import get_sliding_carousel_slides
from springfield.cms.models.pages import SmartWindowPage

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}


def _image_media(image_id, dark_mode_image_id=None):
    return {
        "type": "image",
        "value": {
            "image": image_id,
            "settings": {
                "dark_mode_image": dark_mode_image_id,
                "mobile_image": None,
                "dark_mode_mobile_image": None,
            },
        },
        "id": None,
    }


def _heading(heading_text, superheading_text="", subheading_text=""):
    return {
        "superheading_text": f'<p data-block-key="swph">{superheading_text}</p>' if superheading_text else "",
        "heading_text": f'<p data-block-key="swphh">{heading_text}</p>',
        "subheading_text": f'<p data-block-key="swphs">{subheading_text}</p>' if subheading_text else "",
    }


def get_smart_window_sliding_carousel() -> dict:
    img = settings.PLACEHOLDER_IMAGE_ID
    dark = settings.PLACEHOLDER_DARK_IMAGE_ID
    slides = get_sliding_carousel_slides()
    # Add a 4th slide
    slides = slides + [
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Customize your browsing experience",
                    superheading_text="Personalization",
                    subheading_text="Thousands of extensions and themes to make Firefox yours.",
                ),
                "media": [_image_media(img, dark)],
            },
            "id": "swpsc01-0000-0000-0000-000000000004",
        }
    ]
    return {
        "type": "sliding_carousel",
        "value": {
            "settings": {"show_to": _SHOW_TO_ALL},
            "slides": slides,
        },
        "id": "swpsc01-0000-0000-0000-000000000001",
    }


def get_smart_window_line_cards() -> dict:
    return {
        "type": "line_cards",
        "value": {
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="swplch">Why Smart Window?</p>',
                "subheading_text": "",
            },
            "cards": [
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc1s">Productivity</p>',
                        "headline": '<p data-block-key="swplc1h">Work smarter across windows</p>',
                        "content": '<p data-block-key="swplc1c">Smart Window lets you arrange and switch between open tabs and windows with minimal '
                        "effort, keeping your focus where it matters.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000001",
                },
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc2s">Control</p>',
                        "headline": '<p data-block-key="swplc2h">Your layout, your rules</p>',
                        "content": '<p data-block-key="swplc2c">Drag, snap, and pin windows exactly where you want them. Smart Window gives you '
                        "precise control over your desktop workspace.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000002",
                },
            ],
        },
        "id": "swplc01-0000-0000-0000-000000000001",
    }


def get_smart_window_illustration_cards() -> dict:
    cards = get_illustration_card_2026_variants()[:3]
    return {
        "type": "cards_list",
        "value": {"cards": cards},
        "id": "swpic01-0000-0000-0000-000000000001",
    }


def get_smart_window_icon_cards() -> dict:
    cards = get_icon_card_2026_variants()[:3]
    return {
        "type": "cards_list",
        "value": {"cards": cards},
        "id": "swpkc01-0000-0000-0000-000000000001",
    }


def get_smart_window_testimonial_cards() -> dict:
    img = settings.PLACEHOLDER_IMAGE_ID
    dark = settings.PLACEHOLDER_DARK_IMAGE_ID
    _image = {
        "image": img,
        "settings": {
            "dark_mode_image": dark,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }
    _no_image = {
        "image": None,
        "settings": {
            "dark_mode_image": None,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }
    cards = [
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _image,
                "attribution": '<p data-block-key="swptc1a">Layla Hassan</p>',
                "attribution_role": '<p data-block-key="swptc1r">Product Designer</p>',
                "content": (
                    '<p data-block-key="swptc1c">Smart Window changed how I work. '
                    "I keep my research on one side and my design tool on the other "
                    "\u2014 no more alt-tabbing chaos.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000001",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _no_image,
                "attribution": '<p data-block-key="swptc2a">Marcus Osei</p>',
                "attribution_role": '<p data-block-key="swptc2r">Software Engineer</p>',
                "content": (
                    '<p data-block-key="swptc2c">I run documentation next to my terminal all day. '
                    "Smart Window snaps them perfectly without me thinking about it.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000002",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _image,
                "attribution": '<p data-block-key="swptc3a">Priya Nair</p>',
                "attribution_role": '<p data-block-key="swptc3r">Journalist</p>',
                "content": (
                    '<p data-block-key="swptc3c">Writing while fact-checking used to mean constant switching. '
                    "Smart Window lets me keep my sources visible while I type.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000003",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _no_image,
                "attribution": '<p data-block-key="swptc4a">Tom Reyes</p>',
                "attribution_role": "",
                "content": (
                    '<p data-block-key="swptc4c">Finally a browser feature that understands how people actually work. '
                    "My multitasking got significantly faster.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000004",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _image,
                "attribution": '<p data-block-key="swptc5a">Yuki Tanaka</p>',
                "attribution_role": '<p data-block-key="swptc5r">UX Researcher</p>',
                "content": (
                    '<p data-block-key="swptc5c">I tested Smart Window with dozens of users. '
                    "The consistent feedback: it just makes sense. The learning curve is nearly zero.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000005",
        },
        {
            "type": "testimonial_card",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "attribution_image": _no_image,
                "attribution": '<p data-block-key="swptc6a">Ana Ferreira</p>',
                "attribution_role": '<p data-block-key="swptc6r">Student</p>',
                "content": (
                    '<p data-block-key="swptc6c">Taking notes while watching lectures used to be painful. '
                    "Smart Window makes it effortless \u2014 both windows side by side, perfectly sized.</p>"
                ),
            },
            "id": "swptc01-0000-0000-0000-000000000006",
        },
    ]
    return {
        "type": "cards_list",
        "value": {
            "settings": {"scroll": True},
            "cards": cards,
        },
        "id": "swptc01-0000-0000-0000-000000000001",
    }


def get_smart_window_page_content() -> list[dict]:
    return [
        get_smart_window_sliding_carousel(),
        get_smart_window_line_cards(),
        get_smart_window_illustration_cards(),
        get_smart_window_icon_cards(),
        get_smart_window_testimonial_cards(),
    ]


def get_smart_window_test_page() -> SmartWindowPage:
    image, dark_image, _, _ = get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-smart-window"
    page = SmartWindowPage.objects.filter(slug=slug).first()
    if not page:
        page = SmartWindowPage(
            slug=slug,
            title="Test Smart Window",
            heading_text='<p data-block-key="swph">Introducing Smart Window</p>',
            subheading_text='<p data-block-key="swps">A smarter way to manage your browser windows and tabs.</p>',
            image=image,
            image_dark_mode=dark_image,
        )
        index_page.add_child(instance=page)

    page.heading_text = '<p data-block-key="swph">Introducing Smart Window</p>'
    page.subheading_text = '<p data-block-key="swps">A smarter way to manage your browser windows and tabs.</p>'
    page.image = image
    page.image_dark_mode = dark_image
    page.content = get_smart_window_page_content()
    page.save_revision().publish()
    return page
