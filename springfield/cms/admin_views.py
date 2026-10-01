# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlencode
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from wagtail.admin import messages
from wagtail.admin.views.pages.listing import IndexView
from wagtail.models import Locale, Page
from wagtail_localize.models import Translation, TranslationSource
from wagtaildraftsharing.models import WagtaildraftsharingLink

from springfield.cms.bulk_translations import (
    build_not_syncing_rows,
    build_po_zip,
    build_rows,
    can_edit_translation,
    enabled_translations,
    has_translations,
    has_unsynced_source_changes,
    import_po_files,
    publish_translations,
    restart_translation,
    send_to_smartling,
    stop_translations,
    unpublish_translations,
    zip_filename,
)
from springfield.cms.draftsharing import create_detached_revision, delete_dead_sharing_revisions
from springfield.cms.forms import ConfirmUpdateSlugForm, SelectTranslationsForm, UpdateSlugForm, UploadTranslationsForm
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


def _locale_names(translations):
    return ", ".join(translation.target_locale.get_display_name() for translation in translations)


class ManageTranslationsView(TemplateView):
    """Work on every locale of a page's translations: .po download and upload, publishing,
    syncing and Smartling for syncing locales, and a list of translated pages that aren't syncing."""

    template_name = "wagtailadmin/pages/translations/manage.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.page = get_object_or_404(Page, id=kwargs["page_id"]).specific
        if not request.user.has_perm("wagtail_localize.submit_translation"):
            raise PermissionDenied
        page_permissions = self.page.permissions_for_user(request.user)
        if not page_permissions.can_edit():
            raise PermissionDenied
        self.can_publish = page_permissions.can_publish()

        if not has_translations(self.page):
            raise Http404
        # None when every translation was made outside wagtail-localize.
        self.source = TranslationSource.objects.get_for_instance_or_none(self.page)
        self.translations = enabled_translations(self.source) if self.source else Translation.objects.none()

    @cached_property
    def source_is_behind(self):
        return self.source is not None and has_unsynced_source_changes(self.source)

    def get_context_data(self, select_form=None, upload_form=None, **kwargs):
        context = super().get_context_data(**kwargs)
        select_form = select_form or SelectTranslationsForm(translations=self.translations)
        selected_ids = set(select_form["translations"].value() or []) if select_form.is_bound else None
        context.update(
            page=self.page,
            rows=build_rows(self.source, self.translations, selected_ids) if self.source else [],
            not_syncing_rows=build_not_syncing_rows(self.source, self.page),
            form=select_form,
            upload_form=upload_form or UploadTranslationsForm(),
            can_publish=self.can_publish,
            translate_more_url=self.get_translate_more_url(),
            sync_url=self.get_sync_url(),
        )
        return context

    def get_sync_url(self):
        """wagtail-localize's "Sync translated pages", if the source has changed since the last sync."""
        if not self.source_is_behind:
            return None
        sync_url = reverse("wagtail_localize:update_translations", args=[self.source.id])
        return f"{sync_url}?{urlencode({'next': reverse('cms_page_translations', args=[self.page.id])})}"

    def get_translate_more_url(self):
        """wagtail-localize's "Translate" form, if any locale is left, returning here afterwards."""
        # Same test as wagtail-localize's "Translate this page" button: alias pages can be converted.
        translated_locale_ids = self.page.get_translations(inclusive=True).exclude(alias_of__isnull=False).values_list("locale_id", flat=True)
        if not Locale.objects.exclude(id__in=translated_locale_ids).exists():
            return None
        submit_url = reverse("wagtail_localize:submit_page_translation", args=[self.page.id])
        return f"{submit_url}?{urlencode({'next': reverse('cms_page_translations', args=[self.page.id])})}"

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "upload":
            return self.upload(UploadTranslationsForm(request.POST, request.FILES))
        if action == "restart":
            return self.restart(request.POST.get("translation", ""))
        handlers = {
            "download": self.download,
            "publish": self.publish,
            "unpublish": self.unpublish,
            "stop": self.stop,
            "smartling": self.send_selected_to_smartling,
        }
        if action not in handlers:
            return HttpResponseBadRequest()
        if action in ("publish", "unpublish") and not self.can_publish:
            raise PermissionDenied

        form = SelectTranslationsForm(request.POST, translations=self.translations)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(select_form=form))
        return handlers[action](form.cleaned_data["translations"])

    def download(self, translations):
        editable = [translation for translation in translations if can_edit_translation(translation, self.request.user)]
        not_editable = [translation for translation in translations if translation not in editable]
        if not_editable:
            messages.warning(self.request, f"Left out of the download, as you don't have permission to edit them: {_locale_names(not_editable)}.")
        if not editable:
            return redirect("cms_page_translations", self.page.id)
        response = HttpResponse(build_po_zip(editable), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_filename(self.source)}"'
        return response

    def publish(self, translations):
        published, failed = publish_translations(translations, self.request.user)
        if published:
            messages.success(self.request, f"Published {len(published)} of {len(published) + len(failed)} locales: {_locale_names(published)}.")
        for translation, error in failed:
            messages.error(self.request, f"Could not publish {translation.target_locale.get_display_name()}: {error}")
        return redirect("cms_page_translations", self.page.id)

    def unpublish(self, translations):
        unpublished, not_live, failed = unpublish_translations(translations, self.request.user)
        if unpublished:
            messages.success(self.request, f"Unpublished {len(unpublished)} locales: {_locale_names(unpublished)}.")
        if not_live:
            messages.warning(self.request, f"Already not live, so left alone: {_locale_names(not_live)}.")
        for translation, error in failed:
            messages.error(self.request, f"Could not unpublish {translation.target_locale.get_display_name()}: {error}.")
        return redirect("cms_page_translations", self.page.id)

    def stop(self, translations):
        stopped, failed = stop_translations(translations, self.request.user)
        if stopped:
            messages.success(
                self.request,
                f"Stopped syncing {len(stopped)} locales: {_locale_names(stopped)}. "
                "Their pages are unchanged, and listed under “Not syncing” where you can restart them.",
            )
        for translation, error in failed:
            messages.error(self.request, f"Could not stop syncing {translation.target_locale.get_display_name()}: {error}.")
        return redirect("cms_page_translations", self.page.id)

    def restart(self, translation_id):
        if self.source is None or not translation_id.isdigit():
            return HttpResponseBadRequest()
        translation = self.source.translations.filter(enabled=False, pk=translation_id).select_related("target_locale").first()
        if translation is None:
            return HttpResponseBadRequest()
        locale_name = translation.target_locale.get_display_name()
        if restart_translation(translation, self.request.user):
            messages.success(self.request, f"Restarted syncing {locale_name}. It now opens in the translation editor again.")
        else:
            messages.error(self.request, f"Could not restart syncing {locale_name}: you don't have permission to edit it.")
        return redirect("cms_page_translations", self.page.id)

    def send_selected_to_smartling(self, translations):
        if self.source_is_behind:
            messages.error(
                self.request,
                "Nothing was sent to Smartling: the source page has changes that haven't been synced, "
                "so Smartling would translate out-of-date content. Sync translated pages first, then send.",
            )
            return redirect("cms_page_translations", self.page.id)
        try:
            sent, already_queued, excluded = send_to_smartling(self.source, translations, self.request.user)
        except Exception:
            logger.exception("Sending translation source %s to Smartling failed", self.source.pk)
            messages.error(self.request, "Couldn't create the Smartling job, so nothing was sent. The error has been logged.")
            return redirect("cms_page_translations", self.page.id)

        if sent:
            messages.success(
                self.request,
                f"Sent {len(sent)} locales to Smartling for translation: {_locale_names(sent)}. "
                "The job reaches Smartling on its next sync; translations are imported, not published, when they arrive.",
            )
        if already_queued:
            messages.warning(
                self.request, f"Not sent again, as they're already waiting on a Smartling job for this content: {_locale_names(already_queued)}."
            )
        if excluded:
            messages.warning(self.request, f"Not sent, as these locales are never translated by Smartling: {_locale_names(excluded)}.")
        return redirect("cms_page_translations", self.page.id)

    def upload(self, form):
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(upload_form=form))

        all_translations = self.source.translations.select_related("target_locale") if self.source else []
        result = import_po_files(all_translations, form.cleaned_data["files"], self.request.user)
        for file_name, reason in result.skipped:
            messages.warning(self.request, f"Skipped {file_name}: {reason}.")
        if not result.imported:
            messages.error(self.request, "No translations were imported.")
        else:
            messages.success(
                self.request,
                f"Imported {len(result.imported)} PO files: {_locale_names(translation for _, translation, _ in result.imported)}.",
            )
        for file_name, translation, warnings in result.imported:
            if warnings:
                messages.warning(
                    self.request,
                    f"{file_name} ({translation.target_locale.get_display_name()}): "
                    f"{len(warnings)} entries didn't match this page's current content and were ignored.",
                )
        return redirect("cms_page_translations", self.page.id)
