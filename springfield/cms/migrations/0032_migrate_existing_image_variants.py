# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Migration to migrate existing ImageVariantsBlock data from old formats
# to proper ImageVariantsBlock structure

import json
from collections.abc import MutableSequence

from django.db import migrations


def migrate_sticker_card(block_data):
    """Migrate StickerCardBlock image field from old format to ImageVariantsBlock."""
    if block_data.get("type") != "sticker_card":
        return block_data

    value = {**block_data.get("value", {})}
    image = value.get("image")
    dark_image = value.get("dark_image")

    # Check if image is old format (integer ID)
    if isinstance(image, int):
        value["image"] = {
            "image": image,
            "settings": {
                "mobile_image": None,
                "dark_mode_image": dark_image,
                "dark_mode_mobile_image": None,
            },
        }
        value.pop("dark_image", None)
        block_data["value"] = value
    # Check if image is already a dict but still has dark_image at top level
    elif isinstance(image, dict) and "dark_image" in value:
        dark_image_id = value.pop("dark_image")
        # If the image dict doesn't have settings yet, migrate it
        if "settings" not in image:
            value["image"] = {
                "image": image.get("image") if isinstance(image, dict) else image,
                "settings": {
                    "mobile_image": None,
                    "dark_mode_image": dark_image_id,
                    "dark_mode_mobile_image": None,
                },
            }
        block_data["value"] = value

    return block_data


def migrate_illustration_card(block_data):
    """Migrate IllustrationCardBlock image field from old format to ImageVariantsBlock."""
    if block_data.get("type") != "illustration_card":
        return block_data

    value = {**block_data.get("value", {})}
    image = value.get("image")
    dark_image = value.get("dark_image")

    # Check if image is old format (integer ID)
    if isinstance(image, int):
        value["image"] = {
            "image": image,
            "settings": {
                "mobile_image": None,
                "dark_mode_image": dark_image,
                "dark_mode_mobile_image": None,
            },
        }
        value.pop("dark_image", None)
        block_data["value"] = value
    # Check if image is already a dict but still has dark_image at top level
    elif isinstance(image, dict) and "dark_image" in value:
        dark_image_id = value.pop("dark_image")
        # If the image dict doesn't have settings yet, migrate it
        if "settings" not in image:
            value["image"] = {
                "image": image.get("image") if isinstance(image, dict) else image,
                "settings": {
                    "mobile_image": None,
                    "dark_mode_image": dark_image_id,
                    "dark_mode_mobile_image": None,
                },
            }
        block_data["value"] = value

    return block_data


def migrate_media_value(block_data):
    block_data["value"] = {**block_data.get("value", {})}
    media_items = block_data["value"].get("media", [])
    if media_items:
        migrated_media = []
        for item in media_items:
            if item.get("type") == "image":
                value = item.get("value", {})
                image = value.get("image")
                dark_image = value.get("dark_image")

                # Check if image is old format (integer ID)
                if isinstance(image, int):
                    value = {
                        "image": image,
                        "settings": {
                            "mobile_image": None,
                            "dark_mode_image": dark_image,
                            "dark_mode_mobile_image": None,
                        },
                    }
                    value.pop("dark_image", None)
                    item["value"] = value
                # Check if image is already a dict but still has dark_image at top level
                elif isinstance(image, dict) and "dark_image" in value:
                    dark_image_id = value.pop("dark_image")
                    # If the image dict doesn't have settings yet, migrate it
                    if "settings" not in image:
                        value = {
                            "image": image.get("image") if isinstance(image, dict) else image,
                            "settings": {
                                "mobile_image": None,
                                "dark_mode_image": dark_image_id,
                                "dark_mode_mobile_image": None,
                            },
                        }
                    item["value"] = value
            migrated_media.append(item)
        block_data["value"]["media"] = migrated_media
    return block_data


def migrate_home_carousel_slide(slide_data):
    """Migrate HomeCarouselSlide image field from old format to ImageVariantsBlock."""
    # Slides are structured as {'type': ..., 'value': {...}, 'id': ...}
    # We need to migrate the image inside the 'value' dict
    if not isinstance(slide_data, dict):
        return slide_data

    # Get the inner value dict
    inner_value = slide_data.get("value", {})
    if not isinstance(inner_value, dict):
        return slide_data

    image = inner_value.get("image")

    # Check if image is old format (integer ID)
    if isinstance(image, int):
        inner_value["image"] = {
            "image": image,
            "settings": {
                "mobile_image": None,
                "dark_mode_image": None,
                "dark_mode_mobile_image": None,
            },
        }
        # Update the slide_data with migrated value
        slide_data["value"] = inner_value

    return slide_data


