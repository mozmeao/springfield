# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# from django.core.management import call_command
from django.db import migrations


def migrate_section_pictograms(apps, schema_editor):
    # Disabled: this already ran in production.
    # call_command("migrate_section_pictograms", verbosity=1)
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0160_fill_enterprise_download_resources"),
    ]

    operations = [
        migrations.RunPython(migrate_section_pictograms, reverse_code=migrations.RunPython.noop),
    ]
