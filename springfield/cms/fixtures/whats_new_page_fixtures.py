# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.fixtures.snippet_fixtures import get_floating_qr_code_snippet, get_qr_code_snippet
from springfield.cms.models import WhatsNewIndexPage, WhatsNewPage, WhatsNewPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def get_whatsnew_index_page() -> WhatsNewIndexPage:
    index_page = get_2026_test_index_page()
    wnp_index = WhatsNewIndexPage.objects.filter(slug="test-whatsnew").first()
    if not wnp_index:
        wnp_index = WhatsNewIndexPage(
            slug="test-whatsnew",
            title="Test What's New Index",
        )
        index_page.add_child(instance=wnp_index)
        wnp_index.save_revision().publish()
    return wnp_index


def get_whats_new_page_with_qr_snippet() -> WhatsNewPage:
    get_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-qr"
    page = WhatsNewPage.objects.filter(slug=slug).first()
    if not page:
        page = WhatsNewPage(
            slug=slug,
            title="What's New — QR Snippet Test",
            version="130",
        )
        wnp_index.add_child(instance=page)

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


def get_whats_new_page_2026_with_qr_snippet() -> WhatsNewPage2026:
    get_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-2026-qr"
    page = WhatsNewPage2026.objects.filter(slug=slug).first()
    if not page:
        page = WhatsNewPage2026(
            slug=slug,
            title="What's New 2026 — QR Snippet Test",
            version="131",
        )
        wnp_index.add_child(instance=page)

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


def get_whats_new_page_2026_with_floating_qr_snippet() -> WhatsNewPage2026:
    get_floating_qr_code_snippet()
    wnp_index = get_whatsnew_index_page()

    slug = "test-wnp-2026-floating-qr"
    page = WhatsNewPage2026.objects.filter(slug=slug).first()
    if not page:
        page = WhatsNewPage2026(
            slug=slug,
            title="What's New 2026 — Floating QR Snippet Test",
            version="131",
        )
        wnp_index.add_child(instance=page)

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
