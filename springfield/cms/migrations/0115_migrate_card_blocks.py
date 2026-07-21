# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to convert old specialised card block types to the new unified
# CardBlock. Converts: icon_card, sticker_card, illustration_card, outlined_card,
# testimonial_card → card.

import json
import re
from collections.abc import MutableSequence
from uuid import uuid4

from django.db import migrations

_EMPTY_SHOW_TO = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

_EMPTY_IMAGE_VARIANTS = {
    "image": None,
    "settings": {
        "dark_mode_image": None,
        "mobile_image": None,
        "dark_mode_mobile_image": None,
    },
}


def _uid():
    return str(uuid4())


def _strip_italic_tags(value):
    """Remove <i> and <em> tags (and their closing counterparts) from a RichText value."""
    if not value:
        return value
    return re.sub(r"</?(?:i|em)>", "", value)


def _buttons_row(buttons):
    """Wrap a MixedButtonsBlock list into a ButtonRowBlock content item."""
    return {"type": "buttons", "value": {"spacing": "", "buttons": buttons, "help_text": ""}, "id": _uid()}


def migrate_icon_card(block):
    value = block.get("value", {})
    settings = value.get("settings", {})

    media = []
    if icon := value.get("icon"):
        media.append({"type": "icon", "value": icon, "id": _uid()})

    content = []
    if headline := value.get("headline"):
        content.append(
            {
                "type": "heading",
                "value": {"superheading_text": "", "heading_text": headline, "subheading_text": ""},
                "id": _uid(),
            }
        )
    if body := value.get("content"):
        content.append({"type": "content", "value": body, "id": _uid()})
    if buttons := value.get("buttons"):
        content.append(_buttons_row(buttons))

    return {
        "type": "card",
        "value": {
            "settings": {
                "variant": "",
                "align": "start",
                "expand_link": settings.get("expand_link", False),
                "show_to": settings.get("show_to", _EMPTY_SHOW_TO),
            },
            "media": media,
            "content": content,
        },
        "id": block.get("id", _uid()),
    }


def migrate_sticker_card(block):
    value = block.get("value", {})
    settings = value.get("settings", {})

    content = []
    content.append(
        {
            "type": "heading",
            "value": {
                "superheading_text": _strip_italic_tags(value.get("superheading", "")),
                "heading_text": value.get("headline", ""),
                "subheading_text": "",
            },
            "id": _uid(),
        }
    )
    if image := value.get("image"):
        content.append({"type": "pictogram", "value": image, "id": _uid()})
    if body := value.get("content"):
        content.append({"type": "content", "value": body, "id": _uid()})
    if buttons := value.get("buttons"):
        content.append(_buttons_row(buttons))

    return {
        "type": "card",
        "value": {
            "settings": {
                "variant": "filled",
                "align": "center",
                "expand_link": settings.get("expand_link", False),
                "show_to": settings.get("show_to", _EMPTY_SHOW_TO),
            },
            "media": [],
            "content": content,
        },
        "id": block.get("id", _uid()),
    }


def migrate_illustration_card(block):
    value = block.get("value", {})
    settings = value.get("settings", {})

    top_media = []
    if media := value.get("media"):
        top_media.append({"type": "media", "value": media, "id": _uid()})

    content = []
    content.append(
        {
            "type": "heading",
            "value": {
                "superheading_text": value.get("eyebrow", ""),
                "heading_text": value.get("headline", ""),
                "subheading_text": "",
            },
            "id": _uid(),
        }
    )
    if body := value.get("content"):
        content.append({"type": "content", "value": body, "id": _uid()})
    if buttons := value.get("buttons"):
        content.append(_buttons_row(buttons))

    return {
        "type": "card",
        "value": {
            "settings": {
                "variant": "",
                "align": "start",
                "expand_link": settings.get("expand_link", False),
                "show_to": settings.get("show_to", _EMPTY_SHOW_TO),
            },
            "media": top_media,
            "content": content,
        },
        "id": block.get("id", _uid()),
    }


