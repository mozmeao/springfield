# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def create_button_label_snippets(apps, schema_editor):
    # Skip in test environments and CI — test fixtures create the snippets they need.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    call_command("create_button_label_snippets", verbosity=1)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0067_buttonlabelsnippet"),
        # Required because save_target() may interact with wagtail_localize_smartling
        # which has a handler that queries LandedTranslationTask / JobTranslation.
        ("wagtail_localize_smartling", "0008_jobtranslation_content_hash"),
    ]

    operations = [
        migrations.RunPython(create_button_label_snippets, reverse_code=migrations.RunPython.noop),
    ]
