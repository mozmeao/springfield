# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# from django.core.management import call_command
from django.db import migrations


def create_pretranslated_phrases(apps, schema_editor):
    # Disabled: this already ran in production.
    # call_command("create_pretranslated_phrases", verbosity=1)
    return


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0106_pretranslatedphrase"),
        # Required because save_target() may interact with wagtail_localize_smartling
        # which has a handler that queries LandedTranslationTask / JobTranslation.
        ("wagtail_localize_smartling", "0008_jobtranslation_content_hash"),
    ]

    operations = [
        migrations.RunPython(create_pretranslated_phrases, reverse_code=migrations.RunPython.noop),
    ]
