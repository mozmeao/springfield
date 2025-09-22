# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery
from django.http import Http404

from wagtail.models import Locale, Page
from wagtail_localize.models import TranslatableObject, Translation, TranslationSource

from springfield.base.i18n import split_path_and_normalize_language


def get_page_for_request(*, request):
    """For the given HTTPRequest (and its path) find the corresponding Wagtail
    page, if one exists"""

    lang_code, path, _ = split_path_and_normalize_language(request.path)
    try:
        locale = Locale.objects.get(language_code=lang_code)
    except Locale.DoesNotExist:
        locale = None

    try:
        page = Page.find_for_request(request=request, path=path)
        if page and locale and locale != page.locale:
            page = page.get_translation(locale=locale)

    except (ObjectDoesNotExist, Http404):
        page = None

    return page


def get_locales_for_cms_page(page):
    # Patch in a list of CMS-available locales for pages that are
    # translations, not just aliases

    locales_available_via_cms = [page.locale.language_code]
    try:
        _actual_translations = (
            page.get_translations()
            .live()
            .exclude(
                id__in=Subquery(
                    page.aliases.all().values_list("id", flat=True),
                )
            )
        )
        locales_available_via_cms += [x.locale.language_code for x in _actual_translations]
    except ValueError:
        # when there's no draft and no potential for aliases, etc, the above lookup will fail
        pass

    return locales_available_via_cms


def get_cms_locales_for_path(request):
    locales = []

    if page := get_page_for_request(request=request):
        locales = get_locales_for_cms_page(page=page)

    return locales


def calculate_translation_data(page):
    """Calculate translation data for a given page.

    Args:
        page: A Page object

    Returns:
        list: Each object contains 'locale', 'edit_url', 'view_url', and 'percent_translated'
    """
    translations = []
    try:
        # Get the specific page instance to access translatable fields
        specific_page = page.specific

        page_translations = page.get_translations()
        # Get all translations for this page
        for translation in page.get_translations():
            # Use wagtail-localize's Translation model to get proper progress
            translated_segments = 0
            percent_translated = 0
            try:
                # Find the translation source for the original page
                translation_source = TranslationSource.objects.get_for_instance(specific_page)

                # Find the Translation record for this locale
                translation_record = Translation.objects.get(source=translation_source, target_locale=translation.locale)

                # Get the actual translation progress using wagtail-localize logic
                total_segments, translated_segments = translation_record.get_progress()
                percent_translated = int((translated_segments / total_segments * 100)) if total_segments > 0 else 100

            except (TranslationSource.DoesNotExist, Translation.DoesNotExist, TranslatableObject.DoesNotExist):
                # Sometimes, a page will be translated from a translation, so it
                # will not have a translation from the original page. In that case,
                # loop over the translations, and try to find a translation_record
                # for this translation's locale.
                for page_translation in page_translations:
                    try:
                        # Find the translation source for the original page
                        translation_source = TranslationSource.objects.get_for_instance(page_translation)

                        # Find the Translation record for this locale
                        translation_record = Translation.objects.filter(source=translation_source, target_locale=translation.locale).first()

                        if translation_record:
                            # Get the actual translation progress using wagtail-localize logic
                            total_segments, translated_segments = translation_record.get_progress()
                            percent_translated = int((translated_segments / total_segments * 100)) if total_segments > 0 else 100
                            break
                    except (TranslationSource.DoesNotExist, TranslatableObject.DoesNotExist):
                        pass

            translations.append(
                {
                    "locale": translation.locale.language_code,
                    "edit_url": f"/cms-admin/pages/{translation.id}/edit/",
                    "view_url": translation.get_url() if hasattr(translation, "get_url") else "#",
                    "percent_translated": percent_translated,
                }
            )
    except (ValueError, AttributeError):
        # Handle cases where translations might not be available
        pass

    return translations
