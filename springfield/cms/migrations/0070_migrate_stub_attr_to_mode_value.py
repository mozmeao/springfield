# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations

PAGE_MODELS = [
    "ArticleDetailPage",
    "ArticleIndexPage",
    "ArticleThemePage",
    "DownloadPage",
    "FreeFormPage",
    "FreeFormPage2026",
    "HomePage",
    "SmartWindowExplainerPage",
    "SmartWindowPage",
    "ThanksPage",
    "WhatsNewPage",
    "WhatsNewPage2026",
]


def migrate_stub_attr_fields(apps, schema_editor):
    for model_name in PAGE_MODELS:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            if page.stub_attr_utm_campaign_force:
                page.stub_attr_utm_campaign_mode = "force"
                page.stub_attr_utm_campaign_value = page.stub_attr_utm_campaign_force
            elif page.stub_attr_utm_campaign_override:
                page.stub_attr_utm_campaign_mode = "override"
                page.stub_attr_utm_campaign_value = page.stub_attr_utm_campaign_override
            elif page.stub_attr_utm_campaign:
                page.stub_attr_utm_campaign_mode = "default"
                page.stub_attr_utm_campaign_value = page.stub_attr_utm_campaign
            else:
                continue
            page.save(update_fields=["stub_attr_utm_campaign_mode", "stub_attr_utm_campaign_value"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0069_add_stub_attr_mode_and_value"),
    ]

    operations = [
        migrations.RunPython(migrate_stub_attr_fields, migrations.RunPython.noop),
    ]
