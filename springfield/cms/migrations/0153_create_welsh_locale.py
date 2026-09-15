# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.db import migrations

from springfield.base.config_manager import config

WELSH_LANGUAGE_CODE = "cy"


def _should_skip():
    # Skip in test environments — test fixtures create the locale records they need.
    return (
        "pytest" in sys.modules
        or config("EMPTY_DATABASE_MODE", parser=bool, default="false")
        or config("SQLITE_EXPORT_MODE", parser=bool, default="false")
    )


def create_welsh_locale(apps, schema_editor):
    if _should_skip():
        return

    # Imported inline because the migration needs Wagtail's tree and translation
    # methods, which the historical models from `apps` do not provide.
    from wagtail.models import Locale, Site

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return

    locale, _ = Locale.objects.get_or_create(language_code=WELSH_LANGUAGE_CODE)

    homepage = site.root_page.specific
    if homepage.get_translation_or_none(locale) is not None:
        return

    # Wagtail routes every CMS URL through `site.root_page.localized`, which falls back
    # to the en-US homepage unless a *live* translation exists. Without a live Welsh
    # homepage, /cy/<path>/ resolves against the en-US tree and serves English content
    # at a Welsh URL. An alias mirrors the en-US homepage and its live status; later
    # submitting it for translation clears `alias_of` and makes it a real page.
    # copy_parents=True also creates the per-locale root page at depth 2.
    #
    # Note that publishing the en-US homepage re-publishes its aliases, so this page
    # cannot be withdrawn by unpublishing it — it has to be deleted.
    homepage.copy_for_translation(locale, copy_parents=True, alias=True)


def remove_welsh_locale(apps, schema_editor):
    if _should_skip():
        return

    # See the note in create_welsh_locale about why these are imported inline.
    from wagtail.models import Locale, Page, Site

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return

    locale = Locale.objects.filter(language_code=WELSH_LANGUAGE_CODE).first()
    if not locale:
        return

    # Only remove the homepage while it is still an untouched alias with no children.
    # Once it has been promoted to a real translation (`alias_of` cleared) it holds
    # Welsh content, which a rollback must not destroy.
    welsh_homepage = site.root_page.get_translation_or_none(locale)
    if welsh_homepage is not None and welsh_homepage.alias_of_id is not None and not welsh_homepage.get_children().exists():
        locale_root = welsh_homepage.get_parent()
        welsh_homepage.delete()
        if locale_root is not None and locale_root.depth == 2 and not locale_root.get_children().exists():
            locale_root.delete()

    if not Page.objects.filter(locale=locale).exists():
        locale.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0152_merge_20260910_1400"),
    ]

    operations = [
        migrations.RunPython(create_welsh_locale, remove_welsh_locale),
    ]
