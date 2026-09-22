# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Fills the blog's per-use-case alt text fields from each referenced image's
# description, reusing the cms migration that does the same for its own models.

import importlib

from django.db import migrations

cms_backfill = importlib.import_module("springfield.cms.migrations.0158_backfill_image_alt_text")


def backfill_blog_alt_text(apps, schema_editor):
    cms_backfill.backfill_alt_text(apps, "blog")


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0004_blogarticlepage_image_alt_and_more"),
        ("cms", "0158_backfill_image_alt_text"),
    ]

    operations = [
        # Deliberately not undone: the alt text this writes is indistinguishable
        # from alt text an editor wrote, so reversing it would discard their work too.
        migrations.RunPython(backfill_blog_alt_text, migrations.RunPython.noop),
    ]
