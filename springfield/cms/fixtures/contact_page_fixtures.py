# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page
from springfield.cms.models import ContactPage


def get_form_field_variants() -> list[dict]:
    """Return all form fields from the production contact page, plus textarea and checkbox_group."""
    return [
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "first_name",
                "label": "First Name",
                "required": True,
            },
            "id": "text-field-first-name",
        },
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "last_name",
                "label": "Last Name",
                "required": True,
            },
            "id": "text-field-last-name",
        },
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "company",
                "label": "Company",
                "required": True,
            },
            "id": "text-field-company",
        },
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "job_title",
                "label": "Job Title",
                "required": True,
            },
            "id": "text-field-job-title",
        },
        {
            "type": "email_field",
            "value": {
                "internal_identifier": "business_email",
                "label": "Business Email",
                "required": True,
            },
            "id": "email-field",
        },
        {
            "type": "phone_field",
            "value": {
                "internal_identifier": "business_phone",
                "label": "Business Phone",
                "required": True,
            },
            "id": "phone-field",
        },
        {
            "type": "select_field",
            "value": {
                "internal_identifier": "company_size",
                "label": "Company Size",
                "required": True,
                "options": [
                    {"value": "1 - 10", "label": "1 - 10"},
                    {"value": "11 - 20", "label": "11 - 20"},
                    {"value": "21 - 100", "label": "21 - 100"},
                    {"value": "101+", "label": "101+"},
                ],
            },
            "id": "select-field",
        },
        {
            "type": "country_select_field",
            "value": {
                "internal_identifier": "country",
                "label": "Country",
                "required": True,
            },
            "id": "country-select-field",
        },
        {
            "type": "textarea_field",
            "value": {
                "internal_identifier": "message",
                "label": "Message",
                "required": False,
                "rows": 4,
            },
            "id": "textarea-field",
        },
        {
            "type": "checkbox_group_field",
            "value": {
                "internal_identifier": "services",
                "label": "Services",
                "options": [
                    {"value": "consulting", "label": '<p data-block-key="ctpoptin1">Consulting</p>'},
                    {"value": "implementation", "label": '<p data-block-key="ctpoptin2">Implementation</p>'},
                    {"value": "support", "label": '<p data-block-key="ctpoptin3">Support</p>'},
                ],
            },
            "id": "checkbox-group-field",
        },
        {
            "type": "checkbox_field",
            "value": {
                "internal_identifier": "opt_in",
                "label": '<p data-block-key="ctpoptin1">By checking this box, you agree to the '
                '<a href="/terms-and-conditions/">terms and conditions</a>.</p>',
                "required": True,
            },
            "id": "checkbox-field",
        },
        {
            "type": "hidden_field",
            "value": {
                "internal_identifier": "lead_source",
                "label": "Lead Source",
                "required": False,
                "default_value": "techrider.de",
                "query_param_override": "ls",
            },
            "id": "hidden-field-lead-source",
        },
        {
            "type": "hidden_field",
            "value": {
                "internal_identifier": "cta",
                "label": "CTA",
                "required": False,
                "default_value": "Request Private Briefing",
            },
            "id": "hidden-field-cta",
        },
    ]


def get_contact_test_page() -> ContactPage:
    index_page = get_flare_pages_docs_page()

    slug = "test-contact-page"
    page = get_or_create_page(
        ContactPage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Test Contact Page",
            "basket_api_path": "/api/v1/contact/enterprise/",
            "thank_you_message": '<p data-block-key="ctpty1">Thanks for reaching out!</p>',
        },
    )

    page.intro = [
        {
            "type": "intro",
            "value": {
                "settings": {
                    "layout": "vertical",
                    "full_width": False,
                    "slim": False,
                    "anchor_id": "",
                    "remove_border_radius": False,
                },
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="ctph1">Get in touch</p>',
                    "subheading_text": '<p data-block-key="ctph2">Fill out the form below and we\'ll get back to you.</p>',
                },
                "content": [],
            },
            "id": "ctp00001-0000-0000-0000-000000000001",
        }
    ]
    page.form_fields = get_form_field_variants()
    page.basket_api_path = "/api/v1/contact/enterprise/"
    page.thank_you_message = '<p data-block-key="ctpty1">Thanks for reaching out!</p>'
    page.save_revision().publish()
    return page
