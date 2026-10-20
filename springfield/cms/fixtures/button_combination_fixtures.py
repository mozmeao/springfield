# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Two pages with the same rows of mixed buttons, one with the marketing opt-out
turned on, to check that every combination lays out the same way on both."""

from uuid import uuid4

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_image_variants, get_or_create_page, with_fresh_ids
from springfield.cms.fixtures.block_factories import (
    banner,
    button_row,
    buttons_block,
    card,
    card_content,
    card_settings,
    cards_list,
    heading_block,
    heading_value,
    intro,
    section,
)
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026


def with_fresh_analytics_ids(blocks):
    """Return a copy of fixture data with a new analytics ID on every button.

    Reusing one button variant many times on a page would otherwise repeat the
    element ids derived from it, like the opt-out checkbox's."""
    if isinstance(blocks, dict):
        return {key: (str(uuid4()) if key == "analytics_id" else with_fresh_analytics_ids(value)) for key, value in blocks.items()}
    if isinstance(blocks, list):
        return [with_fresh_analytics_ids(item) for item in blocks]
    return blocks


def kit_intro(block_id, heading_text, subheading_text, buttons):
    return {
        "type": "kit_intro",
        "value": {"heading": heading_value(block_id, heading_text, subheading_text=subheading_text), "buttons": buttons},
        "id": block_id,
    }


def intro_with_buttons(block_id, heading_text, subheading_text, buttons, layout="vertical", media=None):
    return intro(block_id, heading_text, subheading_text, [buttons_block(f"{block_id}-btns", buttons)], media or [], layout=layout)


def card_with_buttons(block_id, align, buttons):
    return card(
        block_id,
        card_settings(variant="outlined", align=align),
        content=[
            heading_block(f"{block_id}-heading", f"Card aligned {align}"),
            card_content(block_id, "The checkbox follows the card's alignment."),
            {"type": "buttons", "value": {"spacing": "", "buttons": buttons, "help_text": ""}, "id": f"{block_id}-btns"},
        ],
    )


def get_button_combination_upper_blocks() -> list[dict]:
    buttons = get_button_variants()
    download = buttons["download"]
    media = [{"type": "image", "value": get_image_variants(), "id": "btncombo-media"}]
    return [
        kit_intro("btncombo-kit-1", "Kit Intro: Download + Link", "A link-style button beside the download.", [download, buttons["link"]]),
        kit_intro("btncombo-kit-2", "Kit Intro: Download only", "A single download button.", [download]),
        intro_with_buttons("btncombo-intro-1", "Intro: Download only", "A single download button.", [download]),
        intro_with_buttons("btncombo-intro-2", "Intro: Download + Button", "A regular button beside the download.", [download, buttons["secondary"]]),
        intro_with_buttons("btncombo-intro-3", "Intro: Download + Link", "A link-style button beside the download.", [download, buttons["link"]]),
        intro_with_buttons(
            "btncombo-intro-4", "Intro: Download + QR Code Modal", "Opens a modal with a QR code.", [download, buttons["qr_code_modal"]]
        ),
        intro_with_buttons(
            "btncombo-intro-5", "Intro: Download + Firefox Account", "A Mozilla account button beside the download.", [download, buttons["fxa"]]
        ),
        intro_with_buttons(
            "btncombo-intro-6",
            "Intro: Two download buttons",
            "With the opt-out on, the row shows one checkbox and the default browser checkbox is dropped.",
            [download, buttons["download_default_browser"]],
        ),
        intro_with_buttons(
            "btncombo-intro-7",
            "Intro: No download button",
            "Without a download button the row never shows the opt-out.",
            [buttons["secondary"], buttons["link"]],
        ),
        intro_with_buttons(
            "btncombo-intro-8",
            "Intro with media right: Download + Link",
            "Buttons and checkbox align to the start.",
            [download, buttons["link"]],
            layout="right",
            media=media,
        ),
        intro_with_buttons(
            "btncombo-intro-9",
            "Intro with media left: Download + Link",
            "Buttons and checkbox align to the start.",
            [download, buttons["link"]],
            layout="left",
            media=media,
        ),
    ]


def get_button_combination_lower_blocks() -> list[dict]:
    buttons = get_button_variants()
    download = buttons["download"]
    pair = [download, buttons["secondary"]]
    return [
        section(
            "btncombo-section-1",
            "Button Rows: Download + Button",
            content_blocks=[
                button_row("btncombo-row-center", pair),
                button_row("btncombo-row-start", pair, alignment="start"),
                button_row("btncombo-row-end", pair, alignment="end"),
                button_row("btncombo-row-stacked", pair, orientation="stacked"),
            ],
            subheading_text="Center, start, end and stacked rows.",
        ),
        cards_list(
            "btncombo-cards-1",
            [
                card_with_buttons("btncombo-card-start", "start", [download, buttons["link"]]),
                card_with_buttons("btncombo-card-center", "center", [download, buttons["link"]]),
                card_with_buttons("btncombo-card-end", "end", [download, buttons["link"]]),
            ],
        ),
        banner(
            "btncombo-banner-1",
            theme="purple-radial-gradient",
            heading_text="Banner: Download + Button",
            subheading_text="A banner's buttons share a row too.",
            buttons=pair,
        ),
    ]


def get_button_combination_test_page(slug, title, enable_marketing_attribution) -> FreeFormPage2026:
    page = get_or_create_page(FreeFormPage2026, slug=slug, parent=get_flare_blocks_docs_page(), defaults={"title": title})
    page.enable_marketing_attribution = enable_marketing_attribution
    page.upper_content = with_fresh_ids(with_fresh_analytics_ids(get_button_combination_upper_blocks()))
    page.content = with_fresh_ids(with_fresh_analytics_ids(get_button_combination_lower_blocks()))
    page.docs = (
        "<p>Every row pairs buttons the way editors combine them. The same rows appear on "
        "<i>Button Combinations</i> and <i>Button Combinations with Marketing Opt-out</i>, so the two "
        "pages can be compared side by side. With the opt-out on, each row holding a download button "
        "shows one checkbox below the row, and the row's buttons stay side by side.</p>"
    )
    page.save_revision().publish()
    return page


def get_button_combination_test_pages() -> list[FreeFormPage2026]:
    return [
        get_button_combination_test_page("test-button-combinations", "Button Combinations", enable_marketing_attribution=False),
        get_button_combination_test_page(
            "test-button-combinations-opt-out",
            "Button Combinations with Marketing Opt-out",
            enable_marketing_attribution=True,
        ),
    ]
