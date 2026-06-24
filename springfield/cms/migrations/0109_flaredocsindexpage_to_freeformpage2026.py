# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import django.db.models.deletion
from django.db import migrations, models


def delete_flare_docs_wagtail_pages(apps, schema_editor):
    Page = apps.get_model("wagtailcore", "Page")
    ContentType = apps.get_model("contenttypes", "ContentType")
    try:
        ct = ContentType.objects.get(app_label="cms", model="flaredocsindexpage")
    except ContentType.DoesNotExist:
        return
    # Snapshot the FlareDocsIndexPage paths before deleting; we then wipe each one along with
    # its entire subtree. A bulk delete on the queryset alone would leave descendant pages
    # (e.g. FreeFormPage2026 block demos) orphaned under the soon-to-be-recreated tree, which
    # later causes path collisions when load_page_fixtures re-adds children.
    flare_docs_paths = list(Page.objects.filter(content_type=ct).values_list("path", flat=True))
    for path in flare_docs_paths:
        Page.objects.filter(path__startswith=path).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0108_migrate_download_button_labels"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(delete_flare_docs_wagtail_pages, migrations.RunPython.noop),
        migrations.DeleteModel(
            name="FlareDocsIndexPage",
        ),
        migrations.CreateModel(
            name="FlareDocsIndexPage",
            fields=[
                (
                    "freeformpage2026_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="cms.freeformpage2026",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("cms.freeformpage2026",),
        ),
    ]
