# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management import call_command
from django.db import migrations


def migrate_forward(apps, schema_editor):
    call_command("migrate_icon_choice_values")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0065_migrate_article_detail_page_icon"),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrations.RunPython.noop),
    ]
