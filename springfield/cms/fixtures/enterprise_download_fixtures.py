# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.models import FreeFormPage2026

ENTERPRISE_DOWNLOAD_HEADING = '<p data-block-key="ed26h">Resources</p>'

RESOURCE_LINKS = [
    ("https://firefox-admin-docs.mozilla.org/", "Firefox Enterprise documentation"),
    ("https://github.com/mozilla/policy-templates/releases", "Policy templates"),
    ("https://support.mozilla.org/products/firefox-enterprise/whats-new-firefox-enterprise/", "Enterprise Release Notes"),
]


def get_enterprise_download_rich_text(uid_prefix: str) -> str:
    """Build the resources list, giving every link a uid built from ``uid_prefix``."""
    items = "".join(
        f'<li><a href="{href}" uid="{uid_prefix}-{index:012d}">{text}</a></li>' for index, (href, text) in enumerate(RESOURCE_LINKS, start=1)
    )
    return f"<ul>{items}</ul>"


ENTERPRISE_DOWNLOAD_RICH_TEXT = get_enterprise_download_rich_text("ed260000-0001-0001-0001")


def get_enterprise_download(
    block_id: str = "ed000001-0000-0000-0000-000000000001",
    center_content: bool = False,
    heading: str = ENTERPRISE_DOWNLOAD_HEADING,
    rich_text: str = ENTERPRISE_DOWNLOAD_RICH_TEXT,
) -> dict:
    return {
        "type": "enterprise_download",
        "value": {
            "center_content": center_content,
            "heading": heading,
            "rich_text": rich_text,
        },
        "id": block_id,
    }


def get_enterprise_download_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-enterprise-download-page",
        parent=index_page,
        defaults={
            "title": "Enterprise Download",
        },
    )

    page.upper_content = [get_enterprise_download(center_content=False)]
    page.content = [
        get_enterprise_download(
            block_id="ed000002-0000-0000-0000-000000000002",
            center_content=True,
            rich_text=get_enterprise_download_rich_text("ed260000-0002-0002-0002"),
        )
    ]
    page.save_revision().publish()
    return page
