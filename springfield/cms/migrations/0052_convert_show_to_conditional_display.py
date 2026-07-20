# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to convert show_to from a flat ChoiceBlock string to the new
# ConditionalDisplayBlock format (dict with platforms, firefox, auth_state keys).

import json
from collections.abc import MutableSequence

from django.db import migrations

# Maps old flat show_to string values to the new ConditionalDisplayBlock dict format.
SHOW_TO_CONVERSION = {
    "all": {"platforms": [], "firefox": "", "auth_state": ""},
    "is-firefox": {"platforms": [], "firefox": "is-firefox", "auth_state": ""},
    "not-firefox": {"platforms": [], "firefox": "not-firefox", "auth_state": ""},
    "state-fxa-supported-signed-in": {
        "platforms": [],
        "firefox": "",
        "auth_state": "state-fxa-supported-signed-in",
    },
    "state-fxa-supported-signed-out": {
        "platforms": [],
        "firefox": "",
        "auth_state": "state-fxa-supported-signed-out",
    },
    "osx": {"platforms": ["osx"], "firefox": "", "auth_state": ""},
    "linux": {"platforms": ["linux"], "firefox": "", "auth_state": ""},
    "windows": {"platforms": ["windows"], "firefox": "", "auth_state": ""},
    "windows-10-plus": {
        "platforms": ["windows-10-plus"],
        "firefox": "",
        "auth_state": "",
    },
    "windows-10-plus-signed-in": {
        "platforms": ["windows-10-plus"],
        "firefox": "",
        "auth_state": "state-fxa-supported-signed-in",
    },
    "windows-10-plus-signed-out": {
        "platforms": ["windows-10-plus"],
        "firefox": "",
        "auth_state": "state-fxa-supported-signed-out",
    },
    "unsupported": {"platforms": ["unsupported"], "firefox": "", "auth_state": ""},
    # Preserve legacy "other-os" bucket semantics: Android + iOS + other.
    "other-os": {
        "platforms": ["android", "ios", "other-os"],
        "firefox": "",
        "auth_state": "",
    },
}


def convert_show_to(data):
    """Recursively convert show_to string values in-place. Returns True if any change was made."""
    changed = False
    if isinstance(data, dict):
        if "show_to" in data and isinstance(data["show_to"], str):
            data["show_to"] = SHOW_TO_CONVERSION.get(
                data["show_to"],
                {"platforms": [], "firefox": "", "auth_state": ""},
            )
            changed = True
        for value in list(data.values()):
            if convert_show_to(value):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_show_to(item):
                changed = True
    return changed


def convert_pages(apps, schema_editor):
    models_and_fields = [
        ("HomePage", ["upper_content", "lower_content"]),
        ("DownloadPage", ["content"]),
        ("ThanksPage", ["content"]),
        ("ArticleThemePage", ["upper_content", "content"]),
        ("FreeFormPage", ["content"]),
        ("WhatsNewPage", ["content"]),
    ]

    for model_name, field_names in models_and_fields:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            changed_fields = []
            for field_name in field_names:
                stream_value = getattr(page, field_name)
                if stream_value and convert_show_to(stream_value.raw_data):
                    changed_fields.append(field_name)
            if changed_fields:
                page.save(update_fields=changed_fields)


def convert_revisions(apps, schema_editor):
    """Update Wagtail page revisions to use the new show_to format."""
    try:
        Revision = apps.get_model("wagtailcore", "Revision")
    except LookupError:
        return

    # All StreamField names that may contain show_to across all affected page types
    field_names = ["content", "upper_content", "lower_content"]

    for revision in Revision.objects.iterator():
        modified = False
        for field_name in field_names:
            raw_json = revision.content.get(field_name)
            if not raw_json:
                continue
            try:
                field_data = json.loads(raw_json)
                if convert_show_to(field_data):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            except (json.JSONDecodeError, TypeError):
                pass
        if modified:
            revision.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0051_bannersnippet_expire_at_bannersnippet_expired_and_more"),
    ]

    operations = [
        migrations.RunPython(convert_pages, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(convert_revisions, reverse_code=migrations.RunPython.noop),
    ]
