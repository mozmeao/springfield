# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# from django.core.management import call_command
from django.db import migrations


def fill_enterprise_download_resources(apps, schema_editor):
    # Disabled: this already ran in production.
    # call_command("migrate_enterprise_download_resources")
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0159_springfieldimage_description_text"),
    ]

    operations = [
        migrations.RunPython(fill_enterprise_download_resources, migrations.RunPython.noop),
    ]
