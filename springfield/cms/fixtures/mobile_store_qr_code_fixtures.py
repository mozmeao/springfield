# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
from springfield.cms.models import FreeFormPage2026


def get_mobile_store_qr_code_variants():
    """Get various mobile store QR code block configurations."""
    return {
        "with_heading": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="1khhq">Get Firefox on Mobile</p>',
                    "heading_text": '<p data-block-key="yy3vb">Download Firefox for iOS and Android</p>',
                    "subheading_text": '<p data-block-key="m6fp1">Scan the QR code or tap a button to download Firefox on your mobile device.</p>',
                },
                "qr_code_data": "https://www.mozilla.org/firefox/mobile/",
            },
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        },
        "without_heading": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": "",
                    "subheading_text": "",
                },
                "qr_code_data": "https://www.mozilla.org/firefox/mobile/",
            },
            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        },
        "with_superheading_only": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="1khhq">Mobile Apps</p>',
                    "heading_text": '<p data-block-key="yy3vb">Take Firefox with you</p>',
                    "subheading_text": "",
                },
                "qr_code_data": "https://www.mozilla.org/firefox/browsers/mobile/",
            },
            "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        },
        "with_all_fields": {
            "type": "mobile_store_qr_code",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="1khhq"><i>NEW</i> Firefox Mobile</p>',
                    "heading_text": '<p data-block-key="yy3vb">Your browser, wherever you go</p>',
                    "subheading_text": '<p data-block-key="m6fp1">Get the same privacy-first browsing experience on your phone or tablet. Fast, secure, and independent.</p>',
                },
                "qr_code_data": "https://mzl.la/firefox-mobile",
            },
            "id": "d4e5f6a7-b8c9-0123-def1-234567890123",
        },
    }


def get_mobile_store_qr_code_test_page():
    """Create a test page for the Mobile Store QR Code block."""
    index_page = get_2026_test_index_page()
    variants = get_mobile_store_qr_code_variants()

    page = FreeFormPage2026.objects.filter(slug="mobile-store-qr-code").first()
    if not page:
        page = FreeFormPage2026(
            slug="mobile-store-qr-code",
            title="Mobile Store QR Code Test",
        )
        index_page.add_child(instance=page)

    # Test the block in both upper_content and content areas
    page.upper_content = [variants["with_heading"]]
    page.content = [
        variants["without_heading"],
        variants["with_superheading_only"],
        variants["with_all_fields"],
    ]

    page.save_revision().publish()
    return page
