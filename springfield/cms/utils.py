# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery
from django.http import Http404

from wagtail.models import Locale, Page
from wagtail_localize.models import TranslatableObject, Translation, TranslationSource

from springfield.base.i18n import split_path_and_normalize_language

logger = logging.getLogger(__name__)


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


def get_translation_percentages_for_page(source_page, target_locale):
    try:
        # Find the translation source for the original page
        translation_source = TranslationSource.objects.get_for_instance(source_page)

        # Find the Translation record for this locale
        translation_record = Translation.objects.get(source=translation_source, target_locale=target_locale)

        # Get the actual translation progress using wagtail-localize logic
        total_segments, translated_segments = translation_record.get_progress()
        percent_translated = int((translated_segments / total_segments * 100)) if total_segments > 0 else 100
        return percent_translated
    except (TranslationSource.DoesNotExist, Translation.DoesNotExist, TranslatableObject.DoesNotExist):
        return None


def calculate_translation_data(source_page):
    """Calculate translation data for a given page.

    Args:
        page: A Page object

    Returns:
        list: Each object contains 'locale', 'edit_url', 'view_url', and 'percent_translated'
    """
    translations_data = []
    try:
        page_translations = source_page.get_translations()
        # Loop over all translations for this source_page, and get data for each of them.
        for translation in page_translations:
            # First, try to get the translation data based on a translation from the source_page.
            percent_translated = get_translation_percentages_for_page(source_page, translation.locale)
            # If we get no data for a translation from the source_page to this
            # page_translation, then the page_translation must be a translation
            # of a different translation of the source_page. Therefore, we loop
            # over the other page translations to try to find the correct source
            # translation and its data.
            if percent_translated is None:
                for other_page_translation in page_translations:
                    # No need to check for a translation from itself.
                    if other_page_translation == translation:
                        continue

                    percent_translated = get_translation_percentages_for_page(other_page_translation, translation.locale)
                    if percent_translated is not None:
                        break

            translations_data.append(
                {
                    "locale": translation.locale.language_code,
                    "edit_url": f"/cms-admin/pages/{translation.id}/edit/",
                    "view_url": translation.get_url() if hasattr(translation, "get_url") else "#",
                    "percent_translated": percent_translated or 0,
                }
            )
    except (ValueError, AttributeError) as error:
        # If there is an unexpected error, then log it.
        logger.exception(error, stack_info=True)

    return translations_data
