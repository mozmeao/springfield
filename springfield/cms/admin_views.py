# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.text import capfirst
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from wagtail.admin import messages
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.views.pages.listing import IndexView
from wagtail.models import Page
from wagtail_localize.models import Translation
from wagtaildraftsharing.models import WagtaildraftsharingLink

from springfield.base.tasks import defer_task
from springfield.cms.draftsharing import create_detached_revision, delete_dead_sharing_revisions
from springfield.cms.forms import ConfirmUpdateSlugForm, UpdateSlugForm
from springfield.cms.slug_updates import find_sibling_with_slug, page_with_translations, update_page_slug
from springfield.cms.workspaces import WorkspaceLink, get_workspace

logger = logging.getLogger(__name__)


class ContentSearchView(IndexView):
    """Wagtail's global page `IndexView` with `.search()` in place of
    `.autocomplete()`. Everything else (filters, columns, pagination,
    permissions) is inherited unchanged."""

    page_title = "Search content"
    index_url_name = "cms_content_search"
    index_results_url_name = "cms_content_search_results"
    # The generic IndexView defaults list_display to plain `__str__` columns;
    # an empty list keeps the page listing's own columns (title links, parent, status).
    list_display = []

    def search_queryset(self, queryset):
        # Identical to PageListingMixin.search_queryset (listing.py) except for
        # .search() rather than .autocomplete().
        if self.is_searching:
            queryset = queryset.search(self.search_query, order_by_relevance=(not self.is_explicitly_ordered))
        return queryset


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


class RegenerateDocsView(TemplateView):
    """Confirms, then reloads the page fixtures that make up the Flare Docs pages. Unavailable on PROD."""

    template_name = "wagtailadmin/regenerate_docs.html"

    def dispatch(self, request, *args, **kwargs):
        if settings.PROD:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        defer_task(call_command, func_args=["load_page_fixtures"])
        if settings.TASK_QUEUE_AVAILABLE:
            messages.success(request, _("The docs are being regenerated in the background."))
        else:
            messages.success(request, _("The docs have been regenerated."))
        return redirect("cms_regenerate_docs")


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


class WorkspaceView(WagtailAdminTemplateMixin, TemplateView):
    template_name = "wagtailadmin/workspaces/workspace.html"
    recent_edits_limit = 10

    def dispatch(self, request, *args, **kwargs):
        self.workspace = get_workspace(kwargs["slug"])
        self.root = self.workspace.get_root_page() if self.workspace else None
        if self.root is None:
            raise Http404
        if not self.workspace.user_can_access(request.user, self.root):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_page_title(self):
        return self.workspace.label

    def get_header_icon(self):
        return self.workspace.icon

    def get_breadcrumbs_items(self):
        return [*self.breadcrumbs_items, {"url": "", "label": self.workspace.label}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace, root, user = self.workspace, self.root, self.request.user
        content = workspace.content_queryset(root)
        root_permissions = root.permissions_for_user(user)
        add_model = workspace.add_page_model
        explore_url = reverse("wagtailadmin_explore", args=[root.pk])
        context.update(
            root=root,
            add_url=(
                reverse("wagtailadmin_pages:add", args=[add_model._meta.app_label, add_model._meta.model_name, root.pk])
                if add_model and root_permissions.can_add_subpage()
                else None
            ),
            add_label=workspace.add_label or (f"Add {add_model._meta.verbose_name.lower()}" if add_model else ""),
            root_edit_url=reverse("wagtailadmin_pages:edit", args=[root.pk]) if root_permissions.can_edit() else None,
            root_edit_label=workspace.root_edit_label or f"Edit “{root.title}” page",
            browse_url=reverse(workspace.listing_url_name) if workspace.listing_url_name else explore_url,
            browse_label=workspace.listing_label,
            tree_url=explore_url if workspace.listing_url_name else None,
            counts=self.get_counts(content),
            recent=self.get_recent(content),
            locales=[
                {"locale": translated.locale, "browse_url": reverse("wagtailadmin_explore", args=[translated.pk])}
                for translated in workspace.get_root_translations(root)
            ],
            manage_links=self.get_snippet_links() + (workspace.get_extra_links(root, user) if workspace.get_extra_links else []),
        )
        return context

    def get_counts(self, content):
        return [
            {"label": "Live", "value": content.live().count(), "status": "live"},
            {"label": "Live, with unpublished changes", "value": content.live().filter(has_unpublished_changes=True).count(), "status": "changes"},
            {"label": "Draft", "value": content.not_live().count(), "status": "draft"},
            {"label": "Scheduled", "value": content.annotate_approved_schedule().filter(_approved_schedule=True).count(), "status": "scheduled"},
        ]

    def get_recent(self, content):
        pages = (
            content.filter(latest_revision_created_at__isnull=False)
            .select_related("locale", "latest_revision__user")
            .order_by("-latest_revision_created_at")[: self.recent_edits_limit]
            .specific()
        )
        user = self.request.user
        return [
            {
                "page": page,
                "edit_url": reverse("wagtailadmin_pages:edit", args=[page.pk]) if page.permissions_for_user(user).can_edit() else None,
                "edited_by": page.latest_revision.user if page.latest_revision else None,
            }
            for page in pages
        ]

    def get_snippet_links(self):
        links = []
        for model in self.workspace.snippet_models:
            viewset = model.snippet_viewset
            if viewset.permission_policy.user_has_any_permission(self.request.user, {"add", "change", "delete", "view"}):
                links.append(
                    WorkspaceLink(capfirst(model._meta.verbose_name_plural), reverse(viewset.get_url_name("list")), viewset.icon or "snippet")
                )
        return links
