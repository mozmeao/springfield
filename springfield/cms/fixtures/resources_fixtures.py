# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.block_factories import link_block, section, subheading_block
from springfield.cms.models import FreeFormPage2026


def get_resources_column_variants() -> list[dict]:
    return [
        {
            "type": "item",
            "value": {
                "headline": '<p data-block-key="2026rc1h">Links Only</p>',
                "list_items": [
                    link_block(
                        block_id="2026rl01-0000-0000-0000-000000000001",
                        label="First link in the column",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e701",
                        custom_url="https://mozilla.org",
                    ),
                    link_block(
                        block_id="2026rl01-0000-0000-0000-000000000002",
                        label="Second link in the column",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e702",
                        custom_url="https://mozilla.org",
                    ),
                    link_block(
                        block_id="2026rl01-0000-0000-0000-000000000003",
                        label="Third link, opens in a new window",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e703",
                        new_window=True,
                        custom_url="https://mozilla.org",
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
                    subheading_block(block_id="2026rs02-0000-0000-0000-000000000001", text="A subheading before any link"),
                    link_block(
                        block_id="2026rl02-0000-0000-0000-000000000001",
                        label="Link under the first subheading",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e711",
                        custom_url="https://mozilla.org",
                    ),
                    link_block(
                        block_id="2026rl02-0000-0000-0000-000000000002",
                        label="Second link under the same subheading",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e712",
                        custom_url="https://mozilla.org",
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
                    link_block(
                        block_id="2026rl03-0000-0000-0000-000000000001",
                        label="Link before the subheading",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e721",
                        custom_url="https://mozilla.org",
                    ),
                    subheading_block(block_id="2026rs03-0000-0000-0000-000000000001", text="A subheading that starts a new list"),
                    link_block(
                        block_id="2026rl03-0000-0000-0000-000000000002",
                        label="Link after the subheading",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e722",
                        custom_url="https://mozilla.org",
                    ),
                    subheading_block(block_id="2026rs03-0000-0000-0000-000000000002", text="A second subheading"),
                    link_block(
                        block_id="2026rl03-0000-0000-0000-000000000003",
                        label="Link in the last list",
                        analytics_id="6cbbc05e-d7ad-4929-befc-410e1e26e723",
                        custom_url="https://mozilla.org",
                    ),
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
        section(heading_text="Resources Inside a Section", content_blocks=[variants[1]], section_id="2026rss1-0000-0000-0000-000000000001"),
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
