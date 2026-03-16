# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.core.management import call_command
from django.db import migrations


def migrate_download_button_labels(apps, schema_editor):
    # Skip in test environments.
    if "pytest" in sys.modules:
        return
    call_command("migrate_download_button_labels")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0057_prefootercta_pretranslated_label"),
    ]

    operations = [
        migrations.RunPython(migrate_download_button_labels, reverse_code=migrations.RunPython.noop),
    ]
