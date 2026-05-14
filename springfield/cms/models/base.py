# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.db import models
from django.utils import translation
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from wagtail.admin.panels import FieldPanel
from wagtail.models import Locale, Page as WagtailBasePage
from wagtail_localize.fields import SynchronizedField

from lib import l10n_utils
from springfield.base.i18n import normalize_language
from springfield.cms.utils import compute_cms_page_locales


class PromotedPageMixin(models.Model):
    """Mixin for pages that can receive externally promoted traffic (e.g. Google Ads, Meta)."""

    enable_marketing_attribution = models.BooleanField(
        default=False,
        help_text=(
            "Enable marketing attribution for externally promoted pages. "
            "Adds the 'Share how you discovered Firefox' opt-out checkbox, "
            "consent banner support for EU visitors, and stub attribution "
            "for CPA tracking. Must not be used together with the 'Set as "
            "default browser' checkbox on download buttons."
        ),
    )

    class Meta:
        abstract = True


@method_decorator(never_cache, name="serve_password_required_response")
class AbstractSpringfieldCMSPage(WagtailBasePage):
    """Base page class for all Wagtail pages within Springfield

    Things we do to in particular are:

    * Use our l10n_utils.render() method so that templates can use Fluent string

    * Ensure private pages are not cached:
        By default, Wagtail is unopinionated about cache-control headers,
        so we need to be sure that pages with acecss restrictions are _not_
        cached anywhere in a shared resource (e.g. the CDN)
        Taking our lead from the relevant Wagtail issue
        https://github.com/wagtail/wagtail/issues/5072#issuecomment-949397013, we:
        1) Override the default `serve()` method with cache-control settings
        for pages with view restrictions.
        2) Apply `never_cache` headers to the `wagtail.Page` class's
        `serve_password_required_response` method, via the @method_decorator above
    """

    ftl_files = None

    og_image = models.ForeignKey(
        "cms.SpringfieldImage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Image displayed when this page is shared on social media. Recommended size: 1200×630 pixels (PNG).",
    )

    promote_panels = WagtailBasePage.promote_panels + [
        FieldPanel("og_image"),
    ]

    # Make the `slug` field 'synchronised', so it automatically gets copied over to
    # every localized variant of the page and shouldn't get sent for translation.
    # See https://wagtail-localize.org/stable/how-to/field-configuration/
    override_translatable_fields = [
        SynchronizedField("slug"),
    ]

    class Meta:
        abstract = True

    @classmethod
    def can_create_at(cls, parent):
        """Only allow users to add new child pages that are permitted by configuration."""
        page_model_signature = f"{cls._meta.app_label}.{cls._meta.object_name}"
        if settings.CMS_ALLOWED_PAGE_MODELS == ["__all__"] or page_model_signature in settings.CMS_ALLOWED_PAGE_MODELS:
            return super().can_create_at(parent)
        return False

    def _patch_request_for_springfield(self, request):
        "Add hints that help us integrate CMS pages with core Springfield logic"

        # Quick annotation to help us track the origin of the page
        request.is_cms_page = True

        # Patch in a list of available locales for pages that are translations, not just aliases
        all_locales, content_locales = compute_cms_page_locales(self)
        request._locales_available_via_cms = all_locales
        request._content_locales_via_cms = content_locales
        return request

    def _render_with_fluent_string_support(self, request, *args, **kwargs):
        # Normally, Wagtail's serve() returns a TemplateResponse, so we
        # can swap that for our Fluent-compatible rendering method
        template = self.get_template(request, *args, **kwargs)
        if request.is_preview:
            context = self.get_preview_context(request, *args, **kwargs)
        else:
            context = self.get_context(request, *args, **kwargs)
        # If we need any special Fluent files to accompany CMS content, spec them as the ftl_files attribute (a List)
        # on the page class. If None is specced, we default to what's in settings.FLUENT_DEFAULT_FILES
        return l10n_utils.render(request, template, context, ftl_files=self.ftl_files)

    def _get_dummy_headers(self, original_request=None):
        """Override Wagtail's fake request for previews to include the query string"""
        dummy_values = super()._get_dummy_headers(original_request)
        if original_request and original_request.META.get("QUERY_STRING"):
            dummy_values["QUERY_STRING"] = original_request.META["QUERY_STRING"]
        return dummy_values

    def serve(self, request, *args, **kwargs):
        # Need to replicate behaviour in https://github.com/wagtail/wagtail/blob/stable/5.2.x/wagtail/models/__init__.py#L1928
        request.is_preview = False

        request = self._patch_request_for_springfield(request)

        response = self._render_with_fluent_string_support(request, *args, **kwargs)

        if len(self.get_view_restrictions()):
            add_never_cache_headers(response)
        return response

    def get_preview_context(self, request, mode_name):
        context = super().get_preview_context(request, mode_name)
        hide_preview = request.GET.get("hide_preview", False)
        context["is_preview"] = not hide_preview
        return context

    def serve_preview(self, request, *args, **kwargs):
        request = self._patch_request_for_springfield(request)
        request.is_preview = True
        return self._render_with_fluent_string_support(request, *args, **kwargs)

    @property
    def localized(self):
        """
        Extends Wagtail's localized to handle alias locales in FALLBACK_LOCALES.

        When the active locale is an alias (e.g. pt-PT → pt-BR) and the page has
        no translation in that alias locale, returns the fallback locale's translation
        instead of the source-locale original.
        """
        localized = super().localized

        lang_code = normalize_language(translation.get_language())

        if localized.locale.language_code == lang_code:
            return localized

        fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})
        if lang_code in fallback_locales:
            fallback_code = fallback_locales[lang_code]
            try:
                fallback_locale = Locale.objects.get(language_code=fallback_code)
                if localized.locale_id != fallback_locale.id:
                    fallback_page = self.get_translation_or_none(fallback_locale)
                    if fallback_page:
                        return fallback_page
            except Locale.DoesNotExist:
                pass

        return localized

    def get_active_locale_url(self, request=None):
        """
        Replace the URLs locale with the active locale if the page is a fallback
        so that the user doesn't navigate away from it's preferred language.

        If the active locale is an alias (e.g. pt-PT → pt-BR) and the page is in the
        fallback locale (e.g. pt-BR), return a URL with the alias locale (e.g. pt-PT).
        host/pt-BR/page/ → host/pt-PT/page/
        """
        url = super().get_url(request)

        active_language = normalize_language(translation.get_language())
        fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})

        if active_language in fallback_locales:
            fallback_code = fallback_locales[active_language]
            if self.locale.language_code == fallback_code:
                url = url.replace(f"/{fallback_code}/", f"/{active_language}/", 1)

        return url

    @property
    def og_title(self):
        return self.seo_title or self.title or "Firefox"

    @property
    def og_description(self):
        return self.search_description

    @property
    def noindex(self):
        """By default, don't add the robots meta tag to CMS pages, but allow child classes to override this if needed."""
        return False
