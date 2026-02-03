# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Fix the page tree after creating feature pages and translations.

When pages are created via migrations (especially through wagtail-localize's
copy_for_translation), the numchild counter can get out of sync. This causes
get_children() to return incorrect results, making translated index pages
appear to have no children.

This migration runs after 0038_create_feature_pages commits, ensuring that
fix_tree() sees all pages in their final state.
"""

from django.db import migrations


def fix_page_tree(apps, schema_editor):
    """Fix the page tree to ensure numchild counts are correct."""
    from wagtail.models import Page

    problems = Page.find_problems()
    bad_numchild = problems[4]  # (bad_alpha, bad_path, orphans, bad_depth, bad_numchild)
    if bad_numchild:
        print(f"\n  Found numchild issues: {bad_numchild}")
        Page.fix_tree(destructive=False)
        print("  Fixed page tree structure")
    else:
        print("\n  Page tree structure OK")


def reverse_noop(apps, schema_editor):
    """No-op reverse migration - tree structure doesn't need to be unfixed."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0038_create_feature_pages"),
    ]

    operations = [
        migrations.RunPython(fix_page_tree, reverse_noop),
    ]
