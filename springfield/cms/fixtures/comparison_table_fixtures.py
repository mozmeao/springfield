# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.fixtures.block_factories import section, table_cell, table_row
from springfield.cms.models import FreeFormPage2026

# Firefox Enterprise support tier data
HEADER_CELLS = ["", "PREMIUM", "STANDARD"]
CONTENT_ROWS = [
    ["Best for", "High-assurance operational support", "Direct support for managed Firefox"],
    ["Availability", "24 hrs/day, Mon–Fri", "09:00–17:00, Mon–Fri"],
    ["Response (business-halting)", "30 minutes", "2 hours"],
    ["Channels", "Email, portal, and live chat", "Email, web portal"],
    ["Named success contact", "Named Success Lead", "Shared POC"],
    ["Business reviews", "Quarterly", "—"],
]


def make_header_row(prefix):
    return table_row(
        cells=[
            table_cell(content=HEADER_CELLS[0], cell_id=f"{prefix}-h0"),
            table_cell(content=HEADER_CELLS[1], cell_id=f"{prefix}-h1"),
            table_cell(content=HEADER_CELLS[2], cell_id=f"{prefix}-h2"),
        ],
        row_id=f"{prefix}-hr",
    )


def make_content_rows(prefix):
    return [
        table_row(
            cells=[
                table_cell(content=cell_content, cell_id=f"{prefix}-r{row_index}c{cell_index}") for cell_index, cell_content in enumerate(row_cells)
            ],
            row_id=f"{prefix}-r{row_index}",
        )
        for row_index, row_cells in enumerate(CONTENT_ROWS)
    ]


def get_comparison_table_variants() -> list[dict]:
    return [
        # Scroll mobile behavior with highlighted column 2
        {
            "type": "comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "scroll",
                "header_row": [make_header_row("ctbl01")],
                "content_rows": make_content_rows("ctbl01"),
            },
            "id": "ctbl0001-0000-0000-0000-000000000001",
        },
        # Stacked mobile behavior with highlighted column 2
        {
            "type": "comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "stacked",
                "header_row": [make_header_row("ctbl02")],
                "content_rows": make_content_rows("ctbl02"),
            },
            "id": "ctbl0002-0000-0000-0000-000000000002",
        },
        # With fine print below the table
        {
            "type": "comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "scroll",
                "header_row": [make_header_row("ctbl03")],
                "content_rows": make_content_rows("ctbl03"),
                "fine_print": '<p data-block-key="ctbl03fp">* Response times are estimates and may vary based on issue complexity.</p>',
            },
            "id": "ctbl0003-0000-0000-0000-000000000003",
        },
    ]


def get_comparison_table_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-comparison-table",
        parent=index_page,
        defaults={"title": "Comparison Table"},
    )

    variants = get_comparison_table_variants()
    sections = [
        section(heading_text="Scroll — highlighted column 2", content_blocks=[variants[0]], section_id="ctblsec01-0000-0000-0000-000000000001"),
        section(
            heading_text="Stacked — highlighted column 2 (disabled on mobile)",
            content_blocks=[variants[1]],
            section_id="ctblsec02-0000-0000-0000-000000000002",
        ),
        section(heading_text="With fine print", content_blocks=[variants[2]], section_id="ctblsec03-0000-0000-0000-000000000003"),
    ]
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>The Comparison Table block renders structured data in a scrollable or stackable table. "
        "Use <b>highlighted_column</b> (1&ndash;4) to visually emphasize a column with a background. "
        "Use <b>mobile_behavior</b> to choose between horizontal scroll (default) or stacked columns on small screens. "
        "The highlight is automatically disabled in stacked mode.</p>"
    )
    page.save_revision().publish()
    return page
