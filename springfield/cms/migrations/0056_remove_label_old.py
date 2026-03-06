# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0055_migrate_download_button_labels"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="prefooterctasnippet",
            name="label_old",
        ),
    ]
