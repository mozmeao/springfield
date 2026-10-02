# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import (
    browser_table_cell,
    browser_table_image_header_cell,
    browser_table_result_cell,
    section,
    table_row,
)
from springfield.cms.models import FreeFormPage2026

# Header cells are image headers; body cells are Yes/No/Limited results.
# The third column's results carry a label override to show that option.
RESULT_HEADERS = ["", "Firefox", "Other browsers"]
RESULT_ROWS = [
    ("Blocks trackers by default", ("yes", ""), ("no", "")),
    ("Works without an account", ("yes", ""), ("limited", "Some features")),
    ("Sells your browsing data", ("no", ""), ("limited", "Sometimes")),
]


def make_header_row(prefix):
    """Header row whose value columns are an image with a label underneath."""
    placeholder_images = get_placeholder_images()

    return table_row(
        cells=[
            browser_table_cell(content=RESULT_HEADERS[0], cell_id=f"{prefix}-h0"),
            browser_table_image_header_cell(
                label=RESULT_HEADERS[1],
                cell_id=f"{prefix}-h1",
                dark_mode_image_id=placeholder_images.dark_image.id,
                image_id=placeholder_images.image.id,
            ),
            browser_table_image_header_cell(label=RESULT_HEADERS[2], cell_id=f"{prefix}-h2", image_id=placeholder_images.image.id),
        ],
        row_id=f"{prefix}-hr",
    )


def make_content_rows(prefix):
    """Content rows whose value columns are Yes/No/Limited results."""

    return [
        table_row(
            cells=[
                browser_table_cell(content=label, cell_id=f"{prefix}-r{i}c0"),
                browser_table_result_cell(result=first[0], label=first[1], cell_id=f"{prefix}-r{i}c1"),
                browser_table_result_cell(result=second[0], label=second[1], cell_id=f"{prefix}-r{i}c2"),
            ],
            row_id=f"{prefix}-r{i}",
        )
        for i, (label, first, second) in enumerate(RESULT_ROWS)
    ]


def get_browser_comparison_table_variants() -> list[dict]:
    return [
        # Stacked mobile behavior with highlighted column 2
        {
            "type": "browser_comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "stacked",
                "header_row": [make_header_row("bctbl01")],
                "content_rows": make_content_rows("bctbl01"),
            },
            "id": "bctbl001-0000-0000-0000-000000000001",
        },
        # Scroll mobile behavior with highlighted column 3
        {
            "type": "browser_comparison_table",
            "value": {
                "highlighted_column": 3,
                "mobile_behavior": "scroll",
                "header_row": [make_header_row("bctbl02")],
                "content_rows": make_content_rows("bctbl02"),
            },
            "id": "bctbl002-0000-0000-0000-000000000002",
        },
        # With fine print below the table
        {
            "type": "browser_comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "stacked",
                "header_row": [make_header_row("bctbl03")],
                "content_rows": make_content_rows("bctbl03"),
                "fine_print": '<p data-block-key="bctbl03fp">* Comparison reflects default settings at the time of publication.</p>',
            },
            "id": "bctbl003-0000-0000-0000-000000000003",
        },
    ]


def get_browser_comparison_table_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()
    # The image header cells reference the placeholder images by ID.
    get_placeholder_images()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-browser-comparison-table",
        parent=index_page,
        defaults={"title": "Browser Comparison Table"},
    )

    variants = get_browser_comparison_table_variants()
    sections = [
        section(
            heading_text="Stacked — highlighted column 2 (disabled on mobile)",
            content_blocks=[variants[0]],
            section_id="bctblsec1-0000-0000-0000-000000000001",
        ),
        section(heading_text="Scroll — highlighted column 3", content_blocks=[variants[1]], section_id="bctblsec2-0000-0000-0000-000000000002"),
        section(heading_text="With fine print", content_blocks=[variants[2]], section_id="bctblsec3-0000-0000-0000-000000000003"),
    ]
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>The Browser Comparison Table block compares Firefox against other browsers. "
        "Its header row takes an <b>image header</b> per column &mdash; a browser logo above a label &mdash; and its "
        "body cells take a <b>comparison result</b> (Yes, No or Limited, rendered as an icon with its name underneath).</p>"
        "<p>Use <b>highlighted_column</b> (1&ndash;4) to emphasize the Firefox column: its logo is enlarged and lifted "
        "above the table, while its label stays lined up with the other columns' labels. "
        "Use <b>mobile_behavior</b> to choose between horizontal scroll (default) or stacked columns on small screens. "
        "The highlight is automatically disabled in stacked mode.</p>"
    )
    page.save_revision().publish()
    return page
