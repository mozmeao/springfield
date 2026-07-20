# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to update BannerBlock and KitBannerBlock settings after the
# banner theme refactor (WT-1140):
#   - BannerSettings.theme: "purple" → "purple-radial-gradient"
#                           "dark-purple" → "dark-purple-gradient"
#   - KitBannerSettings: add missing background_theme field with default "purple-radial-gradient"

import json
from collections.abc import MutableSequence

from django.db import migrations

BANNER_THEME_MAP = {
    "purple": "purple-radial-gradient",
    "dark-purple": "dark-purple-gradient",
}


def update_banner_themes(data):
    """Recursively update banner and kit_banner block settings. Returns True if changed."""
    changed = False
    if isinstance(data, dict):
        block_type = data.get("type")
        if block_type == "banner" and "value" in data:
            settings = data["value"].get("settings")
            if isinstance(settings, dict):
                old_theme = settings.get("theme")
                new_theme = BANNER_THEME_MAP.get(old_theme)
                if new_theme:
                    settings["theme"] = new_theme
                    changed = True
        elif block_type == "kit_banner" and "value" in data:
            settings = data["value"].get("settings")
            if isinstance(settings, dict) and "background_theme" not in settings:
                settings["background_theme"] = "purple-radial-gradient"
                changed = True
        for value in data.values():
            if update_banner_themes(value):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if update_banner_themes(item):
                changed = True
    return changed


def convert_pages(apps, schema_editor):
    models_config = [
        ("FreeFormPage", ["content"]),
        ("FreeFormPage2026", ["upper_content", "content"]),
        ("ArticleThemePage", ["upper_content", "content"]),
        ("WhatsNewPage2026", ["upper_content", "content"]),
        ("SmartWindowPage", ["content"]),
        ("SmartWindowExplainerPage", ["upper_content", "content"]),
    ]

    for model_name, field_names in models_config:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            changed_fields = []
            for field_name in field_names:
                stream_value = getattr(page, field_name)
                if stream_value and update_banner_themes(stream_value.raw_data):
                    changed_fields.append(field_name)
            if changed_fields:
                page.save(update_fields=changed_fields)


def convert_revisions(apps, schema_editor):
    """Update Wagtail page revisions to use the new banner theme values."""
    try:
        Revision = apps.get_model("wagtailcore", "Revision")
        ContentType = apps.get_model("contenttypes", "ContentType")
    except LookupError:
        return

    models_config = [
        ("cms", "freeformpage", ["content"]),
        ("cms", "freeformpage2026", ["upper_content", "content"]),
        ("cms", "articlethemepage", ["upper_content", "content"]),
        ("cms", "whatsnewpage2026", ["upper_content", "content"]),
        ("cms", "smartwindowpage", ["content"]),
        ("cms", "smartwindowexplainerpage", ["upper_content", "content"]),
    ]

    for app_label, model_name, field_names in models_config:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            continue

        for revision in Revision.objects.filter(base_content_type=content_type).iterator():
            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if update_banner_themes(field_data):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                revision.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0082_update_cards_list_settings"),
    ]

    operations = [
        migrations.RunPython(convert_pages, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(convert_revisions, reverse_code=migrations.RunPython.noop),
    ]
