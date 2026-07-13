# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images, with_fresh_ids
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


def _cards_list(cards, settings=None, block_id=""):
    return {
        "type": "cards_list",
        "value": {
            "settings": settings or {"container_width": "", "cards_per_row": "", "two_wide_xs": False},
            "cards": cards,
        },
        "id": block_id,
    }


def _card(card_id, settings, content):
    return {
        "type": "card",
        "value": {
            "settings": settings,
            "content": content,
        },
        "id": card_id,
    }


def _settings(variant="", align="start", expand_link=False):
    return {"variant": variant, "align": align, "expand_link": expand_link, "show_to": _SHOW_TO_ALL}


# ---------------------------------------------------------------------------
# Sticker Cards 2026
# ---------------------------------------------------------------------------


def get_sticker_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        _card(
            "2026sc01-0000-0000-0000-000000000001",
            _settings(variant="filled", align="center"),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026sc1h">Sticker Card 2026</p>',
                        "subheading_text": "",
                    },
                    "id": "2026sc01-0001-0000-0000-000000000001",
                },
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026sc01-0001-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026sc1c">Without superheading, primary button.'
                    " Switch to Dark Mode to see the alternative image.</p>",
                    "id": "2026sc01-0001-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["primary"]], "help_text": ""},
                    "id": "2026sc01-0001-0000-0000-000000000004",
                },
            ],
        ),
        _card(
            "2026sc01-0000-0000-0000-000000000002",
            _settings(variant="filled", align="center"),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": '<p data-block-key="2026sc2s">Firefox 2026</p>',
                        "heading_text": '<p data-block-key="2026sc2h">Sticker Card with Superheading</p>',
                        "subheading_text": "",
                    },
                    "id": "2026sc01-0002-0000-0000-000000000001",
                },
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026sc01-0002-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026sc2c">With superheading and secondary button.</p>',
                    "id": "2026sc01-0002-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["secondary"]], "help_text": ""},
                    "id": "2026sc01-0002-0000-0000-000000000004",
                },
            ],
        ),
        _card(
            "2026sc01-0000-0000-0000-000000000003",
            _settings(variant="filled", align="center", expand_link=True),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026sc3h">Clickable Sticker Card</p>',
                        "subheading_text": "",
                    },
                    "id": "2026sc01-0003-0000-0000-000000000001",
                },
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026sc01-0003-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026sc3c">With expand link enabled - the entire card is clickable.</p>',
                    "id": "2026sc01-0003-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["ghost"]], "help_text": ""},
                    "id": "2026sc01-0003-0000-0000-000000000004",
                },
            ],
        ),
        _card(
            "2026sc01-0000-0000-0000-000000000004",
            _settings(variant="filled", align="center", expand_link=True),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": '<p data-block-key="2026sc4s">Privacy</p>',
                        "heading_text": '<p data-block-key="2026sc4h">All Sticker Card Fields</p>',
                        "subheading_text": "",
                    },
                    "id": "2026sc01-0004-0000-0000-000000000001",
                },
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026sc01-0004-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026sc4c">With all fields filled, expand link enabled, and link button.</p>',
                    "id": "2026sc01-0004-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026sc01-0004-0000-0000-000000000004",
                },
            ],
        ),
    ]


