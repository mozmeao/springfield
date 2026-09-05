# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config
from springfield.cms.management.commands.create_main_navigation_snippet import SNIPPET_TRANSLATION_KEY


def should_skip():
    """Whether this environment builds its own content and should not run the command."""
    return "pytest" in sys.modules or config("SQLITE_EXPORT_MODE", parser=bool, default="false")


def create_main_navigation_snippet(apps, schema_editor):
    if should_skip():
        return
    call_command("create_main_navigation_snippet", verbosity=1)


def delete_main_navigation_snippet(apps, schema_editor):
    if should_skip():
        return

    # Inline import: migration modules load before the app registry is ready.
    from springfield.cms.models import NavigationSnippet

    # Deletes the English snippet and every translation of it, which share a translation_key.
    NavigationSnippet.objects.filter(translation_key=SNIPPET_TRANSLATION_KEY).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0149_smartwindowpage_enable_marketing_attribution"),
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
            delete_main_navigation_snippet,
        ),
    ]
