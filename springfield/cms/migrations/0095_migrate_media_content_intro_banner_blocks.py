# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Data migration for MediaContentBlock, IntroBlock2026, BannerBlock, KitBannerBlock.

These blocks were refactored to use a unified content StreamField:
- MediaContentBlock: eyebrow/headline → heading block; tags + content + buttons → content stream
- IntroBlock2026/BannerBlock/KitBannerBlock: heading.subheading_text + tags + buttons → content stream
"""

import json
import uuid
from collections.abc import MutableSequence

from django.db import migrations


def new_uuid():
    return str(uuid.uuid4())


def transform_media_content_value(value):
    heading = {
        "superheading_text": value.get("eyebrow", ""),
        "heading_text": value.get("headline", ""),
        "subheading_text": "",
    }

    content = []

    if value.get("tags"):
        content.append({"type": "tags", "id": new_uuid(), "value": value["tags"]})

    for item in value.get("content", []):
        content.append(item)

    if value.get("buttons"):
        content.append({"type": "buttons", "id": new_uuid(), "value": value["buttons"]})

    return {
        "settings": value.get("settings", {}),
        "media": value.get("media", []),
        "heading": heading,
        "content": content,
    }


def transform_heading_block_value(value):
    """Move heading.subheading_text + top-level tags + buttons into a content stream."""
    heading = value.get("heading", {})
    subheading = heading.get("subheading_text", "")

    content = []

    if value.get("tags"):
        content.append({"type": "tags", "id": new_uuid(), "value": value["tags"]})

    if subheading:
        content.append({"type": "rich_text", "id": new_uuid(), "value": subheading})

    if value.get("buttons"):
        content.append({"type": "buttons", "id": new_uuid(), "value": value["buttons"]})

    new_heading = {
        "superheading_text": heading.get("superheading_text", ""),
        "heading_text": heading.get("heading_text", ""),
        "subheading_text": "",
    }

    result = {
        "settings": value.get("settings", {}),
        "heading": new_heading,
        "content": content,
    }

    if "media" in value:
        result["media"] = value["media"]

    return result


def is_intro_2026(value):
    """IntroBlock2026 has settings.layout; old IntroBlock has settings.media_position."""
    return "layout" in value.get("settings", {})


def walk_and_transform(data):
    """Recursively walk block data and transform target block types in-place."""
    if isinstance(data, dict):
        block_type = data.get("type", "")
        value = data.get("value")

        if block_type == "media_content" and isinstance(value, dict):
            data["value"] = transform_media_content_value(value)
        elif block_type in ("banner", "kit_banner") and isinstance(value, dict):
            data["value"] = transform_heading_block_value(value)
        elif block_type == "intro" and isinstance(value, dict) and is_intro_2026(value):
            data["value"] = transform_heading_block_value(value)
        else:
            for key, val in data.items():
                if isinstance(val, (dict, list, MutableSequence)):
                    data[key] = walk_and_transform(val)

    elif isinstance(data, (list, MutableSequence)):
        for idx, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[idx] = walk_and_transform(item)

    return data


def transform_page(page, field_names):
    published_revision = page.live_revision
    latest_revision = page.latest_revision

    for field_name in field_names:
        field_value = getattr(page, field_name)
        if field_value:
            walk_and_transform(field_value.raw_data)
    page.save(update_fields=field_names)

    if published_revision:
        for field_name in field_names:
            if field_name in published_revision.content:
                raw = published_revision.content[field_name]
                data = json.loads(raw) if isinstance(raw, str) else raw
                updated = walk_and_transform(data)
                published_revision.content[field_name] = json.dumps(updated) if isinstance(raw, str) else updated
        published_revision.save(update_fields=["content"])

    if latest_revision and latest_revision != published_revision:
        for field_name in field_names:
            if field_name in latest_revision.content:
                raw = latest_revision.content[field_name]
                data = json.loads(raw) if isinstance(raw, str) else raw
                updated = walk_and_transform(data)
                latest_revision.content[field_name] = json.dumps(updated) if isinstance(raw, str) else updated
        latest_revision.save(update_fields=["content"])


def migrate_forward(apps, schema_editor):
    FreeFormPage = apps.get_model("cms", "FreeFormPage")
    WhatsNewPage = apps.get_model("cms", "WhatsNewPage")
    FreeFormPage2026 = apps.get_model("cms", "FreeFormPage2026")
    WhatsNewPage2026 = apps.get_model("cms", "WhatsNewPage2026")
    ArticleThemePage = apps.get_model("cms", "ArticleThemePage")
    SmartWindowPage = apps.get_model("cms", "SmartWindowPage")
    SmartWindowExplainerPage = apps.get_model("cms", "SmartWindowExplainerPage")

    # Pages that use banner/kit_banner and section.media_content
    for page in FreeFormPage.objects.all():
        transform_page(page, ["content"])

    for page in WhatsNewPage.objects.all():
        transform_page(page, ["content"])

    # Pages that use IntroBlock2026, media_content, banner, kit_banner
    for page in FreeFormPage2026.objects.all():
        transform_page(page, ["upper_content", "content"])

    for page in WhatsNewPage2026.objects.all():
        transform_page(page, ["upper_content", "content"])

    for page in ArticleThemePage.objects.all():
        transform_page(page, ["upper_content", "content"])

    for page in SmartWindowPage.objects.all():
        transform_page(page, ["content"])

    for page in SmartWindowExplainerPage.objects.all():
        transform_page(page, ["upper_content", "content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0094_alter_articledetailpage_icon"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrations.RunPython.noop),
    ]
