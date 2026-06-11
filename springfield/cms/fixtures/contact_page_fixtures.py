# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def get_form_field_variants() -> list[dict]:
    """Return form field block variants for testing.

    Returns:
        List of form field block data dictionaries covering all five field types.
    """
    return [
        {
            "type": "text_field",
            "value": {
                "settings": {"internal_identifier": "full_name"},
                "label": "Full Name",
                "required": True,
            },
            "id": "text-field-name",
        },
        {
            "type": "text_field",
            "value": {
                "settings": {"internal_identifier": "company"},
                "label": "Company",
                "required": False,
            },
            "id": "text-field-company",
        },
        {
            "type": "email_field",
            "value": {
                "settings": {"internal_identifier": "email"},
                "label": "Email Address",
                "required": True,
            },
            "id": "email-field",
        },
        {
            "type": "phone_field",
            "value": {
                "settings": {"internal_identifier": "phone"},
                "label": "Phone Number",
                "required": False,
            },
            "id": "phone-field",
        },
        {
            "type": "select_field",
            "value": {
                "settings": {"internal_identifier": "interest"},
                "label": "Area of Interest",
                "required": True,
                "options": [
                    {"value": "attribution", "label": "Attribution"},
                    {"value": "measurement", "label": "Measurement"},
                    {"value": "privacy", "label": "Privacy Solutions"},
                    {"value": "other", "label": "Other"},
                ],
            },
            "id": "select-field",
        },
        {
            "type": "checkbox_group_field",
            "value": {
                "settings": {"internal_identifier": "services"},
                "label": "Services",
                "options": [
                    {"value": "consulting", "label": "Consulting"},
                    {"value": "implementation", "label": "Implementation"},
                    {"value": "support", "label": "Support"},
                ],
            },
            "id": "checkbox-group-field",
        },
        {
            "type": "textarea_field",
            "value": {
                "settings": {"internal_identifier": "message"},
                "label": "Message",
                "required": False,
                "rows": 4,
            },
            "id": "textarea-field",
        },
    ]
