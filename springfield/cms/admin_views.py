# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from wagtail.admin import messages
from wagtail.admin.views.pages.listing import IndexView
from wagtail.admin.views.tags import TAGS_AUTOCOMPLETE_LIMIT
from wagtail.models import Locale, Page
from wagtail_localize.models import Translation
from wagtaildraftsharing.models import WagtaildraftsharingLink

from springfield.cms.draftsharing import create_detached_revision, delete_dead_sharing_revisions
from springfield.cms.forms import ConfirmUpdateSlugForm, UpdateSlugForm
from springfield.cms.models import BlogTag
from springfield.cms.slug_updates import find_sibling_with_slug, page_with_translations, update_page_slug

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


class UpdateSlugView(FormView):
    """Step one of the update-slug action: choose the slug the page should move to."""

    template_name = "wagtailadmin/pages/update_slug.html"
    form_class = UpdateSlugForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.page_to_update = get_object_or_404(Page, id=kwargs["page_id"])
        if not self.page_to_update.permissions_for_user(request.user).can_publish():
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_to_update"] = self.page_to_update
        return context

    def form_valid(self, form):
        confirm_url = reverse("cms_page_update_slug_confirm", args=[self.page_to_update.id])
        return redirect(f"{confirm_url}?{urlencode({'slug': form.cleaned_data['slug']})}")


class UpdateSlugConfirmView(FormView):
    """Step two of the update-slug action: show what the change affects, then do it."""

    template_name = "wagtailadmin/pages/confirm_update_slug.html"
    form_class = ConfirmUpdateSlugForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.page_to_update = get_object_or_404(Page, id=kwargs["page_id"])
        if not self.page_to_update.permissions_for_user(request.user).can_publish():
            raise PermissionDenied

        source = request.POST if request.method == "POST" else request.GET
        self.new_slug = source.get("slug")
        self.conflicting_page = find_sibling_with_slug(self.page_to_update, self.new_slug) if self.new_slug else None

    def dispatch(self, request, *args, **kwargs):
        if not self.new_slug:
            return redirect("cms_page_update_slug", self.page_to_update.id)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["conflicting_page"] = self.conflicting_page
        form_kwargs["initial"] = {**form_kwargs.get("initial", {}), "slug": self.new_slug}
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_to_update"] = self.page_to_update
        context["new_slug"] = self.new_slug
        context["translation_count"] = len(page_with_translations(self.page_to_update)) - 1
        context["conflicting_page"] = self.conflicting_page
        if self.conflicting_page is not None:
            context["conflicting_page_translation_count"] = len(page_with_translations(self.conflicting_page)) - 1
        return context

    def form_valid(self, form):
        try:
            update_page_slug(
                self.page_to_update,
                form.cleaned_data["slug"],
                conflicting_page=self.conflicting_page,
                conflicting_page_slug=form.cleaned_data.get("conflicting_page_slug"),
                publish=form.cleaned_data["publish"],
                user=self.request.user,
            )
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
            return self.form_invalid(form)

        # Re-fetch: the operation changed the slug, and with it the page's URL and
        # possibly its published state, none of which the instance held here reflects.
        updated_page = Page.objects.get(pk=self.page_to_update.pk)
        message_buttons = [messages.button(reverse("wagtailadmin_pages:edit", args=[updated_page.id]), "Edit")]
        if updated_page.live and updated_page.url:
            message_buttons.append(messages.button(updated_page.url, "View live"))

        messages.success(
            self.request,
            f"Page “{updated_page.get_admin_display_title()}” now uses the slug “{form.cleaned_data['slug']}”.",
            buttons=message_buttons,
        )
        return redirect("wagtailadmin_explore", updated_page.get_parent().id)


@require_POST
def create_translation_sharing_link(request, translation_id):
    """Returns a draft-sharing URL for a translated page's unpublished translation.
    Also cleans up revisions for this page's expired links.
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
    if deleted_count:
        logger.info("%d expired link revision(s) deleted for translation page ID=%d", deleted_count, page.pk)

    with transaction.atomic():
        revision = create_detached_revision(translation, page, request.user)
        link = WagtaildraftsharingLink.objects.create_for_revision(revision=revision, user=request.user)

    return JsonResponse({"url": link.url})
