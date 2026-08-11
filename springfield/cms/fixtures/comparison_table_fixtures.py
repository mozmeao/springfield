# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

# Firefox Enterprise support tier data (used by both variants)
HEADER_CELLS = ["", "PREMIUM", "STANDARD"]
CONTENT_ROWS = [
    ["Best for", "High-assurance operational support", "Direct support for managed Firefox"],
    ["Availability", "24 hrs/day, Mon–Fri", "09:00–17:00, Mon–Fri"],
    ["Response (business-halting)", "30 minutes", "2 hours"],
    ["Channels", "Email, portal, and live chat", "Email, web portal"],
    ["Named success contact", "Named Success Lead", "Shared POC"],
    ["Business reviews", "Quarterly", "—"],
]

# Optional cell content data: image headers and Yes/No/Limited results.
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


def row(cells, row_id=""):
    return {
        "type": "item",
        "value": {"cells": cells},
        "id": row_id,
    }


def make_header_row(prefix):
    return row(
        cells=[
            cell(HEADER_CELLS[0], cell_id=f"{prefix}-h0"),
            cell(HEADER_CELLS[1], cell_id=f"{prefix}-h1"),
            cell(HEADER_CELLS[2], cell_id=f"{prefix}-h2"),
        ],
        row_id=f"{prefix}-hr",
    )


def make_content_rows(prefix):
    return [
        row(
            cells=[cell(row_cells[j], cell_id=f"{prefix}-r{i}c{j}") for j in range(3)],
            row_id=f"{prefix}-r{i}",
        )
        for i, row_cells in enumerate(CONTENT_ROWS)
    ]


def make_optional_content_header_row(prefix):
    """Header row whose value columns are an image with a label underneath."""

    return row(
        cells=[
            cell(RESULT_HEADERS[0], cell_id=f"{prefix}-h0"),
            image_header_cell(RESULT_HEADERS[1], cell_id=f"{prefix}-h1", dark_mode_image=settings.PLACEHOLDER_DARK_IMAGE_ID),
            image_header_cell(RESULT_HEADERS[2], cell_id=f"{prefix}-h2"),
        ],
        row_id=f"{prefix}-hr",
    )


def make_optional_content_rows(prefix):
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
        # Optional cell content: image headers, Yes/No/Limited results
        {
            "type": "comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "stacked",
                "header_row": [make_optional_content_header_row("ctbl03")],
                "content_rows": make_optional_content_rows("ctbl03"),
            },
            "id": "ctbl0003-0000-0000-0000-000000000003",
        },
        # Image headers and Yes/No/Limited results with stacked mobile behavior
        {
            "type": "comparison_table",
            "value": {
                "highlighted_column": 2,
                "mobile_behavior": "stacked",
                "header_row": [make_optional_content_header_row("ctbl04")],
                "content_rows": make_optional_content_rows("ctbl04"),
            },
            "id": "ctbl0004-0000-0000-0000-000000000004",
        },
    ]
