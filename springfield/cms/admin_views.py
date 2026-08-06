# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.http import JsonResponse

from django.http import JsonResponse

from wagtail.admin.views.pages.listing import IndexView
from wagtail.admin.views.tags import TAGS_AUTOCOMPLETE_LIMIT
from wagtail.models import Locale

from springfield.cms.models import BlogTag


class ContentSearchView(IndexView):
    """Wagtail's global page `IndexView` with `.search()` in place of
    `.autocomplete()`. Everything else (filters, columns, pagination,
    permissions) is inherited unchanged."""

    page_title = "Search content"
    index_url_name = "cms_content_search"
    index_results_url_name = "cms_content_search_results"

    def search_queryset(self, queryset):
        # Identical to PageListingMixin.search_queryset (listing.py) except for
        # .search() rather than .autocomplete().
        if self.is_searching:
            queryset = queryset.search(self.search_query, order_by_relevance=(not self.is_explicitly_ordered))
        return queryset


def blog_tag_autocomplete(request):
    """Tag autocomplete scoped to published default-locale BlogTags."""
    term = request.GET.get("term", None)
    if not term:
        return JsonResponse([], safe=False)

    names = (
        BlogTag.objects.filter(name__istartswith=term, locale=Locale.get_default())
        .live()
        .order_by("name")
        .values_list("name", flat=True)[:TAGS_AUTOCOMPLETE_LIMIT]
    )
    return JsonResponse(list(names), safe=False)
