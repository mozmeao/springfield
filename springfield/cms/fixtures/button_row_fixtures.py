# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, with_fresh_ids
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _section(heading_text, subheading_text, section_id, button_row):
    return {
        "type": "section",
        "id": section_id,
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="{section_id}h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="{section_id}s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": [button_row],
            "cta": [],
        },
    }


def get_button_row_blocks() -> list[dict]:
    buttons = get_button_variants()
    return [
        _section(
            heading_text="Single Button (center, no spacing)",
            subheading_text="Default settings: one button, centered, no top spacing.",
            section_id="btnrow01-0000-0000-0000-000000000000",
            button_row={
                "type": "button_row",
                "id": "btnrow01-0000-0000-0000-000000000001",
                "value": {
                    "spacing": "",
                    "alignment": "",
                    "buttons": [dict(buttons["primary"], id="btnrow01-0000-0000-0000-000000000002")],
                    "help_text": "",
                },
            },
        ),
        _section(
            heading_text="Two Buttons (start alignment, small spacing)",
            subheading_text="Two buttons aligned to the start of the row with small top spacing.",
            section_id="btnrow02-0000-0000-0000-000000000000",
            button_row={
                "type": "button_row",
                "id": "btnrow02-0000-0000-0000-000000000001",
                "value": {
                    "spacing": "small",
                    "alignment": "start",
                    "buttons": [
                        dict(buttons["primary"], id="btnrow02-0000-0000-0000-000000000002"),
                        dict(buttons["secondary"], id="btnrow02-0000-0000-0000-000000000003"),
                    ],
                    "help_text": "",
                },
            },
        ),
        _section(
            heading_text="Three Buttons (end alignment, large spacing)",
            subheading_text="Maximum of three buttons, right-aligned with large top spacing.",
            section_id="btnrow03-0000-0000-0000-000000000000",
            button_row={
                "type": "button_row",
                "id": "btnrow03-0000-0000-0000-000000000001",
                "value": {
                    "spacing": "large",
                    "alignment": "end",
                    "buttons": [
                        dict(buttons["primary"], id="btnrow03-0000-0000-0000-000000000002"),
                        dict(buttons["secondary"], id="btnrow03-0000-0000-0000-000000000003"),
                        dict(buttons["link"], id="btnrow03-0000-0000-0000-000000000004"),
                    ],
                    "help_text": "",
                },
            },
        ),
        _section(
            heading_text="With Help Text",
            subheading_text="The optional help text field renders a note below the buttons.",
            section_id="btnrow04-0000-0000-0000-000000000000",
            button_row={
                "type": "button_row",
                "id": "btnrow04-0000-0000-0000-000000000001",
                "value": {
                    "spacing": "small",
                    "alignment": "",
                    "buttons": [dict(buttons["primary"], id="btnrow04-0000-0000-0000-000000000002")],
                    "help_text": '<p data-block-key="btnrow04">Optional help text can appear below the buttons.</p>',
                },
            },
        ),
    ]


def get_button_row_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    slug = "test-button-row"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Button Row",
        },
    )

    blocks = get_button_row_blocks()
    page.upper_content = with_fresh_ids(blocks)
    page.content = with_fresh_ids(blocks)
    page.docs = (
        "<p>The Button Row block groups 1–3 buttons in a horizontal row. "
        "Use <b>spacing</b> to add vertical margin above the row (small or large). "
        "Use <b>alignment</b> to left-align (start), right-align (end), or center (default) the buttons. "
        "An optional <b>help text</b> field renders as a short note below the buttons.</p>"
    )
    page.save_revision().publish()
    return page
