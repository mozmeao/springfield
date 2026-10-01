# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def fill_enterprise_download_resources(apps, schema_editor):
    """Populate every empty Enterprise Download block."""
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    call_command("migrate_enterprise_download_resources")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0158_contactpage_basket_form_id_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_enterprise_download_resources, migrations.RunPython.noop),
    ]
