# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import get_smart_window_explainer_test_page
from springfield.cms.models.pages import SmartWindowPage

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}
_ANIMATION_URL = "https://assets.mozilla.net/video/red-pandas.webm"


def _animation_media(image_id, block_id=None):
    return {
        "type": "animation",
        "value": {
            "video_url": _ANIMATION_URL,
            "alt": "Lorem ipsum animation.",
            "poster": image_id,
            "playback": "autoplay_loop",
        },
        "id": block_id,
    }


def _heading(heading_text, superheading_text="", subheading_text=""):
    return {
        "superheading_text": f'<p data-block-key="swph">{superheading_text}</p>' if superheading_text else "",
        "heading_text": f'<p data-block-key="swphh">{heading_text}</p>',
        "subheading_text": f'<p data-block-key="swphs">{subheading_text}</p>' if subheading_text else "",
    }


def _section(heading_text, content_blocks, section_id, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": _SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="{section_id[:8]}h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="{section_id[:8]}s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def get_smart_window_sliding_carousel() -> dict:
    img = settings.PLACEHOLDER_IMAGE_ID
    dark = settings.PLACEHOLDER_DARK_IMAGE_ID
    slides = [
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Lorem ipsum dolor sit amet",
                    superheading_text="Lorem",
                    subheading_text="Consectetur adipiscing elit, sed do eiusmod tempor.",
                ),
                "media": [_animation_media(img, "swpsc01-0000-0000-0000-000000000010")],
            },
            "id": "swpsc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Sed do eiusmod tempor incididunt",
                    superheading_text="Ipsum",
                    subheading_text="Ut labore et dolore magna aliqua.",
                ),
                "media": [_animation_media(dark, "swpsc01-0000-0000-0000-000000000020")],
            },
            "id": "swpsc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Quis nostrud exercitation ullamco",
                    superheading_text="Dolor",
                    subheading_text="Duis aute irure dolor in reprehenderit.",
                ),
                "media": [_animation_media(img, "swpsc01-0000-0000-0000-000000000030")],
            },
            "id": "swpsc01-0000-0000-0000-000000000003",
        },
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
                "heading_text": "",
                "subheading_text": "",
            },
            "cards": [
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc1s">Lorem</p>',
                        "headline": '<p data-block-key="swplc1h">Lorem ipsum dolor sit amet</p>',
                        "content": '<p data-block-key="swplc1c">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod '
                        "tempor incididunt ut labore.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000001",
                },
                {
                    "type": "item",
                    "value": {
                        "superheading": '<p data-block-key="swplc2s">Ipsum</p>',
                        "headline": '<p data-block-key="swplc2h">Consectetur adipiscing elit</p>',
                        "content": '<p data-block-key="swplc2c">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi '
                        "ut aliquip.</p>",
                        "buttons": [],
                    },
                    "id": "swplc01-0000-0000-0000-000000000002",
                },
            ],
        },
        "id": "swplc01-0000-0000-0000-000000000001",
    }


def get_smart_window_illustration_cards() -> dict:
    img = settings.PLACEHOLDER_IMAGE_ID
    animation_cards = [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [_animation_media(img, "swpic01-0000-0000-0000-000000000011")],
                "eyebrow": '<p data-block-key="swpic1e">Lorem</p>',
                "headline": '<p data-block-key="swpic1h">Lorem ipsum dolor sit amet</p>',
                "content": '<p data-block-key="swpic1c">Consectetur adipiscing elit.</p>',
                "buttons": [],
            },
            "id": "swpic01-0000-0000-0000-000000000001",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [_animation_media(img, "swpic01-0000-0000-0000-000000000021")],
                "eyebrow": '<p data-block-key="swpic2e">Ipsum</p>',
                "headline": '<p data-block-key="swpic2h">Sed do eiusmod tempor incididunt</p>',
                "content": '<p data-block-key="swpic2c">Ut labore et dolore magna aliqua ut enim ad minim veniam.</p>',
                "buttons": [],
            },
            "id": "swpic01-0000-0000-0000-000000000002",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [_animation_media(img, "swpic01-0000-0000-0000-000000000031")],
                "eyebrow": '<p data-block-key="swpic3e">Dolor</p>',
                "headline": '<p data-block-key="swpic3h">Quis nostrud exercitation ullamco</p>',
                "content": '<p data-block-key="swpic3c">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore.</p>',
                "buttons": [],
            },
            "id": "swpic01-0000-0000-0000-000000000003",
        },
    ]
    return {
        "type": "cards_list",
        "value": {"cards": animation_cards},
        "id": "swpic01-0000-0000-0000-000000000001",
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
                "content": '<p data-block-key="swptc1c">Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt '
                "ut labore et dolore.</p>",
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
                "content": '<p data-block-key="swptc2c">Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut '
                "aliquip ex ea commodo.</p>",
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
                "content": '<p data-block-key="swptc3c">Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat.</p>',
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
                "content": '<p data-block-key="swptc4c">Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt '
                "mollit anim.</p>",
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
                "content": '<p data-block-key="swptc5c">Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>',
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
                "content": '<p data-block-key="swptc6c">Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque '
                "laudantium.</p>",
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
        _section(
            heading_text="Lorem ipsum dolor sit amet",
            content_blocks=[get_smart_window_line_cards()],
            section_id="swpsec1-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Consectetur adipiscing elit",
            content_blocks=[get_smart_window_illustration_cards()],
            section_id="swpsec2-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Sed do eiusmod tempor",
            content_blocks=[get_smart_window_testimonial_cards()],
            section_id="swpsec3-0000-0000-0000-000000000001",
        ),
    ]


def get_smart_window_test_page() -> SmartWindowPage:
    image, dark_image, _, _ = get_placeholder_images()
    explainer_page = get_smart_window_explainer_test_page()
    index_page = get_2026_test_index_page()

    slug = "test-smart-window"
    page = SmartWindowPage.objects.filter(slug=slug).first()
    if not page:
        page = SmartWindowPage(
            slug=slug,
            title="Test Smart Window",
            heading_text='<p data-block-key="swph">Lorem ipsum dolor sit amet</p>',
            subheading_text='<p data-block-key="swps">Consectetur adipiscing elit, sed do eiusmod tempor incididunt.</p>',
            image=image,
        )
        index_page.add_child(instance=page)

    page.heading_text = '<p data-block-key="swph">Lorem ipsum dolor sit amet</p>'
    page.subheading_text = '<p data-block-key="swps">Consectetur adipiscing elit, sed do eiusmod tempor incididunt.</p>'
    page.image = image
    page.image_dark_mode = dark_image
    page.animation = _ANIMATION_URL
    page.animation_alt = "Lorem ipsum animation."
    page.show_smart_window_button = "us_ca"
    page.redirect_page = explainer_page
    page.content = get_smart_window_page_content()
    page.save_revision().publish()
    return page
