# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.fixtures.block_factories import certification_item, section
from springfield.cms.models import FreeFormPage2026


def get_certification_list_variants() -> list[dict]:
    return [
        {
            "type": "certification_list",
            "value": {
                "list_items": [
                    certification_item(text="DORA", item_id="2026cl01a", url="https://mozilla.org/dora/"),
                    certification_item(text="GDPR", item_id="2026cl01b", url="https://mozilla.org/gdpr/"),
                    certification_item(text="NIS2", item_id="2026cl01c", url="https://mozilla.org/nis2/"),
                    certification_item(text="ISO27001", item_id="2026cl01d", url="https://mozilla.org/iso27001/"),
                    certification_item(text="SEC2", item_id="2026cl01e", url="https://mozilla.org/sec2/"),
                ],
            },
            "id": "2026cli1-0000-0000-0000-000000000001",
        },
        {
            "type": "certification_list",
            "value": {
                "list_items": [
                    certification_item(text="DORA", item_id="2026cl02a"),
                    certification_item(text="GDPR", item_id="2026cl02b"),
                    certification_item(text="NIS2", item_id="2026cl02c"),
                ],
            },
            "id": "2026cli1-0000-0000-0000-000000000002",
        },
    ]


def get_certification_list_sections() -> list[dict]:
    variants = get_certification_list_variants()
    return [
        section(
            heading_text="Certification List - Linked",
            subheading_text="Each pill links out to more detail and underlines on hover.",
            content_blocks=[variants[0]],
            section_id="2026cls1-0000-0000-0000-000000000001",
        ),
        section(
            heading_text="Certification List - Text Only",
            subheading_text="Items without a link render as plain, non-interactive pills.",
            content_blocks=[variants[1]],
            section_id="2026cls1-0000-0000-0000-000000000002",
        ),
    ]


def get_certification_list_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-certification-list",
        parent=index_page,
        defaults={
            "title": "Certification List",
        },
    )

    sections = get_certification_list_sections()
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>The Certification List block renders a row of pill tags, each with plain text or an optional link. "
        "It&rsquo;s a child of the Section block, with no settings or theme options.</p>"
        "<p>Keep item labels short, like a certification or standard acronym. Add a link only when there&rsquo;s "
        "somewhere useful to send visitors &mdash; linked pills underline on hover.</p>"
    )
    page.save_revision().publish()
    return page