def migrate_showcase_block(block_data):
    """Migrate ShowcaseBlock from desktop_image/mobile_image to ImageVariantsBlock."""
    if block_data.get("type") != "showcase":
        return block_data

    value = {**block_data.get("value", {})}
    desktop_image = value.get("desktop_image")
    mobile_image = value.get("mobile_image")

    # Check if we have old format with desktop_image or mobile_image (even if just one exists)
    if ("desktop_image" in value or "mobile_image" in value) and "image" not in value:
        # Extract image IDs from LightDarkImageBlock structures
        desktop_light = desktop_image.get("image") if isinstance(desktop_image, dict) else None
        desktop_dark = desktop_image.get("dark_image") if isinstance(desktop_image, dict) else None
        mobile_light = mobile_image.get("image") if isinstance(mobile_image, dict) else None
        mobile_dark = mobile_image.get("dark_image") if isinstance(mobile_image, dict) else None

        # Build new ImageVariantsBlock structure
        # Use desktop as primary, fall back to mobile if desktop doesn't exist
        primary_image = desktop_light if desktop_light is not None else mobile_light

        value["image"] = {
            "image": primary_image,
            "settings": {
                "mobile_image": mobile_light,
                "dark_mode_image": desktop_dark,
                "dark_mode_mobile_image": mobile_dark,
            },
        }
        value.pop("desktop_image", None)
        value.pop("mobile_image", None)
        block_data["value"] = value

    return block_data


def migrate_card_gallery_card(card_data):
    """Migrate CardGalleryCard image field from old format to ImageVariantsBlock."""
    value = {**card_data}
    image = value.get("image")

    # Check if image is old format (integer ID)
    if isinstance(image, int):
        value["image"] = {
            "image": image,
            "settings": {
                "mobile_image": None,
                "dark_mode_image": None,
                "dark_mode_mobile_image": None,
            },
        }

    return value


def walk_and_transform(data):
    """Recursively walk through the block tree and transform ImageVariantsBlock usage."""
    if isinstance(data, dict):
        # Transform specific block types
        block_type = data.get("type")

        if block_type == "sticker_card":
            data = migrate_sticker_card(data)
        elif block_type == "illustration_card":
            data = migrate_illustration_card(data)
        elif block_type in ["media_content", "intro", "banner"]:
            data = migrate_media_value(data)
        elif block_type == "showcase":
            data = migrate_showcase_block(data)
        elif block_type == "carousel":
            # Handle HomeCarouselBlock slides
            value = data.get("value", {})
            slides = value.get("slides", [])
            if isinstance(slides, (list, MutableSequence)):
                migrated_slides = []
                for slide in slides:
                    migrated_slides.append(migrate_home_carousel_slide(slide))
                value["slides"] = migrated_slides
                data["value"] = value
        elif block_type == "card_gallery":
            # Handle CardGalleryCard images in main_card and secondary_card
            value = data.get("value", {})
            if "main_card" in value:
                value["main_card"] = migrate_card_gallery_card(value["main_card"])
            if "secondary_card" in value:
                value["secondary_card"] = migrate_card_gallery_card(value["secondary_card"])
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
    HomePage = apps.get_model("cms", "HomePage")
    FreeFormPage = apps.get_model("cms", "FreeFormPage")
    WhatsNewPage = apps.get_model("cms", "WhatsNewPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Get content type IDs for each page type
    homepage_ct = ContentType.objects.get_for_model(HomePage)
    freeformpage_ct = ContentType.objects.get_for_model(FreeFormPage)
    whatsnewpage_ct = ContentType.objects.get_for_model(WhatsNewPage)

    # Migrate ALL HomePage revisions (including deleted pages)
    print("Migrating HomePage revisions...")
    for revision in Revision.objects.filter(content_type=homepage_ct).iterator():
        modified = False

        # Migrate upper_content
        if "upper_content" in revision.content:
            try:
                content = json.loads(revision.content["upper_content"])
                updated_value = walk_and_transform(content)
                revision.content["upper_content"] = json.dumps(updated_value)
                modified = True
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Skip malformed data

        # Migrate lower_content
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
        page.upper_content.raw_data = walk_and_transform(page.upper_content.raw_data)
        if page.lower_content:
            page.lower_content.raw_data = walk_and_transform(page.lower_content.raw_data)
        page.save(update_fields=["upper_content", "lower_content"])

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
        ("cms", "0031_thankspage_downloadpage_bannersnippet_and_more"),
    ]

    operations = [
        migrations.RunPython(update_pages, migrations.RunPython.noop),
    ]
