# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# from django.core.management import call_command
from django.db import migrations


def create_main_navigation_snippet(apps, schema_editor):
    # Disabled: this already ran in production.
    # call_command("create_main_navigation_snippet", verbosity=1)
    return


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

    # Forward-only, like the other content migrations: reversing leaves the snippet,
    # its translations and the wagtail_localize records in place, so editor
    # changes are never lost on rollback.
    operations = [
        migrations.RunPython(
            create_main_navigation_snippet,
            migrations.RunPython.noop,
        ),
    ]
