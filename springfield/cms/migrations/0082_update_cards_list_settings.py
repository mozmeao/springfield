# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to convert CardsListBlock2026 settings from the legacy format
# (scroll BooleanBlock) to the new format (container_width/cards_per_row/two_wide_xs).
# Also applies page-specific defaults:
#   - container_width="fill" on HomePage and DownloadPage
#   - two_wide_xs=True on DownloadPage, ArticleThemePage, SmartWindowPage (illustration
#     cards only), and WhatsNewPage2026 versions 149 and 150

import json
from collections.abc import MutableSequence

from django.db import migrations


def _normalize_settings(settings):
    """Convert legacy scroll flag to new format. Returns True if changed."""
    if settings.get("scroll") is True:
        settings.clear()
        settings["container_width"] = "scroll"
        settings["cards_per_row"] = ""
        settings["two_wide_xs"] = False
        return True
    if "container_width" not in settings:
        settings.setdefault("container_width", "")
        settings.setdefault("cards_per_row", "")
        settings.setdefault("two_wide_xs", False)
        return True
    return False


def update_cards_list_settings(data, *, set_fill=False, set_two_wide_xs=False):
    """Recursively find cards_list blocks and update their settings. Returns True if changed."""
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "cards_list" and "value" in data:
            card_settings = data["value"].get("settings")
            if card_settings is None:
                data["value"]["settings"] = {"container_width": "", "cards_per_row": "", "two_wide_xs": False}
                card_settings = data["value"]["settings"]
                changed = True
            if isinstance(card_settings, dict):
                if _normalize_settings(card_settings):
                    changed = True
                if set_fill and card_settings.get("container_width") == "":
                    card_settings["container_width"] = "fill"
                    changed = True
                if set_two_wide_xs and not card_settings.get("two_wide_xs"):
                    card_settings["two_wide_xs"] = True
                    changed = True
        for value in data.values():
            if update_cards_list_settings(value, set_fill=set_fill, set_two_wide_xs=set_two_wide_xs):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if update_cards_list_settings(item, set_fill=set_fill, set_two_wide_xs=set_two_wide_xs):
                changed = True
    return changed


def update_smart_window_cards_list_settings(data):
    """SmartWindowPage variant: apply fill+two_wide_xs only to illustration_card lists."""
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "cards_list" and "value" in data:
            card_settings = data["value"].get("settings")
            cards = data["value"].get("cards", [])
            has_illustration_cards = any(c.get("type") == "illustration_card" for c in cards)
            if card_settings is None:
                data["value"]["settings"] = {"container_width": "", "cards_per_row": "", "two_wide_xs": False}
                card_settings = data["value"]["settings"]
                changed = True
            if isinstance(card_settings, dict):
                if _normalize_settings(card_settings):
                    changed = True
                if has_illustration_cards:
                    if card_settings.get("container_width") == "":
                        card_settings["container_width"] = "fill"
                        changed = True
                    if not card_settings.get("two_wide_xs"):
                        card_settings["two_wide_xs"] = True
                        changed = True
        for value in data.values():
            if update_smart_window_cards_list_settings(value):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if update_smart_window_cards_list_settings(item):
                changed = True
    return changed


def convert_pages(apps, schema_editor):
    # (model_name, field_names, set_fill, set_two_wide_xs)
    # WhatsNewPage2026 two_wide_xs is version-dependent and handled inline.
    # SmartWindowPage uses a dedicated converter function.
    models_config = [
        ("HomePage", ["upper_content", "lower_content"], True, False),
        ("DownloadPage", ["content"], True, True),
        ("ArticleThemePage", ["upper_content", "content"], False, True),
        ("FreeFormPage2026", ["upper_content", "content"], False, False),
        ("WhatsNewPage2026", ["upper_content", "content"], False, None),
    ]

    for model_name, field_names, set_fill, set_two_wide_xs in models_config:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            two_wide = set_two_wide_xs
            if model_name == "WhatsNewPage2026":
                two_wide = getattr(page, "version", "") in ("149", "150")

            changed_fields = []
            for field_name in field_names:
                stream_value = getattr(page, field_name)
                if stream_value and update_cards_list_settings(
                    stream_value.raw_data,
                    set_fill=set_fill,
                    set_two_wide_xs=two_wide,
                ):
                    changed_fields.append(field_name)
            if changed_fields:
                page.save(update_fields=changed_fields)

    SmartWindowPage = apps.get_model("cms", "SmartWindowPage")
    for page in SmartWindowPage.objects.all():
        changed_fields = []
        for field_name in ["content"]:
            stream_value = getattr(page, field_name)
            if stream_value and update_smart_window_cards_list_settings(stream_value.raw_data):
                changed_fields.append(field_name)
        if changed_fields:
            page.save(update_fields=changed_fields)


def convert_revisions(apps, schema_editor):
    """Update Wagtail page revisions to use the new cards_list settings format."""
    try:
        Revision = apps.get_model("wagtailcore", "Revision")
        ContentType = apps.get_model("contenttypes", "ContentType")
    except LookupError:
        return

    # (app_label, model_name, field_names, set_fill, set_two_wide_xs)
    # WhatsNewPage2026 two_wide_xs is version-dependent and handled inline.
    # SmartWindowPage uses the dedicated converter function.
    models_config = [
        ("cms", "homepage", ["upper_content", "lower_content"], True, False),
        ("cms", "downloadpage", ["content"], True, True),
        ("cms", "articlethemepage", ["upper_content", "content"], False, True),
        ("cms", "freeformpage2026", ["upper_content", "content"], False, False),
        ("cms", "whatsnewpage2026", ["upper_content", "content"], False, None),
    ]

    for app_label, model_name, field_names, set_fill, set_two_wide_xs in models_config:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            continue

        for revision in Revision.objects.filter(base_content_type=content_type).iterator():
            two_wide = set_two_wide_xs
            if model_name == "whatsnewpage2026":
                version = revision.content.get("version", "")
                two_wide = version in ("149", "150")

            modified = False
            for field_name in field_names:
                raw_json = revision.content.get(field_name)
                if not raw_json:
                    continue
                try:
                    field_data = json.loads(raw_json)
                    if update_cards_list_settings(
                        field_data,
                        set_fill=set_fill,
                        set_two_wide_xs=two_wide,
                    ):
                        revision.content[field_name] = json.dumps(field_data)
                        modified = True
                except (json.JSONDecodeError, TypeError):
                    pass
            if modified:
                revision.save(update_fields=["content"])

    try:
        swp_content_type = ContentType.objects.get(app_label="cms", model="smartwindowpage")
    except ContentType.DoesNotExist:
        return

    for revision in Revision.objects.filter(base_content_type=swp_content_type).iterator():
        modified = False
        raw_json = revision.content.get("content")
        if raw_json:
            try:
                field_data = json.loads(raw_json)
                if update_smart_window_cards_list_settings(field_data):
                    revision.content["content"] = json.dumps(field_data)
                    modified = True
            except (json.JSONDecodeError, TypeError):
                pass
        if modified:
            revision.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0081_freeformpage2026_show_navigation_and_more"),
    ]

    operations = [
        migrations.RunPython(convert_pages, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(convert_revisions, reverse_code=migrations.RunPython.noop),
    ]