def migrate_outlined_card(block):
    value = block.get("value", {})
    settings = value.get("settings", {})

    content = []
    content.append(
        {
            "type": "heading",
            "value": {
                "superheading_text": "",
                "heading_text": value.get("headline", ""),
                "subheading_text": "",
            },
            "id": _uid(),
        }
    )
    sticker = value.get("sticker", {})
    if sticker and sticker.get("image"):
        content.append({"type": "pictogram", "value": sticker, "id": _uid()})
    if body := value.get("content"):
        content.append({"type": "content", "value": body, "id": _uid()})
    if buttons := value.get("buttons"):
        content.append(_buttons_row(buttons))

    return {
        "type": "card",
        "value": {
            "settings": {
                "variant": "outline",
                "align": "start",
                "expand_link": settings.get("expand_link", False),
                "show_to": settings.get("show_to", _EMPTY_SHOW_TO),
            },
            "media": [],
            "content": content,
        },
        "id": block.get("id", _uid()),
    }


def migrate_testimonial_card(block):
    value = block.get("value", {})
    settings = value.get("settings", {})

    testimonial = {
        "content": value.get("content", ""),
        "attribution": value.get("attribution", ""),
        "attribution_role": value.get("attribution_role", ""),
        "attribution_image": value.get("attribution_image", _EMPTY_IMAGE_VARIANTS),
    }

    return {
        "type": "card",
        "value": {
            "settings": {
                "variant": "outline",
                "align": "start",
                "expand_link": False,
                "show_to": settings.get("show_to", _EMPTY_SHOW_TO),
            },
            "media": [],
            "content": [{"type": "testimonial", "value": testimonial, "id": _uid()}],
        },
        "id": block.get("id", _uid()),
    }


_MIGRATORS = {
    "icon_card": migrate_icon_card,
    "sticker_card": migrate_sticker_card,
    "illustration_card": migrate_illustration_card,
    "outlined_card": migrate_outlined_card,
    "testimonial_card": migrate_testimonial_card,
}


def walk_and_transform(data):
    """Recursively walk the block tree and convert old card types to the new card block."""
    if isinstance(data, dict):
        block_type = data.get("type")
        if block_type in _MIGRATORS:
            return _MIGRATORS[block_type](data)
        for key, value in data.items():
            if isinstance(value, (dict, list, MutableSequence)):
                data[key] = walk_and_transform(value)
    elif isinstance(data, (list, MutableSequence)):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[i] = walk_and_transform(item)
    return data


def _migrate_revision(revision, field_names):
    modified = False
    for field_name in field_names:
        if field_name not in revision.content:
            continue
        try:
            data = json.loads(revision.content[field_name])
            revision.content[field_name] = json.dumps(walk_and_transform(data))
            modified = True
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    if modified:
        revision.save(update_fields=["content"])


def _migrate_page(page, field_names):
    fields_to_save = []
    for field_name in field_names:
        field_value = getattr(page, field_name, None)
        if field_value is None:
            continue
        field_value.raw_data = walk_and_transform(field_value.raw_data)
        fields_to_save.append(field_name)

    if not fields_to_save:
        return

    # Always persist the migrated data to the live database row first.
    page.save(update_fields=fields_to_save)

    if not page.has_unpublished_changes:
        # No pending draft — fetch the real model instance (apps.get_model returns a
        # historical model that lacks Wagtail page methods) so we can create a revision
        # and mark the migrated content as the published version in the CMS.
        from wagtail.models import Page as WagtailPage  # inline: needed after apps.get_model

        real_page = WagtailPage.objects.get(pk=page.pk).specific
        if real_page.alias_of_id is not None:
            return
        revision = real_page.save_revision()
        revision.publish()


_PAGE_CONFIGS = [
    ("HomePage", ["upper_content"]),
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage2026", ["upper_content", "content"]),
    ("SmartWindowPage", ["content"]),
    ("SmartWindowExplainerPage", ["upper_content", "content"]),
    ("ArticleThemePage", ["content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
]


def update_pages(apps, schema_editor):
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    for model_name, field_names in _PAGE_CONFIGS:
        Model = apps.get_model("cms", model_name)
        ct = ContentType.objects.get_for_model(Model)

        print(f"Migrating {model_name} revisions...")
        for revision in Revision.objects.filter(content_type=ct).iterator():
            _migrate_revision(revision, field_names)

        print(f"Migrating current {model_name} pages...")
        for page in Model.objects.all():
            _migrate_page(page, field_names)

    print("Card block migration complete!")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0114_merge_20260714_1149"),
    ]

    operations = [
        migrations.RunPython(update_pages, migrations.RunPython.noop),
    ]
