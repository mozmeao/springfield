# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.db import migrations


def create_alias_locales(apps, schema_editor):
    # Skip in test environments — test fixtures create the locale records they need.
    if "pytest" in sys.modules:
        return

    from wagtail.models import Locale, Site

    alias_locales = ["es-AR", "es-CL", "pt-PT", "en-GB", "en-CA"]

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return
    en_us_root = site.root_page
    # The Wagtail tree root (depth 1) is the parent of all locale root pages.
    wagtail_root = en_us_root.get_parent()

    for code in alias_locales:
        locale, _ = Locale.objects.get_or_create(language_code=code)

        if en_us_root.get_translation_or_none(locale) is not None:
            continue

        # Add a root page for the alias locale as a sibling of the default locale root.
        # We use page.copy() (rather than copy_for_translation) to avoid parent-translation
        # checks while still copying the correct specific content-type and all its
        # DB table rows.  This is required so that wagtail-localize's copy_for_translation
        # — which resolves parent pages via `parent.specific.get_translation(locale)`,
        # filtering by the specific model's queryset — can find this root when
        # translating any child page to this locale.
        #
        # This gives the alias locale its own empty page tree so that Wagtail
        # routes within it and produces a genuine 404 for unknown paths, rather
        # than silently falling back to the en-US tree and returning 200 with
        # wrong-locale content.
        en_us_root.copy(
            to=wagtail_root,
            update_attrs={
                "locale": locale,
                "slug": f"home-{code}",
            },
            copy_revisions=False,
            keep_live=True,
            reset_translation_key=False,
            log_action=None,
        )


def remove_alias_locales(apps, schema_editor):
    if "pytest" in sys.modules:
        return

    from wagtail.models import Locale, Page, Site

    alias_locales = ["es-AR", "es-CL", "pt-PT", "en-GB", "en-CA"]

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return
    en_us_root = site.root_page

    for code in alias_locales:
        locale = Locale.objects.filter(language_code=code).first()
        if not locale:
            continue

        # Delete the root page translation only if it has no child pages
        # (i.e. the alias locale was never promoted to a full locale with its own content).
        alias_root = en_us_root.get_translation_or_none(locale)
        if alias_root is not None and not alias_root.get_children().exists():
            alias_root.delete()

        # Delete the Locale record if no pages remain under it.
        if not Page.objects.filter(locale=locale).exists():
            locale.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0052_convert_show_to_conditional_display"),
    ]

    operations = [
        migrations.RunPython(create_alias_locales, remove_alias_locales),
    ]
