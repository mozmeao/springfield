# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_image_media, get_or_create_page, with_fresh_ids
from springfield.cms.fixtures.block_factories import media_content, section
from springfield.cms.models import FreeFormPage2026

SHARED_URL = "https://www.firefox.com/enterprise/"


def get_sharing_links_variants(content_area: int = 1) -> dict[str, dict]:
    """Return the block variants. ``content_area`` sets the analytics IDs, which also name each
    QR code dialog, so variants placed in two areas of one page need different values."""
    return {
        "full": {
            "type": "sharing_links",
            "id": "shrlnk01-0000-0000-0000-000000000001",
            "value": {
                "copy_label": "Copy link",
                "copy_success_label": "Link copied!",
                "url": SHARED_URL,
                "email_label": "Share by email",
                "email_subject": "Take a look at Firefox for Enterprise",
                "email_body": (
                    "The email button opens a draft in the visitor's mail app with this subject and body. "
                    "The shared URL is added to the end of the body."
                ),
                "qr_label": "Show QR code",
                "qr_heading": '<p data-block-key="shrlnk01">Scan to open on <b>your phone</b></p>',
                "qr_text": '<p data-block-key="shrlnk02">The QR code encodes the same URL the other buttons share.</p>',
                "analytics_id": f"shrlnk01-0000-0000-0000-00000000{content_area:02d}02",
            },
        },
        "required_only": {
            "type": "sharing_links",
            "id": "shrlnk02-0000-0000-0000-000000000001",
            "value": {
                "copy_label": "Copy this page's link",
                "copy_success_label": "Copied!",
                "url": SHARED_URL,
                "email_label": "Share by email",
                "email_subject": "",
                "email_body": "",
                "qr_label": "Show QR code",
                "qr_heading": "",
                "qr_text": "",
                "analytics_id": f"shrlnk02-0000-0000-0000-00000000{content_area:02d}02",
            },
        },
    }


def get_sharing_links_blocks(content_area: int = 1) -> list[dict]:
    variants = get_sharing_links_variants(content_area)
    return [
        section(
            heading_text="All Fields",
            subheading_text="Copy, email and QR code buttons, with an email subject and body and a QR code modal heading and text.",
            section_id="shrlnk01-0000-0000-0000-000000000000",
            content_blocks=[variants["full"]],
        ),
        media_content(
            block_id="shrlnk02-0000-0000-0000-000000000000",
            heading_text="Required Fields Only",
            subheading_text="A custom copy label and URL only: the email draft holds just the URL and the QR code modal shows just the code.",
            body_blocks=[variants["required_only"]],
            media=get_image_media("shrlnk02-0000-0000-0000-000000000003"),
        ),
    ]


def get_sharing_links_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-sharing-links",
        parent=index_page,
        defaults={
            "title": "Sharing Links",
        },
    )

    page.upper_content = with_fresh_ids(get_sharing_links_blocks(content_area=1))
    page.content = with_fresh_ids(get_sharing_links_blocks(content_area=2))
    page.docs = (
        "<p>The Sharing Links block is a row of three buttons for sharing one URL. "
        "<b>Copy link</b> copies the URL to the clipboard, the <b>email</b> button opens a draft "
        "with the optional subject and body followed by the URL, and the <b>QR code</b> button opens "
        "a modal with a QR code for the URL plus the optional heading and text.</p>"
    )
    page.save_revision().publish()
    return page
