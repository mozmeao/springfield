# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def make_link(block_id, label, analytics_id, new_window=False):
    return {
        "type": "link",
        "value": {
            "settings": {"analytics_id": analytics_id},
            "label": label,
            "link": {
                "link_to": "custom_url",
                "page": None,
                "file": None,
                "custom_url": "https://mozilla.org",
                "anchor": "",
                "email": "",
                "phone": "",
                "new_window": new_window,
                "relative_url": "",
            },
        },
        "id": block_id,
    }


def make_subheading(block_id, text):
    return {
        "type": "subheading",
        "value": f'<p data-block-key="{block_id}">{text}</p>',
        "id": block_id,
    }


def get_resources_column_variants() -> list[dict]:
    return [
        {
            "type": "item",
            "value": {
                "headline": '<p data-block-key="2026rc1h">Links Only</p>',
                "list_items": [
                    make_link("2026rl01-0000-0000-0000-000000000001", "First link in the column", "6cbbc05e-d7ad-4929-befc-410e1e26e701"),
                    make_link("2026rl01-0000-0000-0000-000000000002", "Second link in the column", "6cbbc05e-d7ad-4929-befc-410e1e26e702"),
                    make_link(
                        "2026rl01-0000-0000-0000-000000000003",
                        "Third link, opens in a new window",
                        "6cbbc05e-d7ad-4929-befc-410e1e26e703",
                        new_window=True,
                    ),
                ],
            },
            "id": "2026rc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "headline": '<p data-block-key="2026rc2h">Subheading First</p>',
                "list_items": [
                    make_subheading("2026rs02-0000-0000-0000-000000000001", "A subheading before any link"),
                    make_link("2026rl02-0000-0000-0000-000000000001", "Link under the first subheading", "6cbbc05e-d7ad-4929-befc-410e1e26e711"),
                    make_link(
                        "2026rl02-0000-0000-0000-000000000002", "Second link under the same subheading", "6cbbc05e-d7ad-4929-befc-410e1e26e712"
                    ),
                ],
            },
            "id": "2026rc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "headline": '<p data-block-key="2026rc3h">Subheading Between Links</p>',
                "list_items": [
                    make_link("2026rl03-0000-0000-0000-000000000001", "Link before the subheading", "6cbbc05e-d7ad-4929-befc-410e1e26e721"),
                    make_subheading("2026rs03-0000-0000-0000-000000000001", "A subheading that starts a new list"),
                    make_link("2026rl03-0000-0000-0000-000000000002", "Link after the subheading", "6cbbc05e-d7ad-4929-befc-410e1e26e722"),
                    make_subheading("2026rs03-0000-0000-0000-000000000002", "A second subheading"),
                    make_link("2026rl03-0000-0000-0000-000000000003", "Link in the last list", "6cbbc05e-d7ad-4929-befc-410e1e26e723"),
                ],
            },
            "id": "2026rc01-0000-0000-0000-000000000003",
        },
    ]


def get_resources_variants() -> list[dict]:
    columns = get_resources_column_variants()
    return [
        {
            "type": "resources",
            "value": {"columns": columns},
            "id": "2026rb01-0000-0000-0000-000000000001",
        },
        {
            "type": "resources",
            "value": {"columns": columns[:2]},
            "id": "2026rb01-0000-0000-0000-000000000002",
        },
    ]


def make_section(heading_text, content_blocks, section_id):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="2026rs">{heading_text}</p>',
                "subheading_text": "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def get_resources_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-resources",
        parent=index_page,
        defaults={
            "title": "Resources",
        },
    )

    variants = get_resources_variants()
    page_content = [
        make_section(
            "Resources Inside a Section",
            [variants[1]],
            "2026rss1-0000-0000-0000-000000000001",
        ),
        variants[0],
    ]
    page.upper_content = page_content
    page.content = page_content
    page.docs = (
        "<p>Resources arranges columns of links under a headline &mdash; typically used for directories, "
        "footers of long pages, or any list of destinations that benefits from being grouped.</p>"
        "<p>Add a subheading to split a column into labelled groups. Each subheading closes the list of links "
        "above it and starts a new one, so the groups stay separate for screen readers as well as visually.</p>"
    )
    page.save_revision().publish()
    return page