def get_sticker_cards_sections() -> list[dict]:
    cards = get_sticker_card_variants()
    return [
        _section(
            heading_text="Sticker Cards - Default",
            subheading_text="Default layout, auto column count based on number of cards.",
            content_blocks=[
                _cards_list(cards[:3], block_id="2026scs1-0000-0000-0000-000000000001"),
            ],
            section_id="2026ss01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Sticker Cards - 4 Cards",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                _cards_list(cards, block_id="2026scs1-0000-0000-0000-000000000002"),
            ],
            section_id="2026ss01-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Sticker Cards - Narrow container, 2 columns",
            subheading_text="Narrow container (725px) with 2 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:2],
                    settings={"container_width": "narrow", "cards_per_row": "2", "two_wide_xs": False},
                    block_id="2026scs1-0000-0000-0000-000000000003",
                ),
            ],
            section_id="2026ss01-0000-0000-0000-000000000003",
        ),
        _section(
            heading_text="Sticker Cards - Wide container, 3 columns",
            subheading_text="Wide container (1170px) with 3 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:3],
                    settings={"container_width": "wide", "cards_per_row": "3", "two_wide_xs": False},
                    block_id="2026scs1-0000-0000-0000-000000000004",
                ),
            ],
            section_id="2026ss01-0000-0000-0000-000000000004",
        ),
        _section(
            heading_text="Sticker Cards - Fill container, 2 wide on mobile",
            subheading_text="Fill container (no max-width) with 2-wide on mobile.",
            content_blocks=[
                _cards_list(
                    cards[:4],
                    settings={"container_width": "fill", "cards_per_row": "", "two_wide_xs": True},
                    block_id="2026scs1-0000-0000-0000-000000000005",
                ),
            ],
            section_id="2026ss01-0000-0000-0000-000000000005",
        ),
        _section(
            heading_text="Sticker Cards - Scroll",
            subheading_text="Horizontally scrollable card row.",
            content_blocks=[
                _cards_list(
                    cards * 2,
                    settings={"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
                    block_id="2026scs1-0000-0000-0000-000000000006",
                ),
            ],
            section_id="2026ss01-0000-0000-0000-000000000006",
        ),
    ]


def get_sticker_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-sticker-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Sticker Cards",
        },
    )

    sections = get_sticker_cards_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>Sticker Cards display a compact image (pictogram) with a short caption. They work well for thumbnail-style "
        "listings (e.g. quick links, theme galleries) where the image is the primary content.</p>"
        "<p>Keep captions short (a few words). The image should be the focal point &mdash; use bright, distinctive imagery rather "
        "than text-heavy graphics.</p>"
    )
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Illustration Cards 2026
# ---------------------------------------------------------------------------


def get_illustration_card_variants() -> list[dict]:
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        _card(
            "2026ic01-0000-0000-0000-000000000001",
            _settings(),
            [
                {
                    "type": "media",
                    "value": [{"type": "image", "value": _IMAGE_VARIANTS, "id": "2026ic01-0001-0000-0000-000000000001"}],
                    "id": "2026ic01-0001-0000-0000-000000000002",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026ic1h">Illustration Card 2026</p>',
                        "subheading_text": "",
                    },
                    "id": "2026ic01-0001-0000-0000-000000000003",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026ic1c">Without eyebrow, link button. Switch to Dark Mode to see the alternative image.</p>',
                    "id": "2026ic01-0001-0000-0000-000000000004",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026ic01-0001-0000-0000-000000000005",
                },
            ],
        ),
        _card(
            "2026ic01-0000-0000-0000-000000000002",
            _settings(),
            [
                {
                    "type": "media",
                    "value": [{"type": "image", "value": _IMAGE_VARIANTS, "id": "2026ic01-0002-0000-0000-000000000001"}],
                    "id": "2026ic01-0002-0000-0000-000000000002",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": '<p data-block-key="2026ic2e">Privacy</p>',
                        "heading_text": '<p data-block-key="2026ic2h">Illustration Card with Eyebrow</p>',
                        "subheading_text": "",
                    },
                    "id": "2026ic01-0002-0000-0000-000000000003",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026ic2c">With eyebrow and link button.</p>',
                    "id": "2026ic01-0002-0000-0000-000000000004",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026ic01-0002-0000-0000-000000000005",
                },
            ],
        ),
        _card(
            "2026ic01-0000-0000-0000-000000000003",
            _settings(),
            [
                {
                    "type": "media",
                    "value": [videos["youtube"]],
                    "id": "2026ic01-0003-0000-0000-000000000001",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": '<p data-block-key="2026ic3e">Video</p>',
                        "heading_text": '<p data-block-key="2026ic3h">Illustration Card with Video</p>',
                        "subheading_text": "",
                    },
                    "id": "2026ic01-0003-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026ic3c">With a YouTube video instead of an image.</p>',
                    "id": "2026ic01-0003-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026ic01-0003-0000-0000-000000000004",
                },
            ],
        ),
        _card(
            "2026ic01-0000-0000-0000-000000000004",
            _settings(),
            [
                {
                    "type": "media",
                    "value": [videos["animation"]],
                    "id": "2026ic01-0004-0000-0000-000000000001",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": '<p data-block-key="2026ic4e">Animation</p>',
                        "heading_text": '<p data-block-key="2026ic4h">Illustration Card with Animation</p>',
                        "subheading_text": "",
                    },
                    "id": "2026ic01-0004-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026ic4c">With an autoplay looping animation.</p>',
                    "id": "2026ic01-0004-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026ic01-0004-0000-0000-000000000004",
                },
            ],
        ),
    ]


