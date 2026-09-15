# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, with_fresh_ids
from springfield.cms.fixtures.contact_page_fixtures import get_contact_test_page
from springfield.cms.models import FreeFormPage2026


def get_contact_form_variants() -> list[dict]:
    """An intro, then the block on its own and nested in a media + content block, its two placements."""
    contact_page = get_contact_test_page()
    contact_form = {
        "type": "contact_form",
        "value": {"contact_page": contact_page.pk},
        "id": "cf000001-0000-0000-0000-000000000001",
    }
    return [
        {
            "type": "intro",
            "value": {
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="cfin01">Contact Form</p>',
                    "heading_text": '<p data-block-key="cfin02">Embed a contact page\'s form anywhere</p>',
                    "subheading_text": (
                        '<p data-block-key="cfin03">The block renders the form belonging to the contact page it points at, '
                        "and submissions post back to that page. Below it appears on its own and nested in a media + "
                        "content block.</p>"
                    ),
                },
                "content": [],
            },
            "id": "cf000003-0000-0000-0000-000000000001",
        },
        contact_form,
        {
            "type": "media_content",
            "value": {
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": settings.PLACEHOLDER_IMAGE_ID,
                            "settings": {
                                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                                "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                                "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
                            },
                        },
                        "id": "cf000002-0000-0000-0000-000000000002",
                    }
                ],
                "heading": {
                    "heading_text": '<p data-block-key="cfmc01">A contact form beside an image</p>',
                    "subheading_text": (
                        '<p data-block-key="cfmc02">Nested in a media + content block, the form drops its own '
                        "section wrapper and takes the layout of whatever holds it.</p>"
                    ),
                },
                "content": [contact_form],
            },
            "id": "cf000002-0000-0000-0000-000000000001",
        },
    ]


def get_contact_form_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-contact-form-page",
        parent=index_page,
        defaults={
            "title": "Contact Form",
        },
    )

    variants = get_contact_form_variants()
    page.upper_content = with_fresh_ids(variants)
    page.content = with_fresh_ids(variants)
    page.save_revision().publish()
    return page
