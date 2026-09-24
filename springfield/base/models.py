# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models

from wagtail.models.pages import PAGE_PERMISSION_TYPES


class ConfigValue(models.Model):
    name = models.CharField(max_length=100, db_index=True, unique=True)
    value = models.CharField(max_length=200)

    class Meta:
        app_label = "base"

    def __str__(self):
        return f"{self.name}={self.value}"


def translated_page_codename(page_codename: str) -> str:
    """Map a page permission codename ("publish_page") to its "Translated pages" counterpart."""
    return f"{page_codename.removesuffix('_page')}_translated_page"


def page_codename(translated_codename: str) -> str:
    """Map a "Translated pages" permission codename back to the page permission it grants."""
    return f"{translated_codename.removesuffix('_translated_page')}_page"


class TranslatedPagePermission(models.Model):  # noqa: DJ008
    """
    Holds the "Translated pages" group permissions, one per page permission level.

    A group granted one of these levels gets it on every translation of the pages in its
    page permissions. The model has no table: it exists only to own the permissions.
    """

    class Meta:
        app_label = "base"
        managed = False
        default_permissions = ()
        verbose_name = "Translated pages"
        permissions = [(translated_page_codename(codename), label) for codename, label, _long_label in PAGE_PERMISSION_TYPES]
