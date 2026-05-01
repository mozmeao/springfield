# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config


def create_compare_more_pages(apps, schema_editor):
    # Skip in test environments and CI — test fixtures create the pages they need.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    if "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    call_command("create_compare_more_pages", verbosity=1)


def reverse_migration(apps, schema_editor):
    if "pytest" in sys.modules or config("SQLITE_EXPORT_MODE", parser=bool, default="false"):
        return

    from wagtail.models import Locale, Site

    from springfield.cms.models import ArticleIndexPage

    source_locale = Locale.objects.filter(language_code="en-US").first()
    if not source_locale:
        return
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        return
    root_page = site.root_page
    for slug in ("compare", "more"):
        index = ArticleIndexPage.objects.filter(
            slug=slug,
            locale=source_locale,
            path__startswith=root_page.path,
            depth=root_page.depth + 1,
        ).first()
        if index:
            # Delete each child and its translations explicitly. Translated copies live
            # under their own locale root pages with different paths, so a simple
            # path__startswith filter on the English index would miss them.
            for child in index.get_children():
                child.get_translations().delete()
                child.delete()
            # Delete each translated index page by calling .delete() individually rather
            # than using a queryset .delete(). Wagtail's Page.delete() override updates
            # the numchild counter on the parent (the locale root page). A raw queryset
            # .delete() bypasses that override, leaving locale root pages with stale
            # numchild values and a corrupt page tree.
            for translated_index in index.get_translations():
                translated_index.delete()
            index.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0078_articleindexpage_index_card_type"),
        # Required because save_target() may interact with wagtail_localize_smartling
        # which has a handler that queries LandedTranslationTask / JobTranslation.
        ("wagtail_localize_smartling", "0008_jobtranslation_content_hash"),
        # Required because saving pages triggers modelsearch to INSERT INTO wagtailsearch_indexentry,
        # which must exist before this migration runs on a fresh database.
        ("wagtailsearch", "0005_create_indexentry"),
    ]

    operations = [
        migrations.RunPython(
            create_compare_more_pages,
            reverse_migration,
        ),
    ]
