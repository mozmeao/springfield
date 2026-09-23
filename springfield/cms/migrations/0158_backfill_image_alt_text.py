# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Fills the per-use-case alt text fields from each referenced image's
# description, and renames the comparison image header's alt key to image_alt.
# An image with no description is left blank: an empty alt attribute is what
# drops a decorative image out of the accessibility tree, which is what it
# wants. Only source-locale content is filled, so that a translated page keeps
# rendering the English fallback until the next translation sync delivers a
# translated string, rather than storing English as though it were translated.

import json
import os
import sys
from collections.abc import MutableSequence

from django.db import migrations

from wagtail.fields import StreamField

from springfield.base.config_manager import config

# Each entry pairs an image field with the sibling keys found only in the blocks
# that give that image an alt text field of its own. Images in other blocks --
# badge artwork, the dark mode and mobile variants of an image -- have nowhere
# to put alt text, so they are left untouched.
ALT_TEXT_BLOCK_SIBLINGS = {
    "image": ("settings", "list_items", "anchor_id", "link_label", "label"),
    "mobile_image": ("qr_code_data",),
}


def backfill_stream_alt_text(data, descriptions_by_image_id):
    """Walks StreamField raw data, filling each blank alt field from its image's description.

    ``descriptions_by_image_id`` holds only non-decorative images with a
    description, so an image missing from it leaves its alt blank.
    """
    if isinstance(data, dict):
        if "alt" in data and "image_alt" not in data and "label" in data and "image" in data:
            data["image_alt"] = data.pop("alt")

        for image_field_name, sibling_keys in ALT_TEXT_BLOCK_SIBLINGS.items():
            alt_field_name = f"{image_field_name}_alt"
            image_id = data.get(image_field_name)
            if isinstance(image_id, int) and not data.get(alt_field_name) and not data.keys().isdisjoint(sibling_keys):
                data[alt_field_name] = descriptions_by_image_id.get(image_id, "")

        for key, value in data.items():
            if isinstance(value, (dict, list, MutableSequence)):
                data[key] = backfill_stream_alt_text(value, descriptions_by_image_id)

    elif isinstance(data, (list, MutableSequence)):
        for index, item in enumerate(data):
            if isinstance(item, (dict, list, MutableSequence)):
                data[index] = backfill_stream_alt_text(item, descriptions_by_image_id)

    return data


def alt_fields_for_model(model, image_model):
    """Maps each image field name to the sibling field holding its alt text."""
    field_names = {field.name for field in model._meta.local_fields}
    return {
        field.name: f"{field.name}_alt"
        for field in model._meta.local_fields
        if field.is_relation and field.related_model is image_model and f"{field.name}_alt" in field_names
    }


def is_skipped_environment():
    """True where the backfill must not touch content: the test suite, CI, and the sqlite export."""
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    return "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false")


def backfill_alt_text(apps, app_label):
    """Fills the blank alt text fields of every source-locale object in one app, and of its revisions."""
    if is_skipped_environment():
        return

    SpringfieldImage = apps.get_model("cms", "SpringfieldImage")
    Locale = apps.get_model("wagtailcore", "Locale")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    source_locale = Locale.objects.filter(language_code="en-US").first()
    if source_locale is None:
        return

    descriptions_by_image_id = dict(SpringfieldImage.objects.filter(is_decorative=False).exclude(description="").values_list("id", "description"))

    for model in apps.get_models():
        # A page inherits its locale from wagtailcore.Page, so look beyond the model's own fields for it.
        is_translatable = any(field.name == "locale" for field in model._meta.fields)
        if model._meta.app_label != app_label or not is_translatable:
            continue

        alt_fields = alt_fields_for_model(model, SpringfieldImage)
        stream_field_names = [field.name for field in model._meta.local_fields if isinstance(field, StreamField)]
        if not alt_fields and not stream_field_names:
            continue

        source_objects = model.objects.filter(locale=source_locale)
        for obj in source_objects.iterator():
            changed_field_names = list(alt_fields.values())
            for image_field_name, alt_field_name in alt_fields.items():
                image_id = getattr(obj, f"{image_field_name}_id")
                if image_id and not getattr(obj, alt_field_name):
                    setattr(obj, alt_field_name, descriptions_by_image_id.get(image_id, ""))

            for stream_field_name in stream_field_names:
                # An empty stream holds no image, and writing it back would turn a NULL column into [].
                stream_value = getattr(obj, stream_field_name)
                if stream_value:
                    # RawDataView writes straight through to the stream's stored data.
                    backfill_stream_alt_text(stream_value.raw_data, descriptions_by_image_id)
                    changed_field_names.append(stream_field_name)

            obj.save(update_fields=changed_field_names)

        content_type = ContentType.objects.get_for_model(model)
        # object_id is a CharField, and a queryset on the right of __in reaches the database uncoerced.
        source_object_ids = [str(pk) for pk in source_objects.values_list("pk", flat=True)]
        revisions = Revision.objects.filter(content_type=content_type, object_id__in=source_object_ids)
        for revision in revisions.iterator():
            for image_field_name, alt_field_name in alt_fields.items():
                image_id = revision.content.get(image_field_name)
                if image_id and not revision.content.get(alt_field_name):
                    revision.content[alt_field_name] = descriptions_by_image_id.get(image_id, "")

            # A revision holds each StreamField value as a JSON string, not as parsed data.
            for stream_field_name in stream_field_names:
                stream_json = revision.content.get(stream_field_name)
                if stream_json:
                    revision.content[stream_field_name] = json.dumps(backfill_stream_alt_text(json.loads(stream_json), descriptions_by_image_id))

            revision.save(update_fields=["content"])


def backfill_cms_alt_text(apps, schema_editor):
    backfill_alt_text(apps, "cms")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0157_navigationsnippet_logo_alt"),
    ]

    operations = [
        migrations.RunPython(backfill_cms_alt_text, migrations.RunPython.noop),
    ]
