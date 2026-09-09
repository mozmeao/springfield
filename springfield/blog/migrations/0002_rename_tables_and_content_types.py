# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Renames blog model tables from cms_* to blog_* and updates their
# content types to point at the blog app.

from django.db import migrations

BLOG_MODEL_NAMES = [
    "blogarticleauthor",
    "blogarticlepage",
    "blogauthor",
    "blogindexpage",
    "blogtag",
    "blogtopic",
    "blogtopicpage",
    "taggedblogarticle",
]


def move_content_types_to_blog(apps, schema_editor):
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type_model.objects.filter(app_label="cms", model__in=BLOG_MODEL_NAMES).update(app_label="blog")
    content_type_model.objects.clear_cache()


def move_content_types_to_cms(apps, schema_editor):
    content_type_model = apps.get_model("contenttypes", "ContentType")
    content_type_model.objects.filter(app_label="blog", model__in=BLOG_MODEL_NAMES).update(app_label="cms")
    content_type_model.objects.clear_cache()


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterModelTable(name="blogarticleauthor", table=None),
        migrations.AlterModelTable(name="blogarticlepage", table=None),
        migrations.AlterModelTable(name="blogauthor", table=None),
        migrations.AlterModelTable(name="blogindexpage", table=None),
        migrations.AlterModelTable(name="blogtag", table=None),
        migrations.AlterModelTable(name="blogtopic", table=None),
        migrations.AlterModelTable(name="blogtopicpage", table=None),
        migrations.AlterModelTable(name="taggedblogarticle", table=None),
        migrations.RunPython(move_content_types_to_blog, move_content_types_to_cms),
    ]
