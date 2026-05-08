# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "alt_text": "",
    "variants": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


def _media(block_id):
    return {
        "type": "media",
        "value": [{"type": "image", "value": _IMAGE_VARIANTS, "id": f"{block_id}-img"}],
        "id": block_id,
    }


_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _heading(heading_text, block_id, superheading_text="", subheading_text=""):
    return {
        "type": "heading",
        "value": {
            "superheading_text": f'<p data-block-key="{block_id}s">{superheading_text}</p>' if superheading_text else "",
            "heading_text": f'<p data-block-key="{block_id}h">{heading_text}</p>',
            "subheading_text": f'<p data-block-key="{block_id}sub">{subheading_text}</p>' if subheading_text else "",
        },
        "id": block_id,
    }


def _pricing_heading(heading_text, block_id, subheading_text=""):
    return {
        "type": "pricing_heading",
        "value": {
            "heading_text": f'<p data-block-key="{block_id}h">{heading_text}</p>',
            "subheading_text": f'<p data-block-key="{block_id}sub">{subheading_text}</p>' if subheading_text else "",
        },
        "id": block_id,
    }


def _icon_list(items, block_id):
    return {
        "type": "icon_list",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "icon": item["icon"],
                        "text": f'<p data-block-key="{block_id}i{index}">{item["text"]}</p>',
                    },
                    "id": f"{block_id}i{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _numbered_list(items, block_id):
    return {
        "type": "numbered_list",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "heading": f'<p data-block-key="{block_id}h{index}">{item["heading"]}</p>',
                        "text": f'<p data-block-key="{block_id}t{index}">{item["text"]}</p>',
                    },
                    "id": f"{block_id}n{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _timeline(items, block_id):
    return {
        "type": "timeline",
        "value": {
            "list_items": [
                {
                    "type": "item",
                    "value": {
                        "superheading_text": f'<p data-block-key="{block_id}s{index}">{item["superheading_text"]}</p>',
                        "heading_text": f'<p data-block-key="{block_id}h{index}">{item["heading_text"]}</p>',
                        "subheading_text": f'<p data-block-key="{block_id}sub{index}">{item["subheading_text"]}</p>',
                    },
                    "id": f"{block_id}ti{index}",
                }
                for index, item in enumerate(items)
            ],
        },
        "id": block_id,
    }


def _card(content_blocks, card_id, tag="", stick_image_to_right=False):
    return {
        "type": "card",
        "value": {
            "settings": {"stick_image_to_right": stick_image_to_right},
            "tag": tag,
            "content": content_blocks,
        },
        "id": card_id,
    }


def _two_column_cards(cards, block_id, anchor_id=""):
    return {
        "type": "two_column_cards",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": anchor_id,
            },
            "cards": cards,
        },
        "id": block_id,
    }


def get_two_column_cards_variants() -> list[dict]:
    get_placeholder_images()
    buttons = get_button_variants()
    return [
        _two_column_cards(
            anchor_id="plans",
            cards=[
                _card(
                    tag="Free",
                    content_blocks=[
                        _heading("Basic Plan", "tcc1-h1", subheading_text="Get started for free"),
                        _icon_list(
                            items=[
                                {"icon": "checkmark", "text": "Basic tracker blocking"},
                                {"icon": "bookmark", "text": "Sync bookmarks across devices"},
                                {"icon": "history", "text": "Access browsing history"},
                            ],
                            block_id="tcc1-il1",
                        ),
                        {
                            "type": "button",
                            "value": [buttons["primary"]],
                            "id": "tcc1-btn1",
                        },
                    ],
                    card_id="tcc1-card1",
                ),
                _card(
                    tag="Plus",
                    stick_image_to_right=True,
                    content_blocks=[
                        _heading("Premium Plan", "tcc1-h2", subheading_text="Everything in Free, plus more"),
                        _icon_list(
                            items=[
                                {"icon": "shield", "text": "Advanced tracker blocking"},
                                {"icon": "lock", "text": "VPN protection"},
                                {"icon": "heart", "text": "Priority customer support"},
                            ],
                            block_id="tcc1-il2",
                        ),
                        {
                            "type": "button",
                            "value": [buttons["primary"]],
                            "id": "tcc1-btn2",
                        },
                    ],
                    card_id="tcc1-card2",
                ),
            ],
            block_id="2026tcc1-0000-0000-0000-000000000001",
        ),
        _two_column_cards(
            cards=[
                _card(
                    content_blocks=[
                        _pricing_heading(
                            "$4.99/month",
                            "tcc2-ph1",
                            subheading_text="Billed monthly",
                        ),
                        _numbered_list(
                            items=[
                                {"heading": "Download Firefox", "text": "Get the browser that puts privacy first."},
                                {"heading": "Sign in", "text": "Create a free account to sync everywhere."},
                                {"heading": "Stay protected", "text": "Enhanced tracking protection enabled."},
                            ],
                            block_id="tcc2-nl1",
                        ),
                    ],
                    card_id="tcc2-card1",
                ),
                _card(
                    content_blocks=[
                        _pricing_heading(
                            "$9.99/month",
                            "tcc2-ph2",
                            subheading_text="Billed monthly",
                        ),
                        _timeline(
                            items=[
                                {
                                    "superheading_text": "Step 1",
                                    "heading_text": "Create your account",
                                    "subheading_text": "Sign up with your email address.",
                                },
                                {
                                    "superheading_text": "Step 2",
                                    "heading_text": "Choose a plan",
                                    "subheading_text": "Select the plan that fits your needs.",
                                },
                                {
                                    "superheading_text": "Step 3",
                                    "heading_text": "Start browsing",
                                    "subheading_text": "Enjoy private, secure browsing.",
                                },
                            ],
                            block_id="tcc2-tl1",
                        ),
                    ],
                    card_id="tcc2-card2",
                ),
            ],
            block_id="2026tcc1-0000-0000-0000-000000000002",
        ),
        _two_column_cards(
            cards=[
                _card(
                    tag="Free",
                    content_blocks=[
                        _heading("Free Plan", "tcc3-h1", subheading_text="Get started for free"),
                        _icon_list(
                            items=[
                                {"icon": "checkmark", "text": "Basic tracker blocking"},
                                {"icon": "bookmark", "text": "Sync bookmarks across devices"},
                            ],
                            block_id="tcc3-il1",
                        ),
                        {
                            "type": "button",
                            "value": [buttons["primary"]],
                            "id": "tcc3-btn1",
                        },
                        _media("tcc3-m1"),
                    ],
                    card_id="tcc3-card1",
                ),
                _card(
                    tag="Plus",
                    stick_image_to_right=True,
                    content_blocks=[
                        _heading("Premium Plan", "tcc3-h2", subheading_text="Everything in Free, plus more"),
                        _icon_list(
                            items=[
                                {"icon": "shield", "text": "Advanced tracker blocking"},
                                {"icon": "lock", "text": "VPN protection"},
                            ],
                            block_id="tcc3-il2",
                        ),
                        {
                            "type": "button",
                            "value": [buttons["primary"]],
                            "id": "tcc3-btn2",
                        },
                        _media("tcc3-m2"),
                    ],
                    card_id="tcc3-card2",
                ),
            ],
            block_id="2026tcc1-0000-0000-0000-000000000003",
        ),
    ]


def get_two_column_cards_test_page() -> FreeFormPage2026:
    index_page = get_2026_test_index_page()

    slug = "test-two-column-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Two Column Cards 2026")
        index_page.add_child(instance=page)

    variants = get_two_column_cards_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
