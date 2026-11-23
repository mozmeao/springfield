# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def import_image_alt_text(apps, schema_editor):
    # Disabled: this already ran in production.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0167_sharefirefoxpage_nav_cta_and_pre_footer"),
        ("wagtailsearch", "0010_add_text_fields"),
    ]

    operations = [
        migrations.RunPython(import_image_alt_text, migrations.RunPython.noop),
    ]
