# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import migrations


def create_enterprise_redirects(apps, schema_editor):
    """Move the /enterprise/ redirect into Wagtail so editors can remove it from the admin.

    The locale middleware prefixes the path before Wagtail looks up redirects,
    so each locale needs its own entry. Redirects already on these paths, such as
    ones Wagtail created on a slug change, are made temporary too, because a
    site-specific redirect wins over a site-wide one.
    """
    Locale = apps.get_model("wagtailcore", "Locale")
    Redirect = apps.get_model("wagtailredirects", "Redirect")
    for language_code in Locale.objects.values_list("language_code", flat=True):
        old_path = f"/{language_code}/enterprise"
        redirect_link = f"/{language_code}/browsers/enterprise/"
        Redirect.objects.filter(old_path=old_path).update(redirect_page=None, redirect_link=redirect_link, is_permanent=False)
        Redirect.objects.get_or_create(
            old_path=old_path,
            site=None,
            defaults={"redirect_link": redirect_link, "is_permanent": False},
        )


def delete_enterprise_redirects(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    Redirect = apps.get_model("wagtailredirects", "Redirect")
    old_paths = [f"/{language_code}/enterprise" for language_code in Locale.objects.values_list("language_code", flat=True)]
    Redirect.objects.filter(old_path__in=old_paths, site=None).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0161_migrate_section_pictograms"),
        ("wagtailredirects", "0008_add_verbose_name_plural"),
    ]

    operations = [
        migrations.RunPython(create_enterprise_redirects, delete_enterprise_redirects),
    ]
