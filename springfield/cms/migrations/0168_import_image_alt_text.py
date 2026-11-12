# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def import_image_alt_text(apps, schema_editor):
    # Skip where there is no production image library to correct: tests, CI and the sqlite
    # export all replay the migration chain against a database built from scratch.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    call_command("import_image_alt_text", verbosity=1)
    # After the import, so that the tags it sets are the ones left to tidy up.
    call_command("normalize_image_tags", verbosity=1)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0167_sharefirefoxpage_nav_cta_and_pre_footer"),
        # Both commands add every image they change to the search index, so the index table
        # must exist in its current shape before this runs on a fresh database.
        ("wagtailsearch", "0010_add_text_fields"),
    ]

    # Forward-only, like the other content migrations: reversing would leave the images as
    # these commands set them, so there is nothing for a rollback to restore.
    operations = [
        migrations.RunPython(import_image_alt_text, migrations.RunPython.noop),
    ]
