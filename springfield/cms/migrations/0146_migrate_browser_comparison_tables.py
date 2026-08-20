# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def migrate_browser_comparison_tables(apps, schema_editor):
    # Skip in test environments and CI — test fixtures create the data they need.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    call_command("migrate_browser_comparison_tables", verbosity=1)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0145_migrate_tab_image_to_media"),
    ]

    operations = [
        migrations.RunPython(migrate_browser_comparison_tables, reverse_code=migrations.RunPython.noop),
    ]
