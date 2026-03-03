# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.utils import translation

from wagtail.models import Locale as WagtailLocale

from springfield.base.i18n import normalize_language

logger = logging.getLogger(__name__)


class SpringfieldLocale(WagtailLocale):
    """Custom Locale model that handles Springfield's mixed-case language codes.

    Wagtail's default Locale.get_active() uses Django's translation.get_language()
    which returns lowercase codes (e.g., 'en-gb'). However, our Locale records
    are stored with mixed-case codes (e.g., 'en-GB'). This subclass normalizes
    the language code before lookup to ensure the correct Locale is found.
    """

    class Meta:
        proxy = True

    @classmethod
    def get_active(cls):
        """
        Gets the Locale for the currently activated language code.

        Overrides Wagtail's implementation to normalize the language code
        before looking it up, ensuring mixed-case codes like 'en-GB' are
        matched correctly even when Django returns lowercase 'en-gb'.
        """
        try:
            language_code = translation.get_language()

            # Normalize the language code to match Springfield's mixed-case format
            normalized_code = normalize_language(language_code)

            if normalized_code:
                return cls.objects.get(language_code=normalized_code)
            else:
                # If normalization fails, try the original code
                logger.warning(f"[SpringfieldLocale.get_active] Normalization returned None, using original: {language_code}")
                return cls.objects.get(language_code=language_code)
        except cls.DoesNotExist:
            from django.conf import settings

            # Before falling back to the site default, check whether the active
            # language is an alias locale with a configured fallback (e.g. es-AR
            # → es-MX). This logic is called when the alias Locale DB record
            # does not exist.
            active_code = normalized_code or language_code
            fallback_code = getattr(settings, "FALLBACK_LOCALES", {}).get(active_code)
            if fallback_code:
                try:
                    return cls.objects.get(language_code=fallback_code)
                except cls.DoesNotExist:
                    pass

            logger.warning(f"[SpringfieldLocale.get_active] Locale not found for '{active_code}', falling back to default: {settings.LANGUAGE_CODE}")
            return cls.objects.get(language_code=settings.LANGUAGE_CODE)
