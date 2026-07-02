# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page
from springfield.cms.fixtures.snippet_fixtures import get_floating_qr_code_snippet, get_qr_code_snippet
from springfield.cms.models import WhatsNewIndexPage, WhatsNewPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_whatsnew_index_page() -> WhatsNewIndexPage:
    index_page = get_flare_pages_docs_page()
    wnp_index = get_or_create_page(
        WhatsNewIndexPage,
        slug="test-whatsnew",
        parent=index_page,
        defaults={"title": "What's New Index Page"},
    )
    wnp_index.save_revision().publish()
    return wnp_index


def get_whats_new_page_with_qr_snippet() -> WhatsNewPage2026:
    get_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-qr"
    page = get_or_create_page(
        WhatsNewPage2026,
        slug=slug,
        parent=wnp_index,
        defaults={
            "title": "What's New — QR Snippet Test",
            "version": "131",
        },
    )

    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="wnp-h">What\'s new in Firefox</p>',
                    "subheading_text": "",
                },
                "content": [],
                "cta": [],
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
        },
    ]
    page.show_qr_code_snippet = True
    page.save_revision().publish()
    return page


def get_whats_new_page_with_floating_qr_snippet() -> WhatsNewPage2026:
    get_floating_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-floating-qr"
    page = get_or_create_page(
        WhatsNewPage2026,
        slug=slug,
        parent=wnp_index,
        defaults={
            "title": "What's New — Floating QR Snippet Test",
            "version": "131",
        },
    )

    page.content = [
        {
            "type": "section",
            "value": {
                "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="wnp-h">What\'s new in Firefox</p>',
                    "subheading_text": "",
                },
                "content": [],
                "cta": [],
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
        },
    ]
    page.show_floating_qr_code_snippet = True
    page.save_revision().publish()
    return page
