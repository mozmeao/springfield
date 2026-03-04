# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.db import migrations


def create_alias_locales(apps, schema_editor):
    # Skip in test environments — test fixtures create the locale records they need.
    if "pytest" in sys.modules:
        return

    from django.contrib.contenttypes.models import ContentType

    from wagtail.models import Locale, Page, Site

    alias_locales = ["es-AR", "es-CL", "pt-PT", "en-GB", "en-CA"]

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return
    en_us_root = site.root_page
    # The Wagtail tree root (depth 1) is the parent of all locale root pages.
    wagtail_root = en_us_root.get_parent()
    page_content_type = ContentType.objects.get_for_model(Page)

    for code in alias_locales:
        locale, _ = Locale.objects.get_or_create(language_code=code)

        if en_us_root.get_translation_or_none(locale) is not None:
            continue

        # Add an empty root page as a sibling of the default locale root.
        # We bypass copy_for_translation (which requires the parent to already
        # have a translation in the target locale) and add directly under the
        # Wagtail tree root instead.
        # This gives the alias locale its own empty page tree so that Wagtail
        # routes within it and produces a genuine 404 for unknown paths, rather
        # than silently falling back to the en-US tree and returning 200 with
        # wrong-locale content.
        new_root = Page(
            title=en_us_root.title,
            slug=f"home-{code}",
            content_type=page_content_type,
            locale=locale,
            translation_key=en_us_root.translation_key,
            live=True,
            has_unpublished_changes=False,
        )
        wagtail_root.add_child(instance=new_root)


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
        ("cms", "0051_bannersnippet_expire_at_bannersnippet_expired_and_more"),
    ]

    operations = [
        migrations.RunPython(create_alias_locales, remove_alias_locales),
    ]
