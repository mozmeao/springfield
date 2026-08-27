# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Converts TabBlock's old `image` field to the new `media` StreamBlock.
# The old field was ImageChooserBlock (stores an int ID) but may also appear
# as an ImageVariantsBlock dict {image: <id>, settings: {...}} in some databases.
# Both formats are handled; the result is always a plain int ID in the media block.

import json
import uuid
from collections.abc import MutableSequence

from django.db import migrations


def migrate_tab(list_item):
    # ListBlock stores each tab as {"type": "item", "value": {...tab fields...}, "id": "..."}
    if not isinstance(list_item, dict):
        return list_item

    tab = list_item.get("value")
    if not isinstance(tab, dict) or "media" in tab:
        return list_item

    image = tab.get("image")

    # Plain ImageChooserBlock int ID
    if isinstance(image, int):
        image_id = image
    # ImageVariantsBlock dict {image: <id>, settings: {...}}
    elif isinstance(image, dict) and isinstance(image.get("image"), int):
        image_id = image["image"]
    else:
        return list_item

    tab["media"] = [
        {
            "type": "image",
            "id": uuid.uuid4().hex,
            "value": {
                "image": image_id,
                "settings": {"dark_mode_image": None, "mobile_image": None, "dark_mode_mobile_image": None},
            },
        }
    ]
    del tab["image"]
    return list_item


def walk_and_transform(data):
    if isinstance(data, dict):
        if data.get("type") == "tabs":
            value = data.get("value", {})
            tabs = value.get("tabs", [])
            if isinstance(tabs, (list, MutableSequence)):
                value["tabs"] = [migrate_tab(tab) for tab in tabs]
                data["value"] = value

        for key, val in data.items():
            if isinstance(val, (dict, list, MutableSequence)):
                data[key] = walk_and_transform(val)

    elif isinstance(data, (list, MutableSequence)):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[i] = walk_and_transform(item)

    return data


def migrate_pages(apps, schema_editor):
    ReferralHubPage = apps.get_model("cms", "ReferralHubPage")
    ReferralGetFirefoxPage = apps.get_model("cms", "ReferralGetFirefoxPage")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    hub_ct = ContentType.objects.get_for_model(ReferralHubPage)
    getff_ct = ContentType.objects.get_for_model(ReferralGetFirefoxPage)

    for revision in Revision.objects.filter(content_type=hub_ct).iterator():
        modified = False
        for field in ("upper_content", "extra_content"):
            if field in revision.content:
                try:
                    content = json.loads(revision.content[field])
                    revision.content[field] = json.dumps(walk_and_transform(content))
                    modified = True
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass
        if modified:
            revision.save(update_fields=["content"])

    for page in ReferralHubPage.objects.all():
        page.upper_content.raw_data = walk_and_transform(page.upper_content.raw_data)
        if page.extra_content:
            page.extra_content.raw_data = walk_and_transform(page.extra_content.raw_data)
        page.save(update_fields=["upper_content", "extra_content"])

    for revision in Revision.objects.filter(content_type=getff_ct).iterator():
        if "upper_content" in revision.content:
            try:
                content = json.loads(revision.content["upper_content"])
                revision.content["upper_content"] = json.dumps(walk_and_transform(content))
                revision.save(update_fields=["content"])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

    for page in ReferralGetFirefoxPage.objects.all():
        page.upper_content.raw_data = walk_and_transform(page.upper_content.raw_data)
        page.save(update_fields=["upper_content"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0144_blogarticlepage_bottom_banner"),
    ]

    operations = [
        migrations.RunPython(migrate_pages, migrations.RunPython.noop),
    ]
