# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Migration to migrate ShowcaseBlock from image field to media field

import json
import uuid
from collections.abc import MutableSequence

from django.db import migrations


def migrate_showcase_block(block_data):
    """Migrate ShowcaseBlock from image field to media StreamBlock field."""
    if block_data.get("type") != "showcase":
        return block_data

    value = {**block_data.get("value", {})}
    image = value.get("image")

    # Check if we have old format with image field and no media field
    if image and "media" not in value:
        # Wrap the image data in a StreamBlock format with type='image'
        value["media"] = [
            {
                "type": "image",
                "value": image,
                "id": str(uuid.uuid4()),
            }
        ]
        # Remove the old image field
        value.pop("image", None)
        block_data["value"] = value

    return block_data


def walk_and_transform(data):
    """Recursively walk through the block tree and transform ShowcaseBlock."""
    if isinstance(data, dict):
        # Transform showcase blocks
        block_type = data.get("type")
        if block_type == "showcase":
            data = migrate_showcase_block(data)

        # Recursively transform nested structures
        for key, value in data.items():
            if isinstance(value, (dict, list, MutableSequence)):
                data[key] = walk_and_transform(value)

    elif isinstance(data, (list, MutableSequence)):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[i] = walk_and_transform(item)

    return data


def update_pages(apps, schema_editor):
    HomePage = apps.get_model("cms", "HomePage")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Get content type ID for HomePage
    homepage_ct = ContentType.objects.get_for_model(HomePage)

    # Migrate ALL HomePage revisions (including deleted pages)
    print("Migrating HomePage revisions...")
    for revision in Revision.objects.filter(content_type=homepage_ct).iterator():
        modified = False

        # Migrate lower_content (where ShowcaseBlock is used)
        if "lower_content" in revision.content:
            try:
                content = json.loads(revision.content["lower_content"])
                updated_value = walk_and_transform(content)
                revision.content["lower_content"] = json.dumps(updated_value)
                modified = True
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Skip malformed data

        if modified:
            revision.save(update_fields=["content"])

    # Update current HomePage state (only existing pages)
    print("Migrating current HomePage data...")
    for page in HomePage.objects.all():
        if page.lower_content:
            page.lower_content.raw_data = walk_and_transform(page.lower_content.raw_data)
            page.save(update_fields=["lower_content"])

    print("Migration complete!")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0037_remove_thankspage_pre_footer"),
    ]

    operations = [
        migrations.RunPython(update_pages, migrations.RunPython.noop),
    ]
