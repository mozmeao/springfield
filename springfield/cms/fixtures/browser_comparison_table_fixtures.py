# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.comparison_table_fixtures import row, section
from springfield.cms.models import FreeFormPage2026

# Header cells are image headers; body cells are Yes/No/Limited results.
# The third column's results carry a label override to show that option.
RESULT_HEADERS = ["", "Firefox", "Other browsers"]
RESULT_ROWS = [
    ("Blocks trackers by default", ("yes", ""), ("no", "")),
    ("Works without an account", ("yes", ""), ("limited", "Some features")),
    ("Sells your browsing data", ("no", ""), ("limited", "Sometimes")),
]


def cell(content, column_span=1, cell_id="", optional_content=None):
    return {
        "type": "item",
        "value": {
            "content": content,
            "optional_content": optional_content or [],
            "column_span": column_span,
        },
        "id": cell_id,
    }


def result_cell(result, label="", cell_id=""):
    return cell(
        "",
        cell_id=cell_id,
        optional_content=[
            {
                "type": "comparison_result",
                "value": {"result": result, "label": label},
                "id": f"{cell_id}-oc",
            }
        ],
    )


def image_header_cell(label, cell_id="", dark_mode_image=None):
    return cell(
        "",
        cell_id=cell_id,
        optional_content=[
            {
                "type": "image_header",
                "value": {
                    "image": settings.PLACEHOLDER_IMAGE_ID,
                    "dark_mode_image": dark_mode_image,
                    "alt": "",
                    "label": label,
                },
                "id": f"{cell_id}-oc",
            }
        ],
    )


def make_header_row(prefix):
    """Header row whose value columns are an image with a label underneath."""

    return row(
        cells=[
            cell(RESULT_HEADERS[0], cell_id=f"{prefix}-h0"),
            image_header_cell(RESULT_HEADERS[1], cell_id=f"{prefix}-h1", dark_mode_image=settings.PLACEHOLDER_DARK_IMAGE_ID),
            image_header_cell(RESULT_HEADERS[2], cell_id=f"{prefix}-h2"),
        ],
        row_id=f"{prefix}-hr",
    )


def make_content_rows(prefix):
    """Content rows whose value columns are Yes/No/Limited results."""

    return [
        row(
            cells=[
                cell(label, cell_id=f"{prefix}-r{i}c0"),
                result_cell(first[0], first[1], cell_id=f"{prefix}-r{i}c1"),
                result_cell(second[0], second[1], cell_id=f"{prefix}-r{i}c2"),
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
        section("Stacked — highlighted column 2 (disabled on mobile)", variants[0], "bctblsec1-0000-0000-0000-000000000001"),
        section("Scroll — highlighted column 3", variants[1], "bctblsec2-0000-0000-0000-000000000002"),
        section("With fine print", variants[2], "bctblsec3-0000-0000-0000-000000000003"),
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
