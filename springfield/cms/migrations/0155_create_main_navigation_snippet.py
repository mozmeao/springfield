# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def should_skip():
    """Whether this environment builds its own content and should not run the command."""
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    return "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false")


def create_main_navigation_snippet(apps, schema_editor):
    if should_skip():
        return
    call_command("create_main_navigation_snippet", verbosity=1)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0154_move_blog_models_to_blog_app"),
        # Required because save_target() may interact with wagtail_localize_smartling
        # which has a handler that queries LandedTranslationTask / JobTranslation.
        ("wagtail_localize_smartling", "0008_jobtranslation_content_hash"),
        # Required because saving snippets triggers modelsearch to INSERT INTO
        # wagtailsearch_indexentry, which must exist before this migration runs
        # on a fresh database.
        ("wagtailsearch", "0005_create_indexentry"),
    ]

    operations = [
        migrations.RunPython(
            create_main_navigation_snippet,
            migrations.RunPython.noop,
        ),
    ]
