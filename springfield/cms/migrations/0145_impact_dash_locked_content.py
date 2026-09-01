# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration renaming ImpactDashBlock's locked_summary to locked_content, so
# it pairs with locked_heading the way the rendered summary_heading/summary_content
# pair does. Without it the copy an editor already wrote would read as blank, as
# Wagtail falls back to the field default for a key the stored JSON does not have.

import json
from collections.abc import MutableSequence

from django.db import migrations

OLD_KEY = "locked_summary"
NEW_KEY = "locked_content"

# The only StreamFields an impact dashboard can reach: it lives in a tab, and tabs
# are only offered by the ShowcaseBlock(allow_tabs=True) entries on these two pages.
PAGE_FIELDS = [
    ("ReferralHubPage", ["upper_content", "extra_content"]),
    ("ReferralGetFirefoxPage", ["upper_content"]),
]


def rename_key(data, old_key, new_key):
    """Rewrite the key on every impact_dash block in a raw StreamField tree."""
    if isinstance(data, dict):
        if data.get("type") == "impact_dash" and isinstance(data.get("value"), dict):
            value = data["value"]
            if old_key in value:
                value[new_key] = value.pop(old_key)
        for key, child in data.items():
            if isinstance(child, (dict, list, MutableSequence)):
                data[key] = rename_key(child, old_key, new_key)
    elif isinstance(data, (list, MutableSequence)):
        for index, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[index] = rename_key(item, old_key, new_key)
    return data


def migrate_revisions(apps, model, field_names, old_key, new_key):
    """Rewrite drafts too, or the editor's next save would drop the copy again."""
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type = ContentType.objects.get_for_model(model)

    for revision in Revision.objects.filter(content_type=content_type).iterator():
        modified = False
        for field_name in field_names:
            raw = revision.content.get(field_name)
            if not raw:
                continue
            try:
                revision.content[field_name] = json.dumps(rename_key(json.loads(raw), old_key, new_key))
            except (json.JSONDecodeError, TypeError):
                continue
            modified = True
        if modified:
            revision.save(update_fields=["content"])


def rename_stored_key(apps, old_key, new_key):
    for model_name, field_names in PAGE_FIELDS:
        model = apps.get_model("cms", model_name)
        for page in model.objects.all().iterator():
            for field_name in field_names:
                stream = getattr(page, field_name, None)
                if stream is None:
                    continue
                stream.raw_data = rename_key(stream.raw_data, old_key, new_key)
            page.save(update_fields=field_names)
        migrate_revisions(apps, model, field_names, old_key, new_key)


def forwards(apps, schema_editor):
    rename_stored_key(apps, OLD_KEY, NEW_KEY)


def backwards(apps, schema_editor):
    rename_stored_key(apps, NEW_KEY, OLD_KEY)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0144_blogarticlepage_bottom_banner"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
