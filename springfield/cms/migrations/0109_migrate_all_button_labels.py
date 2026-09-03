# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def migrate_labels(apps, schema_editor):
    # Deliberately disabled — this has already run against every database with legacy
    # plain-string labels to convert. Re-running would also break a from-scratch migrate
    # (e.g. demos, the sqlite export): migrate_all_button_labels queries the live model
    # registry, which reflects fields added by migrations later than this one, and a
    # fresh database doesn't have those columns yet at this point in migration history.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0108_migrate_download_button_labels"),
    ]

    operations = [
        migrations.RunPython(migrate_labels, reverse_code=migrations.RunPython.noop),
    ]
