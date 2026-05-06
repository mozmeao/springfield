# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}

_EMPTY_IMAGE_VARIANTS = {
    "image": None,
    "settings": {
        "dark_mode_image": None,
        "mobile_image": None,
        "dark_mode_mobile_image": None,
    },
}


def _section(heading_text, content_blocks, section_id, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="sc2026h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="sc2026s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


# ---------------------------------------------------------------------------
# Sticker Cards 2026
# ---------------------------------------------------------------------------


def get_sticker_card_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "image": _IMAGE_VARIANTS,
                "superheading": "",
                "headline": '<p data-block-key="2026sc1h">Sticker Card 2026</p>',
                "content": '<p data-block-key="2026sc1c">Without superheading, primary button. Switch to Dark Mode to see the alternative image.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "2026sc01-0000-0000-0000-000000000001",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "image": _IMAGE_VARIANTS,
                "superheading": '<p data-block-key="2026sc2s">Firefox 2026</p>',
                "headline": '<p data-block-key="2026sc2h">Sticker Card with Superheading</p>',
                "content": '<p data-block-key="2026sc2c">With superheading and secondary button.</p>',
                "buttons": [buttons["secondary"]],
            },
            "id": "2026sc01-0000-0000-0000-000000000002",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "image": _IMAGE_VARIANTS,
                "superheading": "",
                "headline": '<p data-block-key="2026sc3h">Clickable Sticker Card</p>',
                "content": '<p data-block-key="2026sc3c">With expand link enabled - the entire card is clickable.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "2026sc01-0000-0000-0000-000000000003",
        },
        {
            "type": "sticker_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "image": _IMAGE_VARIANTS,
                "superheading": '<p data-block-key="2026sc4s">Privacy</p>',
                "headline": '<p data-block-key="2026sc4h">All Sticker Card Fields</p>',
                "content": '<p data-block-key="2026sc4c">With all fields filled, expand link enabled, and link button.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026sc01-0000-0000-0000-000000000004",
        },
    ]


def get_sticker_cards_2026_sections() -> list[dict]:
    cards = get_sticker_card_2026_variants()
    return [
        _section(
            heading_text="Sticker Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards[:3]},
                    "id": "2026scs1-0000-0000-0000-000000000001",
                }
            ],
            section_id="2026ss01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Sticker Cards - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards},
                    "id": "2026scs1-0000-0000-0000-000000000002",
                }
            ],
            section_id="2026ss01-0000-0000-0000-000000000002",
        ),
    ]


def get_sticker_cards_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-sticker-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Sticker Cards 2026")
        index_page.add_child(instance=page)

    sections = get_sticker_cards_2026_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Illustration Cards 2026
# ---------------------------------------------------------------------------


def get_illustration_card_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [{"type": "image", "value": _IMAGE_VARIANTS, "id": "2026ic01-0000-0000-0000-000000000011"}],
                "eyebrow": "",
                "headline": '<p data-block-key="2026ic1h">Illustration Card 2026</p>',
                "content": '<p data-block-key="2026ic1c">Without eyebrow, link button. Switch to Dark Mode to see the alternative image.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026ic01-0000-0000-0000-000000000001",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [{"type": "image", "value": _IMAGE_VARIANTS, "id": "2026ic01-0000-0000-0000-000000000021"}],
                "eyebrow": '<p data-block-key="2026ic2e">Privacy</p>',
                "headline": '<p data-block-key="2026ic2h">Illustration Card with Eyebrow</p>',
                "content": '<p data-block-key="2026ic2c">With eyebrow and link button.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026ic01-0000-0000-0000-000000000002",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [videos["youtube"]],
                "eyebrow": '<p data-block-key="2026ic3e">Video</p>',
                "headline": '<p data-block-key="2026ic3h">Illustration Card with Video</p>',
                "content": '<p data-block-key="2026ic3c">With a YouTube video instead of an image.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026ic01-0000-0000-0000-000000000003",
        },
        {
            "type": "illustration_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "media": [videos["animation"]],
                "eyebrow": '<p data-block-key="2026ic4e">Animation</p>',
                "headline": '<p data-block-key="2026ic4h">Illustration Card with Animation</p>',
                "content": '<p data-block-key="2026ic4c">With an autoplay looping animation.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026ic01-0000-0000-0000-000000000004",
        },
    ]


def get_illustration_cards_2026_sections() -> list[dict]:
    cards = get_illustration_card_2026_variants()
    return [
        _section(
            heading_text="Illustration Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards[:3]},
                    "id": "2026ics1-0000-0000-0000-000000000001",
                }
            ],
            section_id="2026is01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Illustration Cards - All Media Types",
            subheading_text="All illustration card variants including image, video, and animation.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards},
                    "id": "2026ics1-0000-0000-0000-000000000002",
                }
            ],
            section_id="2026is01-0000-0000-0000-000000000002",
        ),
    ]


def get_illustration_cards_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-illustration-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Illustration Cards 2026")
        index_page.add_child(instance=page)

    sections = get_illustration_cards_2026_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Step Cards 2026
