# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Create draft CMS scaffolds for four static pages that are moving into the CMS.

Every page these commands write is a DRAFT. All four routes already carry prefer_cms, so a page
only reaches the public when an editor publishes it — this migration never does.

Once these have run in production, comment the call_command lines out, as 0039 and 0088 did:
re-running would create a second copy of each page beside the one editors have been working on.
"""

import os
import sys

from django.core.management import call_command
from django.db import migrations

from springfield.base.config_manager import config

# Each page is its own command, so a page that has already been created in production can be
# commented out on its own line without disturbing the others.
PAGE_COMMANDS = (
    "create_mobile_focus_page",
    "create_landing_get_page",
    "create_complete_pdf_page",
    "create_free_pdf_editor_page",
)

# (slug, model name, source locale) for the reverse. Spelled out rather than read from the registry:
# a reverse has to keep working after the page_content modules it mirrors have moved on. The locale
# matters because a translation shares its source page's slug — filtering on slug alone returns the
# source and all 13 translations, and deleting the source takes the translations with it, so the
# rest of that queryset is already gone by the time the loop reaches it.
CREATED_PAGES = (
    ("focus", "FreeFormPage2026", "en-US", ("mobile",)),
    ("get", "FreeFormPage2026", "en-US", ("landing",)),
    ("complete-pdf", "ArticleDetailPage", "fr", ("features",)),
    ("free-pdf-editor", "ArticleDetailPage", "fr", ("features",)),
)


def should_skip() -> bool:
    # Test fixtures build the pages they need, and the SQLite export has no permission to copy
    # image files around.
    is_ci = os.environ.get("CI", "").lower() in ("1", "true", "yes")
    return "pytest" in sys.modules or is_ci or config("SQLITE_EXPORT_MODE", parser=bool, default="false")


def create_c_pages(apps, schema_editor):
    if should_skip():
        return

    for command_name in PAGE_COMMANDS:
        # Deliberately no --force: a force-rewrite replaces the page body, and by the time anyone
        # re-runs this an editor may already have started finishing the draft.
        call_command(command_name, verbosity=1)


def reverse_migration(apps, schema_editor):
    if should_skip():
        return

    from wagtail.models import Locale, Page, Site

    from springfield.cms import models as cms_models

    def resolve_parent(locale_code, parent_slugs):
        """The same walk the forward migration's commands do, spelled out so this reverse does not
        depend on page_content modules that may have moved on."""
        locale = Locale.objects.filter(language_code=locale_code).first()
        if locale is None:
            return None
        node = Site.objects.get(is_default_site=True).root_page
        if node.locale_id != locale.pk:
            node = Page.objects.filter(translation_key=node.translation_key, locale=locale).first()
        for slug in parent_slugs:
            if node is None:
                return None
            node = node.get_children().filter(slug=slug, locale=locale).first()
        return node

    for slug, model_name, locale_code, parent_slugs in CREATED_PAGES:
        page_model = getattr(cms_models, model_name)
        parent = resolve_parent(locale_code, parent_slugs)
        if parent is None:
            continue
        # live=False is the safety rail. The forward migration never publishes anything and refuses
        # to touch a live page, so a live page with one of these slugs is either one this migration
        # skipped — /mobile/focus/ is already live in production — or a draft an editor has since
        # finished and published. Deleting either would destroy work this migration did not do.
        # Scoped to the parent, not just the slug. Slugs are reused across the tree — /features/focus/
        # is a live page unrelated to the /mobile/focus/ this migration creates — so a slug-only
        # filter would delete someone else's page.
        for page in page_model.objects.child_of(parent).filter(slug=slug, locale__language_code=locale_code, live=False):
            # Delete each translation and each page one at a time rather than through a queryset.
            # Wagtail's Page.delete() override fixes up the parent's numchild counter; a queryset
            # .delete() bypasses the override and leaves a corrupt tree behind.
            for translation in page.get_translations():
                if not translation.live:
                    translation.delete()
            page.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0162_sharefirefoxpage"),
        # Required because save_target() may interact with wagtail_localize_smartling, which has a
        # handler that queries LandedTranslationTask / JobTranslation.
        ("wagtail_localize_smartling", "0008_jobtranslation_content_hash"),
        # Required because saving pages triggers modelsearch to INSERT INTO wagtailsearch_indexentry,
        # which must exist before this migration runs on a fresh database.
        ("wagtailsearch", "0005_create_indexentry"),
    ]

    operations = [
        migrations.RunPython(create_c_pages, reverse_migration),
    ]
