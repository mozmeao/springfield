# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to convert IllustrationCard2026Block.image (ImageVariantsBlock)
# to IllustrationCard2026Block.media (MediaBlock StreamBlock list).

import json
from collections.abc import MutableSequence
from uuid import uuid4

from django.db import migrations


def migrate_illustration_card_block(block_data):
    """Convert illustration_card block's image field to media StreamBlock."""
    if block_data.get("type") != "illustration_card":
        return block_data

    value = {**block_data.get("value", {})}
    image = value.get("image")

    if image is not None and "media" not in value:
        value["media"] = [
            {
                "type": "image",
                "value": image,
                "id": str(uuid4()),
            }
        ]
        del value["image"]
        block_data["value"] = value

    return block_data


def walk_and_transform(data):
    """Recursively walk through the block tree and migrate illustration_card blocks."""
    if isinstance(data, dict):
        if data.get("type") == "illustration_card":
            data = migrate_illustration_card_block(data)
        else:
            for key, value in data.items():
                if isinstance(value, (dict, list, MutableSequence)):
                    data[key] = walk_and_transform(value)

    elif isinstance(data, (list, MutableSequence)):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[i] = walk_and_transform(item)

    return data


def migrate_stream_field(page, field_name):
    """Migrate a single StreamField on a page instance."""
    field = getattr(page, field_name, None)
    if field is None:
        return False
    field.raw_data = walk_and_transform(field.raw_data)
    return True


def migrate_revision(revision, field_names):
    """Migrate named StreamFields within a revision's content dict."""
    modified = False
    for field_name in field_names:
        if field_name in revision.content:
            try:
                content = json.loads(revision.content[field_name])
                revision.content[field_name] = json.dumps(walk_and_transform(content))
                modified = True
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
    return modified


def update_pages(apps, schema_editor):
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    page_configs = [
        ("HomePage", ["upper_content"]),
        ("FreeFormPage2026", ["upper_content", "content"]),
        ("WhatsNewPage2026", ["upper_content", "content"]),
        ("SmartWindowPage", ["content"]),
        ("SmartWindowExplainerPage", ["upper_content", "content"]),
    ]

    for model_name, field_names in page_configs:
        PageModel = apps.get_model("cms", model_name)
        ct = ContentType.objects.get_for_model(PageModel)

        print(f"Migrating {model_name} revisions...")
        for revision in Revision.objects.filter(content_type=ct).iterator():
            if migrate_revision(revision, field_names):
                revision.save(update_fields=["content"])

        print(f"Migrating current {model_name} data...")
        for page in PageModel.objects.all():
            update_fields = []
            for field_name in field_names:
                if migrate_stream_field(page, field_name):
                    update_fields.append(field_name)
            if update_fields:
                page.save(update_fields=update_fields)

    print("Migration complete!")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0066_smartwindowpage_animation_and_more"),
    ]

    operations = [
        migrations.RunPython(update_pages, migrations.RunPython.noop),
    ]
