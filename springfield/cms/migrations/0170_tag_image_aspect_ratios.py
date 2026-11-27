# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations
from django.utils.text import slugify

from springfield.cms.images.ratios import get_exact_ratio_tag


def get_unused_slug(Tag, name):
    # Historical models skip taggit's own unique-slug logic, so pick one by hand.
    base = slugify(name)
    slug, suffix = base, 0
    while Tag.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}_{suffix}"
    return slug


def tag_aspect_ratios(apps, schema_editor):
    # Never call image.save() here: it would queue rendition generation, which
    # has OOM'd the single production worker on oversized images.
    Image = apps.get_model("cms", "SpringfieldImage")
    Tag = apps.get_model("taggit", "Tag")
    TaggedItem = apps.get_model("taggit", "TaggedItem")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(app_label="cms", model="springfieldimage")
    tags_by_name = {}

    for image in Image.objects.only("pk", "width", "height").iterator():
        name = get_exact_ratio_tag(image.width, image.height)
        if name is None:
            continue
        if name not in tags_by_name:
            tag = Tag.objects.filter(name=name).first()
            tags_by_name[name] = tag or Tag.objects.create(name=name, slug=get_unused_slug(Tag, name))
        TaggedItem.objects.get_or_create(tag=tags_by_name[name], content_type=content_type, object_id=image.pk)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0169_freeformpage2026_marketing_attribution_mode_and_more"),
        ("taggit", "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(tag_aspect_ratios, migrations.RunPython.noop),
    ]
