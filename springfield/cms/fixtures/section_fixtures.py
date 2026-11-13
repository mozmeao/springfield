# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import (
    SHOW_TO_ALL,
    get_flare_blocks_docs_page,
    get_image_media,
    get_or_create_page,
    get_placeholder_images,
    with_fresh_ids,
)
from springfield.cms.fixtures.block_factories import button, cards_list, heading_value, icon_card, media_content, rich_text, show_to_value
from springfield.cms.models import FreeFormPage2026


def section_block(block_id, heading_text, subheading_text="", content=None, cta=None, anchor_id="", show_to=None, pictogram=None):
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": show_to or SHOW_TO_ALL, "anchor_id": anchor_id},
            "pictogram": pictogram,
            "heading": heading_value(block_id, heading_text, subheading_text=subheading_text),
            "content": content or [],
            "cta": cta or [],
        },
        "id": block_id,
    }


def get_section_variants() -> list[dict]:
    return [
        section_block(
            "2026se01-0000-0000-0000-000000000001",
            heading_text="Section: the basic page container",
            subheading_text="A Section wraps a heading and a stack of inner blocks. Most page content lives inside one.",
            content=[
                media_content(
                    "2026se01-0000-0000-0000-000000000010",
                    heading_text="Inner block: Media + Content",
                    subheading_text="",
                    body_blocks=[
                        rich_text(
                            "2026se01-0000-0000-0000-000000000011",
                            '<p data-block-key="2026se1c">Sections can hold Media + Content, Cards, Banners, tables and more. '
                            "Add blocks here the way you would anywhere else.</p>",
                        )
                    ],
                    media=get_image_media("2026se01-0000-0000-0000-000000000012"),
                )
            ],
            cta=[
                button(
                    "2026se01-0000-0000-0000-000000000013",
                    "Optional section CTA",
                    "f0000000-0000-0000-0000-000000000001",
                    url="https://www.mozilla.org/",
                )
            ],
        ),
        section_block(
            "2026se01-0000-0000-0000-000000000002",
            heading_text="Section with an anchor ID",
            subheading_text="Set an Anchor ID (here, 'features') so navigation and in-page links can jump straight to this section.",
            anchor_id="features",
            content=[
                cards_list(
                    "2026se01-0000-0000-0000-000000000020",
                    cards=[
                        icon_card("2026se01-0000-0000-0000-000000000021", "activity", "Anchor IDs make long pages navigable.", headline="Linkable"),
                        icon_card(
                            "2026se01-0000-0000-0000-000000000022", "android", "Keep IDs short, lowercase and unique per page.", headline="Tidy IDs"
                        ),
                    ],
                )
            ],
        ),
        section_block(
            "2026se01-0000-0000-0000-000000000003",
            heading_text="Section shown only to Windows visitors",
            subheading_text="The Show To setting hides a whole section unless the visitor matches. This one targets Windows.",
            show_to=show_to_value(platforms=["windows"]),
            content=[
                rich_text(
                    "2026se01-0000-0000-0000-000000000030",
                    '<p data-block-key="2026se3c">You are seeing this because your platform is Windows. On any other platform the '
                    "whole section is removed from the page, not just hidden.</p>",
                )
            ],
        ),
    ]


def get_section_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-section",
        parent=index_page,
        defaults={"title": "Section"},
    )

    page.content = with_fresh_ids(get_section_variants())
    page.docs = (
        "<p>The Section is the main structural block: a heading, an optional pictogram, a stack of inner content blocks, "
        "and an optional single call-to-action. Reach for it whenever a part of the page needs its own heading and grouping.</p>"
        "<p>Two settings do most of the work. <b>Anchor ID</b> makes the section a jump target for navigation and in-page links. "
        "<b>Show To</b> controls who sees it — by platform, Firefox status, default-browser state and more — removing the whole "
        "section for everyone else.</p>"
    )
    page.save_revision().publish()
    return page
