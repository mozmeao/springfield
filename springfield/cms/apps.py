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

        # Replace Wagtail's formfield_for_dbfield with our SVG-sanitizing version
        self._patch_image_form_field()

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

    @staticmethod
    def _patch_image_form_field():
        """
        Replace Wagtail's formfield_for_dbfield with our version that uses
        SanitizingWagtailImageField for SVG sanitization.
        This ensures that all image upload forms use our custom field which
        sanitizes SVG files and rejects them if they contain potentially
        dangerous content like scripts or event handlers.
        This is similar to the _patch_locale_get_active approach - we replace
        a Wagtail function with our enhanced version at app startup.
        """

        from django.utils.text import capfirst
        from django.utils.translation import gettext as _

        import wagtail.images.forms
        from wagtail.admin.forms.collections import CollectionChoiceField
        from wagtail.models import Collection

        from springfield.cms.fields import SanitizingWagtailImageField

        def formfield_for_dbfield(db_field, **kwargs):
            """
            Custom formfield callback for image forms with SVG sanitization.
            This replaces Wagtail's default formfield_for_dbfield to use our
            SanitizingWagtailImageField instead of WagtailImageField.
            """
            if db_field.name == "file":
                return SanitizingWagtailImageField(
                    label=capfirst(db_field.verbose_name),
                    **kwargs,
                )
            elif db_field.name == "collection":
                return CollectionChoiceField(
                    label=_("Collection"),
                    queryset=Collection.objects.all(),
                    empty_label=None,
                    **kwargs,
                )

            # For all other fields, use default
            return db_field.formfield(**kwargs)

        # Replace Wagtail's function with ours
        wagtail.images.forms.formfield_for_dbfield = formfield_for_dbfield
