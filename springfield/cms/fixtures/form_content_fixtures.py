# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_blocks_docs_page, get_or_create_page, with_fresh_ids
from springfield.cms.fixtures.block_factories import heading_value, section, show_to_value
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.contact_page_fixtures import get_contact_test_page
from springfield.cms.fixtures.sharing_links_fixtures import get_sharing_links_variants
from springfield.cms.fixtures.tag_fixtures import get_tag_variants
from springfield.cms.models import FreeFormPage2026


def get_form_content_variants(content_area: int = 1) -> list[dict]:
    """Form + Content blocks covering both form positions and every content item.

    ``content_area`` sets the sharing links' analytics IDs, which must differ between the page's two content areas.
    """
    contact_page = get_contact_test_page()
    buttons = get_button_variants()
    tags = get_tag_variants()
    sharing_links = get_sharing_links_variants(content_area)
    return [
        {
            "type": "form_content",
            "value": {
                "form_before": True,
                "show_to": SHOW_TO_ALL,
                "form": {
                    "contact_page": contact_page.pk,
                    "two_column": False,
                    "query_params": [{"key": "ls", "value": "form-content-block"}],
                },
                "heading": heading_value(
                    "fc01",
                    "Form before the content",
                    subheading_text="Form Before puts the form on the left on desktop. On mobile it always comes after the content.",
                    superheading_text="Form + Content",
                ),
                "content": [
                    {"type": "tags", "value": [tags["purple"], tags["green"]], "id": "fc000001-0000-0000-0000-000000000002"},
                    {
                        "type": "rich_text",
                        "value": (
                            '<p data-block-key="fc01c">The form is loaded from the chosen Contact Page, which also handles '
                            "its submissions. A query param set on the block feeds the Contact Page's hidden fields.</p>"
                        ),
                        "id": "fc000001-0000-0000-0000-000000000003",
                    },
                    {"type": "buttons", "value": [buttons["primary"], buttons["secondary"]], "id": "fc000001-0000-0000-0000-000000000004"},
                ],
            },
            "id": "fc000001-0000-0000-0000-000000000001",
        },
        {
            "type": "form_content",
            "value": {
                "form_before": False,
                "show_to": SHOW_TO_ALL,
                "form": {"contact_page": contact_page.pk, "two_column": True, "query_params": []},
                "heading": heading_value("fc02", "Form after the content, in two columns"),
                "content": [
                    {
                        "type": "rich_text",
                        "value": '<p data-block-key="fc02c">By default the form comes after the content on every screen size.</p>'
                        '<p data-block-key="xc32s">The "Two Column" setting splits the form in two columns on desktop.</p>',
                        "id": "fc000002-0000-0000-0000-000000000002",
                    },
                    sharing_links["required_only"],
                ],
            },
            "id": "fc000002-0000-0000-0000-000000000001",
        },
    ]


def get_form_content_conditional_variant() -> dict:
    """A top-level Form + Content block shown only to Firefox users."""
    contact_page = get_contact_test_page()
    return {
        "type": "form_content",
        "value": {
            "form_before": False,
            "show_to": show_to_value(firefox="is-firefox"),
            "form": {"contact_page": contact_page.pk, "two_column": False, "query_params": []},
            "heading": heading_value(
                "fc03", "Shown to Firefox users only", subheading_text="Placed at the top level of the page (outside a section)."
            ),
            "content": [],
        },
        "id": "fc000003-0000-0000-0000-000000000001",
    }


def get_form_content_blocks(content_area: int = 1) -> list[dict]:
    return with_fresh_ids(
        [
            section(
                section_id="fcs00001-0000-0000-0000-000000000001",
                heading_text="Form + Content",
                subheading_text="A Contact Page's form on one side, a heading and content on the other.",
                content_blocks=get_form_content_variants(content_area),
            ),
            get_form_content_conditional_variant(),
        ]
    )


def get_form_content_test_page() -> FreeFormPage2026:
    index_page = get_flare_blocks_docs_page()

    page = get_or_create_page(
        FreeFormPage2026,
        slug="test-form-content",
        parent=index_page,
        defaults={
            "title": "Form + Content",
        },
    )

    page.upper_content = get_form_content_blocks(content_area=1)
    page.content = get_form_content_blocks(content_area=2)
    page.docs = (
        "<p>The Form + Content block places a Contact Page&rsquo;s form alongside a content column (heading, tags, body, "
        'buttons, sharing links). The form follows the content by default. The "Form Before" setting moves it to the left on desktop.</p>'
    )
    page.save_revision().publish()
    return page