# ---------------------------------------------------------------------------


def get_step_card_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": _IMAGE_VARIANTS,
                "eyebrow": "",
                "headline": '<p data-block-key="2026st1h">Step Card 2026</p>',
                "content": '<p data-block-key="2026st1c">Without eyebrow, primary button. Switch to Dark Mode to see the alternative image.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026st01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": False},
                "image": _IMAGE_VARIANTS,
                "eyebrow": '<p data-block-key="2026st2e">Download</p>',
                "headline": '<p data-block-key="2026st2h">Step Card with Eyebrow</p>',
                "content": '<p data-block-key="2026st2c">With eyebrow and secondary button.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026st01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": True},
                "image": _IMAGE_VARIANTS,
                "eyebrow": "",
                "headline": '<p data-block-key="2026st3h">Clickable Step Card</p>',
                "content": "",
                "buttons": [buttons["link"]],
            },
            "id": "2026st01-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "settings": {"expand_link": True},
                "image": _IMAGE_VARIANTS,
                "eyebrow": '<p data-block-key="2026st4e">Import</p>',
                "headline": '<p data-block-key="2026st4h">All Step Card Fields</p>',
                "content": '<p data-block-key="2026st4c">With all fields filled, expand link enabled, and link button.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026st01-0000-0000-0000-000000000004",
        },
    ]


def get_step_cards_2026_sections() -> list[dict]:
    cards = get_step_card_2026_variants()
    return [
        _section(
            heading_text="Step Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                {
                    "type": "step_cards",
                    "value": {"cards": cards[:3]},
                    "id": "2026stcs-0000-0000-0000-000000000001",
                }
            ],
            section_id="2026sts1-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Step Cards - 4 Columns",
            subheading_text="When 4 step cards are present the grid switches to 4 columns.",
            content_blocks=[
                {
                    "type": "step_cards",
                    "value": {"cards": cards},
                    "id": "2026stcs-0000-0000-0000-000000000002",
                }
            ],
            section_id="2026sts1-0000-0000-0000-000000000002",
        ),
    ]


def get_step_cards_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-step-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Step Cards 2026")
        index_page.add_child(instance=page)

    sections = get_step_cards_2026_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Outlined Cards 2026
# ---------------------------------------------------------------------------


def get_outlined_card_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "outlined_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "sticker": _EMPTY_IMAGE_VARIANTS,
                "headline": '<p data-block-key="2026oc1h">Outlined Card 2026</p>',
                "content": '<p data-block-key="2026oc1c">Without sticker, primary button.</p>',
                "buttons": [buttons["primary"]],
            },
            "id": "2026oc01-0000-0000-0000-000000000001",
        },
        {
            "type": "outlined_card",
            "value": {
                "settings": {"expand_link": False, "show_to": _SHOW_TO_ALL},
                "sticker": _IMAGE_VARIANTS,
                "headline": '<p data-block-key="2026oc2h">Outlined Card with Sticker</p>',
                "content": '<p data-block-key="2026oc2c">With sticker and secondary button. Switch to Dark Mode to see the alternative image.</p>',
                "buttons": [buttons["secondary"]],
            },
            "id": "2026oc01-0000-0000-0000-000000000002",
        },
        {
            "type": "outlined_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "sticker": _EMPTY_IMAGE_VARIANTS,
                "headline": '<p data-block-key="2026oc3h">Clickable Outlined Card</p>',
                "content": '<p data-block-key="2026oc3c">With expand link enabled - the entire card is clickable.</p>',
                "buttons": [buttons["ghost"]],
            },
            "id": "2026oc01-0000-0000-0000-000000000003",
        },
        {
            "type": "outlined_card",
            "value": {
                "settings": {"expand_link": True, "show_to": _SHOW_TO_ALL},
                "sticker": _IMAGE_VARIANTS,
                "headline": '<p data-block-key="2026oc4h">All Outlined Card Fields</p>',
                "content": '<p data-block-key="2026oc4c">With sticker, expand link enabled, and link button.</p>',
                "buttons": [buttons["link"]],
            },
            "id": "2026oc01-0000-0000-0000-000000000004",
        },
    ]


def get_outlined_cards_2026_sections() -> list[dict]:
    cards = get_outlined_card_2026_variants()
    return [
        _section(
            heading_text="Outlined Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards[:3]},
                    "id": "2026ocs1-0000-0000-0000-000000000001",
                }
            ],
            section_id="2026os01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Outlined Cards - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                {
                    "type": "cards_list",
                    "value": {"cards": cards},
                    "id": "2026ocs1-0000-0000-0000-000000000002",
                }
            ],
            section_id="2026os01-0000-0000-0000-000000000002",
        ),
    ]


def get_outlined_cards_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-outlined-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Outlined Cards 2026")
        index_page.add_child(instance=page)

    sections = get_outlined_cards_2026_sections()
    page.upper_content = sections
    page.content = sections
    page.save_revision().publish()
    return page