def get_illustration_cards_sections() -> list[dict]:
    cards = get_illustration_card_variants()
    return [
        _section(
            heading_text="Illustration Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                _cards_list(cards[:3], block_id="2026ics1-0000-0000-0000-000000000001"),
            ],
            section_id="2026is01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Illustration Cards - All Media Types",
            subheading_text="All illustration card variants including image, video, and animation.",
            content_blocks=[
                _cards_list(cards, block_id="2026ics1-0000-0000-0000-000000000002"),
            ],
            section_id="2026is01-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Illustration Cards - Narrow Container, 2 Columns",
            subheading_text="Narrow container (725px) with 2 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:2],
                    settings={"container_width": "narrow", "cards_per_row": "2", "two_wide_xs": False},
                    block_id="2026ics1-0000-0000-0000-000000000003",
                ),
            ],
            section_id="2026is01-0000-0000-0000-000000000003",
        ),
        _section(
            heading_text="Illustration Cards - Scroll",
            subheading_text="Horizontally scrollable card row.",
            content_blocks=[
                _cards_list(
                    cards * 2,
                    settings={"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
                    block_id="2026ics1-0000-0000-0000-000000000004",
                ),
            ],
            section_id="2026is01-0000-0000-0000-000000000004",
        ),
    ]


def get_illustration_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-illustration-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Illustration Cards",
        },
    )

    sections = get_illustration_cards_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>Illustration Cards combine a generous illustration with a headline, description, and one or more buttons. They&rsquo;re "
        "the workhorse card for product and feature roundups where each item needs equal visual prominence.</p>"
        "<p>Aim for illustrations with consistent styles and color treatment across a set.</p>"
    )
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Step Cards 2026
# ---------------------------------------------------------------------------


def get_step_card_variants() -> list[dict]:
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


def get_step_cards_sections() -> list[dict]:
    cards = get_step_card_variants()
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


def get_step_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-step-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Step Cards",
        },
    )

    sections = get_step_cards_sections()
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>Step Cards visualize a sequential process &mdash; a how-to, a setup walkthrough &mdash; by numbering each card and laying "
        "them out left-to-right.</p>"
        "<p>Limit the sequence to 3&ndash;4 steps so the flow stays scannable. Each step&rsquo;s content should be short and "
        "action-oriented (a verb in the headline, a single supporting sentence).</p>"
    )
    page.save_revision().publish()
    return page


# ---------------------------------------------------------------------------
# Outlined Cards 2026
# ---------------------------------------------------------------------------


