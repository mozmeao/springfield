# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page
from springfield.cms.models import ContactPage


def get_form_field_variants() -> list[dict]:
    """
    Returns a list of form field variants for the contact page. Reflects the fields used by the
    Enterprise contact form on the live site.
    """
    return [
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "first_name",
                "label": "First name",
                "required": True,
            },
            "id": "text-field-first-name",
        },
        {
            "type": "text_field",
            "value": {
                "internal_identifier": "last_name",
                "label": "Last name",
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
                "label": "Job title",
                "required": True,
            },
            "id": "text-field-job-title",
        },
        {
            "type": "email_field",
            "value": {
                "internal_identifier": "business_email",
                "label": "Business email",
                "required": True,
            },
            "id": "email-field",
        },
        {
            "type": "phone_field",
            "value": {
                "internal_identifier": "business_phone",
                "label": "Business phone",
                "required": False,
            },
            "id": "phone-field",
        },
        {
            "type": "country_select_field",
            "value": {
                "internal_identifier": "country",
                "label": "Country or region",
                "required": True,
            },
            "id": "country-select-field",
        },
        {
            "type": "select_field",
            "value": {
                "internal_identifier": "firefox_use_stage",
                "label": "Which best describes your organization's use of Firefox?",
                "required": True,
                "options": [
                    {"value": "currently_deploy", "label": "We currently deploy and manage Firefox"},
                    {"value": "piloting", "label": "We are piloting or evaluating Firefox"},
                    {"value": "planning", "label": "We are planning a Firefox deployment"},
                    {"value": "exploring", "label": "We are exploring whether Firefox is right for us"},
                ],
            },
            "id": "select-field-firefox-use-stage",
        },
        {
            "type": "select_field",
            "value": {
                "internal_identifier": "deployment_size",
                "label": "How many devices (endpoints) would your Firefox deployment cover?",
                "required": True,
                "options": [
                    {"value": "up_to_500", "label": "Up to 500"},
                    {"value": "501_2500", "label": "501-2,500"},
                    {"value": "2501_5000", "label": "2,501-5,000"},
                    {"value": "5001_10000", "label": "5,001-10,000"},
                    {"value": "10001_25000", "label": "10,001-25,000"},
                    {"value": "25001_50000", "label": "25,001-50,000"},
                    {"value": "50001_100000", "label": "50,001-100,000"},
                    {"value": "over_100000", "label": "More than 100,000"},
                    {"value": "not_sure", "label": "Not sure yet"},
                ],
            },
            "id": "select-field-deployment-size",
        },
        {
            "type": "checkbox_group_field",
            "value": {
                "internal_identifier": "support_needs",
                "label": "What can Firefox Professional Support help with?",
                "required": True,
                "options": [
                    {"value": "planning_evaluating", "label": '<p data-block-key="ctpsn1">Planning or evaluating a Firefox deployment</p>'},
                    {"value": "deployment_config", "label": '<p data-block-key="ctpsn2">Deployment, configuration, or browser management</p>'},
                    {
                        "value": "security_compliance",
                        "label": '<p data-block-key="ctpsn3">Security, compliance, or data-sovereignty requirements</p>',
                    },
                    {"value": "troubleshooting", "label": '<p data-block-key="ctpsn4">Troubleshooting or escalation of technical issues</p>'},
                    {"value": "migration", "label": '<p data-block-key="ctpsn5">Migration from another browser</p>'},
                    {"value": "plans_pricing", "label": '<p data-block-key="ctpsn6">Understanding support plans and pricing</p>'},
                ],
            },
            "id": "checkbox-group-field-support-needs",
        },
        {
            "type": "select_field",
            "value": {
                "internal_identifier": "timeline",
                "label": "When are you looking to put support in place?",
                "required": True,
                "options": [
                    {"value": "asap", "label": "As soon as possible"},
                    {"value": "1_3_months", "label": "Within 1-3 months"},
                    {"value": "3_6_months", "label": "Within 3-6 months"},
                    {"value": "6_plus_months", "label": "More than 6 months from now"},
                    {"value": "exploring", "label": "We are still exploring"},
                ],
            },
            "id": "select-field-timeline",
        },
        {
            "type": "textarea_field",
            "value": {
                "internal_identifier": "message",
                "label": "Anything else you'd like us to know?",
                "required": False,
                "rows": 4,
            },
            "id": "textarea-field",
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
                "default_value": "enterprise-default-lead-submission",
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
                    "heading_text": '<p data-block-key="ctph1">Talk to our team about a support plan</p>',
                    "subheading_text": (
                        '<p data-block-key="ctph2">Tell us about your organization and we\'ll help you '
                        "scope a Firefox Professional Support plan — dedicated, private support for "
                        "large-scale deployments, with defined escalation paths and closer access to "
                        "Mozilla's engineering and product teams.</p>"
                        '<p data-block-key="ctph3">Looking for help with Firefox itself? Visit '
                        '<a href="https://support.mozilla.org">Mozilla Support</a>.</p>'
                    ),
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
