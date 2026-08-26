# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from wagtail.admin.views.pages.listing import IndexView
from wagtail.admin.views.tags import TAGS_AUTOCOMPLETE_LIMIT
from wagtail.models import Locale, Page
from wagtail_localize.models import Translation
from wagtaildraftsharing.models import WagtaildraftsharingLink

from springfield.cms.draftsharing import create_detached_revision, delete_dead_sharing_revisions, reusable_sharing_link
from springfield.cms.models import BlogTag

logger = logging.getLogger(__name__)


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


@require_POST
def create_translation_sharing_link(request, translation_id):
    """Returns a draft-sharing URL for a translated page's unpublished translation.

    Reuses an existing link when the translation has not changed since it was made,
    and cleans up revisions for this page's expired links.
    """
    translation = get_object_or_404(Translation, id=translation_id)
    try:
        page = translation.get_target_instance()
    except ObjectDoesNotExist:
        raise Http404
    if not isinstance(page, Page):
        raise Http404
    if not page.permissions_for_user(request.user).can_edit():
        raise PermissionDenied

    deleted_count = delete_dead_sharing_revisions(page)
    logger.info("%d expired link revision(s) deleted for translation page ID=%d", deleted_count, page.pk)

    link = reusable_sharing_link(translation, page)
    if link is None:
        revision = create_detached_revision(translation, page, request.user)
        link = WagtaildraftsharingLink.objects.create_for_revision(revision=revision, user=request.user)

    return JsonResponse({"url": link.url})
