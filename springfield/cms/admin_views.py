# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin content search and blog tag autocomplete.

Wagtail's admin page search — both the standalone search page and the search box
on the page listing — uses `.autocomplete()`, which only reads
`AutocompleteField` content (on our pages, just `title`). This view reuses
Wagtail's global page listing (`IndexView`, with its page-type/owner/date/status
filters) unchanged except for one thing: it searches with `.search()` instead,
so pages match on any indexed `SearchField` — including StreamField body content.

Also here: the tag autocomplete view backing BlogTagField's picker, scoped to
published default-locale tags.
"""

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
    """Tag autocomplete scoped to published default-locale BlogTags.

    Wagtail's own view (`wagtailadmin_tag_model_autocomplete`) returns every row of the tag
    model, so with per-locale tags it mixes languages and offers drafts. Access control comes
    from the register_admin_urls hook, whose URLs Wagtail wraps in require_admin_access.
    """
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
