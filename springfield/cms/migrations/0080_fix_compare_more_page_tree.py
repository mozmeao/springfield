# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Fix the page tree after creating compare/more pages and translations.

When pages are created via migrations (especially through wagtail-localize's
copy_for_translation), the numchild counter can get out of sync. This causes
get_children() to return incorrect results, making translated index pages
appear to have no children.

This migration runs after 0079_create_compare_more_pages commits, ensuring
that fix_tree() sees all pages in their final state.
"""

import sys

from django.db import migrations

from springfield.base.config_manager import config


def fix_page_tree(apps, schema_editor):
    if "pytest" in sys.modules or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    from wagtail.models import Page

    Page.fix_tree(destructive=False)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0079_create_compare_more_pages"),
    ]

    operations = [
        migrations.RunPython(fix_page_tree, reverse_noop),
    ]
