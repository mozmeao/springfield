# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.db import migrations, models

from springfield.base.config_manager import config

# Concrete pages carrying the per-page floating QR override fields
# (QRCodeFloatingSnippetMixin).
PAGE_MODELS = [
    "FreeFormPage2026",
    "ThanksPage",
    "WhatsNewPage2026",
]


def backfill_open_behavior(apps, schema_editor):
    """Populate `open_behavior` from the original open/closed boolean.

    Existing snippets and pages predate `open_behavior`, so their value is
    blank; carry the old `default_open` / `floating_qr_default_open` intent
    forward. Page overrides left blank stay blank ("inherit the snippet's
    setting").

    Skipped on fresh databases (pytest, CI, and the sqlite DB export replay the
    whole migration chain with no prod data to backfill) — running data
    migrations there has broken the DB export before.
    """
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    Snippet = apps.get_model("cms", "QRCodeFloatingSnippet")
    for snippet in Snippet.objects.all():
        if not snippet.open_behavior:
            snippet.open_behavior = "open" if snippet.default_open else "closed"
            snippet.save(update_fields=["open_behavior"])

    for model_name in PAGE_MODELS:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            if not page.floating_qr_open_behavior and page.floating_qr_default_open is not None:
                page.floating_qr_open_behavior = "open" if page.floating_qr_default_open else "closed"
                page.save(update_fields=["floating_qr_open_behavior"])


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0147_freeformpage2026_floating_qr_open_behavior_and_more"),
    ]

    operations = [
        # Backfill first, while the original booleans still hold the values.
        migrations.RunPython(backfill_open_behavior, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="freeformpage2026",
            name="show_floating_qr_code_snippet",
            field=models.BooleanField(
                default=False,
                help_text="If true, the second-generation floating QR code snippet is displayed on the page.",
                verbose_name="Show Floating QR Code Snippet",
            ),
        ),
        migrations.AlterField(
            model_name="freeformpage2026",
            name="show_qr_code_snippet",
            field=models.BooleanField(default=False, help_text="If true, the first-generation floating QR code snippet is displayed on the page."),
        ),
        migrations.AlterField(
            model_name="qrcodefloatingsnippet",
            name="open_behavior",
            field=models.CharField(
                choices=[("open", "Open on page load"), ("closed", "Closed"), ("delayed", "Closed, then opens automatically")],
                default="open",
                help_text="How the snippet starts.",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="thankspage",
            name="show_floating_qr_code_snippet",
            field=models.BooleanField(
                default=False,
                help_text="If true, the second-generation floating QR code snippet is displayed on the page.",
                verbose_name="Show Floating QR Code Snippet",
            ),
        ),
        migrations.AlterField(
            model_name="thankspage",
            name="show_qr_code_snippet",
            field=models.BooleanField(default=False, help_text="If true, the first-generation floating QR code snippet is displayed on the page."),
        ),
        migrations.AlterField(
            model_name="whatsnewpage2026",
            name="show_floating_qr_code_snippet",
            field=models.BooleanField(
                default=False,
                help_text="If true, the second-generation floating QR code snippet is displayed on the page.",
                verbose_name="Show Floating QR Code Snippet",
            ),
        ),
        migrations.AlterField(
            model_name="whatsnewpage2026",
            name="show_qr_code_snippet",
            field=models.BooleanField(default=False, help_text="If true, the first-generation floating QR code snippet is displayed on the page."),
        ),
    ]
