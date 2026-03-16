# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration placeholder. The actual migration was performed via the
# migrate_download_button_labels management command, which has since been
# removed. This migration is kept to preserve the migration chain.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0057_prefootercta_pretranslated_label"),
    ]

    operations = []
