# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def forwards(apps, schema_editor):
    """Copy enable_marketing_attribution=True to marketing_attribution_mode='enabled'."""
    FreeFormPage2026 = apps.get_model("cms", "FreeFormPage2026")
    FreeFormPage2026.objects.filter(enable_marketing_attribution=True).update(
        marketing_attribution_mode="enabled",
    )


def backwards(apps, schema_editor):
    """Reverse: copy marketing_attribution_mode='enabled' back to enable_marketing_attribution=True."""
    FreeFormPage2026 = apps.get_model("cms", "FreeFormPage2026")
    FreeFormPage2026.objects.filter(marketing_attribution_mode="enabled").update(
        enable_marketing_attribution=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0086_freeformpage2026_marketing_attribution_mode_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