def get_outlined_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        _card(
            "2026oc01-0000-0000-0000-000000000001",
            _settings(variant="outline"),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026oc1h">Outlined Card 2026</p>',
                        "subheading_text": "",
                    },
                    "id": "2026oc01-0001-0000-0000-000000000001",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026oc1c">Without sticker, primary button.</p>',
                    "id": "2026oc01-0001-0000-0000-000000000002",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["primary"]], "help_text": ""},
                    "id": "2026oc01-0001-0000-0000-000000000003",
                },
            ],
        ),
        _card(
            "2026oc01-0000-0000-0000-000000000002",
            _settings(variant="outline"),
            [
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026oc01-0002-0000-0000-000000000001",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026oc2h">Outlined Card with Sticker</p>',
                        "subheading_text": "",
                    },
                    "id": "2026oc01-0002-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026oc2c">With sticker and secondary button. Switch to Dark Mode to see the alternative image.</p>',
                    "id": "2026oc01-0002-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["secondary"]], "help_text": ""},
                    "id": "2026oc01-0002-0000-0000-000000000004",
                },
            ],
        ),
        _card(
            "2026oc01-0000-0000-0000-000000000003",
            _settings(variant="outline", expand_link=True),
            [
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026oc3h">Clickable Outlined Card</p>',
                        "subheading_text": "",
                    },
                    "id": "2026oc01-0003-0000-0000-000000000001",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026oc3c">With expand link enabled - the entire card is clickable.</p>',
                    "id": "2026oc01-0003-0000-0000-000000000002",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["ghost"]], "help_text": ""},
                    "id": "2026oc01-0003-0000-0000-000000000003",
                },
            ],
        ),
        _card(
            "2026oc01-0000-0000-0000-000000000004",
            _settings(variant="outline", expand_link=True),
            [
                {
                    "type": "pictogram",
                    "value": {"image": _IMAGE_VARIANTS},
                    "id": "2026oc01-0004-0000-0000-000000000001",
                },
                {
                    "type": "heading",
                    "value": {
                        "superheading_text": "",
                        "heading_text": '<p data-block-key="2026oc4h">All Outlined Card Fields</p>',
                        "subheading_text": "",
                    },
                    "id": "2026oc01-0004-0000-0000-000000000002",
                },
                {
                    "type": "content",
                    "value": '<p data-block-key="2026oc4c">With sticker, expand link enabled, and link button.</p>',
                    "id": "2026oc01-0004-0000-0000-000000000003",
                },
                {
                    "type": "buttons",
                    "value": {"spacing": "", "buttons": [buttons["link"]], "help_text": ""},
                    "id": "2026oc01-0004-0000-0000-000000000004",
                },
            ],
        ),
    ]


def get_outlined_cards_sections() -> list[dict]:
    cards = get_outlined_card_variants()
    return [
        _section(
            heading_text="Outlined Cards - 3 Columns",
            subheading_text="Default 3-column grid layout.",
            content_blocks=[
                _cards_list(cards[:3], block_id="2026ocs1-0000-0000-0000-000000000001"),
            ],
            section_id="2026os01-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Outlined Cards - 4 Columns",
            subheading_text="When 4 cards are present the grid switches to 4 columns.",
            content_blocks=[
                _cards_list(cards, block_id="2026ocs1-0000-0000-0000-000000000002"),
            ],
            section_id="2026os01-0000-0000-0000-000000000002",
        ),
        _section(
            heading_text="Outlined Cards - Wide Container, 3 Columns",
            subheading_text="Wide container (1170px) with 3 columns forced.",
            content_blocks=[
                _cards_list(
                    cards[:3],
                    settings={"container_width": "wide", "cards_per_row": "3", "two_wide_xs": False},
                    block_id="2026ocs1-0000-0000-0000-000000000003",
                ),
            ],
            section_id="2026os01-0000-0000-0000-000000000003",
        ),
        _section(
            heading_text="Outlined Cards - Scroll",
            subheading_text="Horizontally scrollable card row.",
            content_blocks=[
                _cards_list(
                    cards * 2,
                    settings={"container_width": "scroll", "cards_per_row": "", "two_wide_xs": False},
                    block_id="2026ocs1-0000-0000-0000-000000000004",
                ),
            ],
            section_id="2026os01-0000-0000-0000-000000000004",
        ),
    ]


def get_outlined_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-outlined-cards"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Outlined Cards",
        },
    )

    sections = get_outlined_cards_sections()
    page.upper_content = with_fresh_ids(sections)
    page.content = with_fresh_ids(sections)
    page.docs = (
        "<p>Outlined Cards present small content within a bordered container, usually pointing the user somewhere else to get more info. "
        "Always use more than one (ideally 3 or 4), since banners are more appropriate when you only have one thing to highlight.</p>"
    )
    page.save_revision().publish()
    return page
