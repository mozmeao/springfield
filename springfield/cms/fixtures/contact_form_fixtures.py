# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images, with_fresh_ids
from springfield.cms.fixtures.contact_page_fixtures import get_contact_test_page
from springfield.cms.models import FreeFormPage2026


def get_contact_form_variants() -> list[dict]:
    """An intro, then the block on its own and nested in a media + content block, its two placements."""
    placeholder_images = get_placeholder_images()
    contact_page = get_contact_test_page()
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
        {
            "type": "contact_form",
            "value": {
                "contact_page": contact_page.pk,
                "two_column": False,
                "query_params": [{"key": "ls", "value": "contact-form-block-lead-submission"}],
            },
            "id": "cf000001-0000-0000-0000-000000000001",
        },
        {
            "type": "media_content",
            "value": {
                "media": [
                    {
                        "type": "image",
                        "value": {
                            "image": placeholder_images.image.id,
                            "settings": {
                                "dark_mode_image": placeholder_images.dark_image.id,
                                "mobile_image": placeholder_images.mobile_image.id,
                                "dark_mode_mobile_image": placeholder_images.dark_mobile_image.id,
                            },
                        },
                        "id": "cf000002-0000-0000-0000-000000000002",
                    }
                ],
                "heading": {
                    "heading_text": '<p data-block-key="cfmc01">A contact form beside an image</p>',
                    "subheading_text": (
                        '<p data-block-key="cfmc02">Nested in a Media + Content block. The two-column layout option helps '
                        "organize the form fields side by side on larger screens.</p>"
                    ),
                },
                "content": [
                    {
                        "type": "contact_form",
                        "value": {"contact_page": contact_page.pk, "two_column": True},
                        "id": "cf000001-0000-0000-0000-000000000002",
                    }
                ],
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
