# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}


def get_line_card_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "item",
            "value": {
                "superheading": "",
                "headline": '<p data-block-key="2026lc1h">Line Card Without Superheading</p>',
                "content": '<p data-block-key="2026lc1c">Content without superheading or buttons. '
                "This card demonstrates the minimal layout with just a headline and body text.</p>",
                "buttons": [],
            },
            "id": "2026lc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "superheading": '<p data-block-key="2026lc2s">Privacy</p>',
                "headline": '<p data-block-key="2026lc2h">Line Card with Superheading</p>',
                "content": '<p data-block-key="2026lc2c">Content with a superheading label above the headline and a link button below. '
                "Use this variant to categorize or tag the card topic.</p>",
                "buttons": [buttons["link"]],
            },
            "id": "2026lc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "superheading": "",
                "headline": '<p data-block-key="2026lc3h">Line Card with Two Buttons</p>',
                "content": '<p data-block-key="2026lc3c">Content without superheading and two action buttons. '
                "This variant is suited for presenting a primary action alongside a secondary option.</p>",
                "buttons": [buttons["primary"], buttons["ghost"]],
            },
            "id": "2026lc01-0000-0000-0000-000000000003",
        },
        {
            "type": "item",
            "value": {
                "superheading": '<p data-block-key="2026lc4s">Security</p>',
                "headline": '<p data-block-key="2026lc4h">Line Card — All Fields</p>',
                "content": '<p data-block-key="2026lc4c">Content with all fields populated: a superheading label, a headline, descriptive body text, '
                "and two action buttons for primary and secondary calls to action.</p>",
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": "2026lc01-0000-0000-0000-000000000004",
        },
    ]


def get_line_cards_variants() -> list[dict]:
    cards = get_line_card_variants()
    return [
        {
            "type": "line_cards",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="2026lcbh1">Line Cards with Heading</p>',
                    "subheading_text": '<p data-block-key="2026lcbs1">Optional subheading for the block.</p>',
                },
                "cards": cards,
            },
            "id": "2026lcb1-0000-0000-0000-000000000001",
        },
        {
            "type": "line_cards",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": "",
                    "subheading_text": "",
                },
                "cards": cards[:2],
            },
            "id": "2026lcb1-0000-0000-0000-000000000002",
        },
    ]


def _section(heading_text, content_blocks, section_id):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="2026lcs">{heading_text}</p>',
                "subheading_text": "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def get_line_cards_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-line-cards-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Line Cards 2026")
        index_page.add_child(instance=page)

    variants = get_line_cards_variants()
    page_content = [
        _section(
            "Line Cards Inside a Section",
            [variants[1]],
            "2026lcs1-0000-0000-0000-000000000001",
        ),
        variants[0],
    ]
    page.upper_content = page_content
    page.content = page_content
    page.save_revision().publish()
    return page
