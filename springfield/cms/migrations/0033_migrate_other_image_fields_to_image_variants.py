# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Migration to migrate StepCardBlock from old image/dark_image format
# to ImageVariantsBlock structure

import json
from collections.abc import MutableSequence

from django.db import migrations


def migrate_step_card_block(card_data):
    """Migrate StepCardBlock image field from old format to ImageVariantsBlock.

    StepCards in ListBlocks are structured as {'type': 'item', 'value': {...}, 'id': ...}
    We don't check the type since ListBlock uses 'item', not 'step_card'.
    """
    if not isinstance(card_data, dict):
        return card_data

    # Get the inner value dict
    inner_value = card_data.get("value", {})
    if not isinstance(inner_value, dict):
        return card_data

    image = inner_value.get("image")
    dark_image = inner_value.get("dark_image")

    # Check if image is old format (integer ID)
    if isinstance(image, int):
        inner_value["image"] = {
            "image": image,
            "settings": {
                "mobile_image": None,
                "dark_mode_image": dark_image,
                "dark_mode_mobile_image": None,
            },
        }
        inner_value.pop("dark_image", None)
        # Update the card_data with migrated value
        card_data["value"] = inner_value
    # Check if image is already a dict but still has dark_image at top level
    elif isinstance(image, dict) and "dark_image" in inner_value:
        dark_image_id = inner_value.pop("dark_image")
        # If the image dict doesn't have settings yet, migrate it
        if "settings" not in image:
            inner_value["image"] = {
                "image": image.get("image") if isinstance(image, dict) else image,
                "settings": {
                    "mobile_image": None,
                    "dark_mode_image": dark_image_id,
                    "dark_mode_mobile_image": None,
                },
            }
        card_data["value"] = inner_value

    return card_data


def walk_and_transform(data):
    """Recursively walk through the block tree and transform step cards."""
    if isinstance(data, dict):
        # Check if this is a step_cards block (StepCardListBlock)
        if data.get("type") == "step_cards":
            # step_cards uses ListBlock, so cards is a list
            value = data.get("value", {})
            cards = value.get("cards", [])
            if isinstance(cards, list):
                migrated_cards = []
                for card in cards:
                    migrated_cards.append(migrate_step_card_block(card))
                value["cards"] = migrated_cards
                data["value"] = value

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
    FreeFormPage = apps.get_model("cms", "FreeFormPage")
    WhatsNewPage = apps.get_model("cms", "WhatsNewPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Get content type IDs
    freeformpage_ct = ContentType.objects.get_for_model(FreeFormPage)
    whatsnewpage_ct = ContentType.objects.get_for_model(WhatsNewPage)

    # Migrate ALL FreeFormPage revisions (including deleted pages)
    print("Migrating FreeFormPage revisions...")
    for revision in Revision.objects.filter(content_type=freeformpage_ct).iterator():
        if "content" in revision.content:
            try:
                content = json.loads(revision.content["content"])
                updated_value = walk_and_transform(content)
                revision.content["content"] = json.dumps(updated_value)
                revision.save(update_fields=["content"])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Skip malformed data

    # Update current FreeFormPage state (only existing pages)
    print("Migrating current FreeFormPage data...")
    for page in FreeFormPage.objects.all():
        page.content.raw_data = walk_and_transform(page.content.raw_data)
        page.save(update_fields=["content"])

    # Migrate ALL WhatsNewPage revisions (including deleted pages)
    print("Migrating WhatsNewPage revisions...")
    for revision in Revision.objects.filter(content_type=whatsnewpage_ct).iterator():
        if "content" in revision.content:
            try:
                content = json.loads(revision.content["content"])
                updated_value = walk_and_transform(content)
                revision.content["content"] = json.dumps(updated_value)
                revision.save(update_fields=["content"])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Skip malformed data

    # Update current WhatsNewPage state (only existing pages)
    print("Migrating current WhatsNewPage data...")
    for page in WhatsNewPage.objects.all():
        page.content.raw_data = walk_and_transform(page.content.raw_data)
        page.save(update_fields=["content"])

    print("Migration complete!")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0032_migrate_existing_image_variants"),
    ]

    operations = [
        migrations.RunPython(update_pages, migrations.RunPython.noop),
    ]
