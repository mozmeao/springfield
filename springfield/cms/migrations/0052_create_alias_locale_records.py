# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys

from django.db import migrations


def create_alias_locales(apps, schema_editor):
    # Skip in test environments — test fixtures create the locale records they need.
    if "pytest" in sys.modules:
        return
    Locale = apps.get_model("wagtailcore", "Locale")
    alias_locales = ["es-AR", "es-CL", "pt-PT", "en-GB", "en-CA"]
    for code in alias_locales:
        Locale.objects.get_or_create(language_code=code)


def remove_alias_locales(apps, schema_editor):
    if "pytest" in sys.modules:
        return
    Locale = apps.get_model("wagtailcore", "Locale")
    alias_locales = ["es-AR", "es-CL", "pt-PT", "en-GB", "en-CA"]
    # Only remove if no pages are under these locales (safe reverse migration)
    for code in alias_locales:
        locale = Locale.objects.filter(language_code=code).first()
        if locale and locale.translations.count() == 0:
            locale.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0051_bannersnippet_expire_at_bannersnippet_expired_and_more"),
    ]

    operations = [
        migrations.RunPython(create_alias_locales, remove_alias_locales),
    ]
