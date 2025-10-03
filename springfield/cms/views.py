# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Min, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import ListView, TemplateView

from wagtail.admin.views.generic.base import BaseListingView
from wagtail.models import Page

from springfield.cms.forms import TranslationsFilterForm
from springfield.cms.utils import calculate_translation_data


class FlareTestView(TemplateView):
    template_name = "cms/flare-test.html"


@method_decorator(staff_member_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class TranslationsListView(ListView, BaseListingView):
    """A view that shows a list of pages with their translations."""

    model = Page
    template_name = "cms/translations_list.html"
    context_object_name = "pages"
    paginate_by = 50

    def get_queryset(self):
        """Get original pages only, excluding root pages and translations of pages."""

        # Get all pages (live and draft), excluding root pages
        all_pages = Page.objects.filter(depth__gt=2).select_related("locale")  # Exclude root page (depth=1) and locale root pages (depth=2)

        # All translations of a page should have the same translation_key, so we
        # get the ids of the original translations by using the minimum ID for
        # each unique translation_key.
        min_ids_by_translation_key = (
            all_pages.order_by("translation_key").values("translation_key").annotate(min_id=Min("id")).values_list("min_id", flat=True)
        )

        # Get the original pages (not any of their translations).
        pages_qs = Page.objects.filter(id__in=min_ids_by_translation_key).order_by("title")

        # Filter pages_qs by any filters (if specified).
        form = TranslationsFilterForm(self.request.GET)
        if not form.is_valid():
            pages_qs = pages_qs.none()
        else:
            # Filter by translation key.
            translation_key = form.cleaned_data.get("translation_key")
            if translation_key:
                pages_qs = pages_qs.filter(translation_key=translation_key)

            # Filter by search query.
            search_query = form.cleaned_data.get("search")
            if search_query:
                pages_qs = pages_qs.filter(Q(title__icontains=search_query) | Q(slug__icontains=search_query))

            # Filter by original language.
            if form.cleaned_data.get("original_language"):
                pages_qs = pages_qs.filter(locale__language_code=form.cleaned_data["original_language"])
            # Filter by whether a page exists in a particular language.
            exists_in_language = form.cleaned_data.get("exists_in_language")
            if exists_in_language:
                if exists_in_language == TranslationsFilterForm.ALL_LANGUAGES:
                    # Special case: filter for pages that exist in ALL configured languages
                    num_languages = len(settings.WAGTAIL_CONTENT_LANGUAGES)

                    # Get translation keys that have exactly num_languages pages (one per language)
                    translation_keys_in_all_languages = (
                        all_pages.order_by("translation_key")
                        .values("translation_key")
                        .annotate(locale_count=Count("locale", distinct=True))
                        .filter(locale_count=num_languages)
                        .values_list("translation_key", flat=True)
                    )
                    pages_qs = pages_qs.filter(translation_key__in=translation_keys_in_all_languages)
                elif exists_in_language == TranslationsFilterForm.CORE_LANGUAGES:
                    # Special case: filter for pages that exist in ALL core languages
                    core_language_codes = [lang_code for lang_code, lang_name in settings.WAGTAIL_CORE_LANGUAGES]

                    # For each core language, get translation keys that have a page in that language
                    # Then find the intersection of all these sets
                    translation_keys_sets = []
                    for core_lang in core_language_codes:
                        keys = set(all_pages.filter(locale__language_code=core_lang).values_list("translation_key", flat=True).distinct())
                        translation_keys_sets.append(keys)

                    # Get intersection of all sets (translation keys that exist in ALL core languages)
                    if translation_keys_sets:
                        translation_keys_in_all_core = set.intersection(*translation_keys_sets)
                        pages_qs = pages_qs.filter(translation_key__in=translation_keys_in_all_core)
                    else:
                        pages_qs = pages_qs.none()
                else:
                    # Get all translation keys that have a translation in the selected language
                    translation_keys_with_locale = (
                        all_pages.filter(locale__language_code=exists_in_language).values_list("translation_key", flat=True).distinct()
                    )
                    pages_qs = pages_qs.filter(translation_key__in=translation_keys_with_locale)

        return pages_qs

    def get_context_data(self, **kwargs):
        """Add translation data to the context."""
        context = super().get_context_data(**kwargs)

        # Add translation data for each page using utility function
        pages_with_translations = []
        for page in context["pages"]:
            translations = calculate_translation_data(page)
            pages_with_translations.append(
                {
                    "page": page,
                    "translations": translations,
                    "edit_url": f"/cms-admin/pages/{page.id}/edit/",
                    "view_url": page.get_url() if hasattr(page, "get_url") else "#",
                }
            )

        context["pages_with_translations"] = pages_with_translations

        # Add filter form to context
        context["filter_form"] = TranslationsFilterForm(self.request.GET)

        return context
