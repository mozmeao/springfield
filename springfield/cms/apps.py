# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "springfield.cms"

    def ready(self):
        from springfield.cms import signals  # noqa

        # Replace Wagtail's Locale.get_active() with our implementation
        self._patch_locale_get_active()

    @staticmethod
    def _patch_locale_get_active():
        """
        Replace Wagtail's Locale.get_active() with Springfield's version.

        This ensures that when Wagtail's routing code calls Locale.get_active(),
        it uses our implementation that normalizes language codes from lowercase
        (e.g., 'en-gb') to mixed-case (e.g., 'en-GB').
        """
        from wagtail.models import Locale

        from springfield.cms.models.locale import SpringfieldLocale

        # Replace the classmethod on the base Locale class
        # We need to use the descriptor protocol properly for classmethods
        Locale.get_active = classmethod(SpringfieldLocale.get_active.__func__)
