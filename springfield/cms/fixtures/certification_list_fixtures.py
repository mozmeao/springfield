# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

_EMPTY_LINK = {
    "link_to": "",
    "page": None,
    "file": None,
    "custom_url": "",
    "anchor": "",
    "email": "",
    "phone": "",
    "new_window": False,
    "relative_url": "",
}


def _link(url):
    return {
        "link_to": "custom_url",
        "page": None,
        "file": None,
        "custom_url": url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": False,
        "relative_url": "",
    }


def _section(heading_text, content_blocks, section_id, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="cl2026h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="cl2026s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def _certification(text, item_id, url=""):
    return {
        "type": "item",
        "value": {
            "text": text,
            "link": _link(url) if url else _EMPTY_LINK,
        },
        "id": item_id,
    }


def get_certification_list_variants() -> list[dict]:
    return [
        {
            "type": "certification_list",
            "value": {
                "list_items": [
                    _certification("DORA", "2026cl01a", "https://mozilla.org/dora/"),
                    _certification("GDPR", "2026cl01b", "https://mozilla.org/gdpr/"),
                    _certification("NIS2", "2026cl01c", "https://mozilla.org/nis2/"),
                    _certification("ISO27001", "2026cl01d", "https://mozilla.org/iso27001/"),
                    _certification("SEC2", "2026cl01e", "https://mozilla.org/sec2/"),
                ],
            },
            "id": "2026cli1-0000-0000-0000-000000000001",
        },
        {
            "type": "certification_list",
            "value": {
                "list_items": [
                    _certification("DORA", "2026cl02a"),
                    _certification("GDPR", "2026cl02b"),
                    _certification("NIS2", "2026cl02c"),
                ],
            },
            "id": "2026cli1-0000-0000-0000-000000000002",
        },
    ]


def get_certification_list_sections() -> list[dict]:
    variants = get_certification_list_variants()
    return [
        _section(
            heading_text="Certification List - Linked",
            subheading_text="Each pill links out to more detail and underlines on hover.",
            content_blocks=[variants[0]],
            section_id="2026cls1-0000-0000-0000-000000000001",
        ),
        _section(
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
