# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Generated by Django 4.2.18 on 2025-02-10 20:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0003_rename_bedrockimage_springfieldimage"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="BedrockRendition",
            new_name="SpringfieldRendition",
        ),
    ]
