# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
from collections import defaultdict
from http import HTTPStatus

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation.trans_real import parse_accept_lang_header

from wagtail.models import Page, Site
from wagtail_localize.models import TranslationSource
from wagtail_localize_smartling.locks import get_in_flight_locales_for_instance

from springfield.base.i18n import normalize_language
from springfield.cms.utils import LOCALE_FALLBACK_EXEMPT_ATTR, current_request
from springfield.cms.views import _serve_fallback_page

logger = logging.getLogger(__name__)


class CurrentRequestMiddleware:
    """Make the request being served available through utils.current_request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            current_request.reset(token)


class CMSLocaleFallbackMiddleware:
    """Middleware that handles two locale-fallback concerns for 404 responses:

    1. Alias-locale transparent serving: if the requested locale is a
       configured alias (e.g. es-AR → es-MX) and the page exists in the
       fallback locale, serve that content at the alias URL without redirecting.

    2. Accept-Language redirect: if no alias fallback is found, redirect to
       the best available locale based on the user's Accept-Language header,
       falling back to settings.LANGUAGE_CODE.

    Note: for alias locales where Wagtail itself cannot produce a correct
    response (no Locale DB record, or no live root page translation), the
    pre-wagtail-interception is handled by ``wagtail_serve_with_locale_fallback``
    in the URL router — not here.  This middleware only handles 404s that
    come back *after* the URL router has run.
    """

    def __init__(self, get_response):
        # One-time configuration and initialization.
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code == HTTPStatus.NOT_FOUND:
            if self._has_null_byte(request) is True:
                # Don't bother processing URLs with null-byte content - they
                # are fake/vuln scan requests
                return response

            if getattr(request, LOCALE_FALLBACK_EXEMPT_ATTR, False):
                # A page *was* found at this path and deliberately returned 404
                # (e.g. required query params were missing or malformed). The
                # fallback logic below assumes a 404 means no page matched, so
                # it would find that same page again and redirect to it forever.
                return response

            _path = request.path.lstrip("/")
            lang_prefix, _, sub_path = _path.partition("/")
            fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})

            # At this point we have a request that has resulted in a 404,
            # which means it didn't match any Django URLs, and didn't match
            # a CMS page for the current locale+path combination in the URL.

            # Check if the requested locale is a configured alias locale (e.g. es-AR → es-MX).
            # If so, try to find and serve the fallback locale's page inline — no redirect.
            # This means that the URL will be whatever the user requested (for example,
            # /es-AR/somepage), but the page content will come from the fallback locale
            # page (for example, the /es-MX/somepage Page).
            if lang_prefix in fallback_locales:
                fallback_response = _serve_fallback_page(request, lang_prefix, sub_path, fallback_locales)
                if fallback_response is not None:
                    return fallback_response
                # Fallback page not found — fall through to Accept-Language redirect logic.

            # Let's see if there is an alternative version available in a
            # different locale that the user would actually like to see.
            # And failing that, if we have it in the default locale, we can
            # fall back to that (which is consistent with what we do with
            # Fluent-based hard-coded pages).

            # Is the requested path available in other languages, checked in
            # order of user preference?
            accept_lang_header = request.headers.get("Accept-Language")

            # We only want the language codes from parse_accept_lang_header,
            # not their weighting, and we want them to be formatted the way
            # we expect them to be

            if accept_lang_header:
                ranked_locales = [normalize_language(x[0]) for x in parse_accept_lang_header(accept_lang_header)]
            else:
                ranked_locales = []

            # Ensure the default locale is also included, as a last-ditch option.
            # NOTE: remove if controversial in terms of user intent but then
            # we'll have to make sure we pass a locale code into the call to
            # url() in templates, so that cms_only_urls.py returns a useful
            # language code

            if settings.LANGUAGE_CODE not in ranked_locales:
                ranked_locales.append(settings.LANGUAGE_CODE)

            _url_path = sub_path.lstrip("/")
            append_slash_needed = settings.APPEND_SLASH and not request.path.endswith("/")
            if append_slash_needed and _url_path:
                _url_path += "/"

            # Now try to get hold of all the pages that exist in the CMS for the extracted path
            # that are also in a locale that is acceptable to the user or maybe the fallback locale.
            #
            # We build full Wagtail url_paths by looking up the site root page's
            # translations for each candidate locale.  This avoids hard-coding
            # the root slug.

            site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
            if not site:
                return response

            root_page = site.root_page
            # Fetch only (language_code, url_path) for candidate locale roots.
            locale_root_paths = dict(
                Page.objects.filter(
                    translation_key=root_page.translation_key,
                    locale__language_code__in=ranked_locales,
                ).values_list("locale__language_code", "url_path")
            )

            possible_url_path_patterns = []
            for locale_code in ranked_locales:
                root_url_path = locale_root_paths.get(locale_code)
                if root_url_path:
                    possible_url_path_patterns.append(f"{root_url_path}{_url_path}")

            cms_pages_with_viable_locales = Page.objects.live().select_related("locale").filter(url_path__in=possible_url_path_patterns)

            if cms_pages_with_viable_locales:
                # OK, we have some candidate pages with that desired path and at least one
                # viable locale. Let's try to send the user to their most preferred one.

                # Evaluate the queryset just once, then explore the results in memory
                lookup = defaultdict(list)
                for page in cms_pages_with_viable_locales:
                    lookup[page.locale.language_code].append(page)

                for locale_code in ranked_locales:
                    if locale_code in lookup:
                        page_list = lookup[locale_code]
                        # There _should_ only be one matching for this locale, but let's not assume
                        if len(page_list) > 1:
                            logger.warning(f"CMS 404-fallback problem - multiple pages with same path found: {page_list}")
                        page = page_list[0]  # page_list should be a list of 1 item
                        target = page.url
                        if query_string := request.META.get("QUERY_STRING"):
                            target = f"{target}?{query_string}"
                        # Pure trailing-slash canonicalisation within the same locale → 301.
                        # Cross-locale fallbacks remain 302 (Accept-Language dependent).
                        if append_slash_needed and locale_code == lang_prefix:
                            return HttpResponsePermanentRedirect(target)
                        return HttpResponseRedirect(target)

                # Note: we can make this more efficient by leveraging the cached page tree
                # (once the work to pre-cache the page tree lands)

        return response

    def _has_null_byte(self, request):
        if "\x00" in request.path:
            logger.warning("Null byte found in request path: %s", request.path)
            # This gets called as a 404, so let's just treat it as Not Found
            return True
        return False


class PendingTranslationSyncGuardMiddleware:
    """
    Refuse "Sync translated pages" for non-superusers while the page has content
    at Smartling.

    When a translation is sent to Smartling, we wait for the page's text to be
    translated. Syncing the source page to the translations creates a mismatch
    between the text that was sent to Smartling and the text that exists on the
    page(s), so we do not allow syncing until the Smartling translation has
    returned.

    It refuses with a redirect and a message rather than ``PermissionDenied`` because
    Wagtail only converts that into a styled refusal when a *view* raises it. Raised
    here it would reach Django's raw 403, and springfield has no 403 template in
    which to explain itself.
    """

    # A wagtail-localize translation component would be the natural home for this, but
    # a component's ``clean()`` is skipped whenever the component is optional
    view_name = "wagtail_localize:update_translations"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Do nothing for any view that is not self.view_name.
        match = request.resolver_match
        if match is None or match.view_name != self.view_name:
            return None

        # Do nothing for unauthenticated users.
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        source = TranslationSource.objects.filter(pk=view_kwargs.get("translation_source_id")).first()
        if source is None:
            # Stale bookmark or deleted source: let the view raise its own 404.
            return None

        try:
            instance = source.get_source_instance()
        except ObjectDoesNotExist:
            return None

        # Do nothing if this is not a Page.
        if not isinstance(instance, Page):
            return None

        # Do nothing if the instance doesn't look like the wagtail-localize-smartling class.
        can_bypass_lock = getattr(instance, "can_bypass_pending_translation_lock", None)
        if can_bypass_lock is None:
            return None

        # Do nothing if the instance isn't being translated into any locales.
        locales = get_in_flight_locales_for_instance(instance)
        if not locales:
            return None

        # If the user can bypass the lock, give the user a warning message on GETs.
        # After a POST, the view has already redirected onwards and the sync has
        # happened, so the message would be too late.
        if can_bypass_lock(user):
            if request.method == "GET":
                messages.warning(
                    request,
                    _(
                        "This page is being translated in Smartling into "
                        "%(locales)s. Syncing now would create a mismatch "
                        "between the changed text, and the text translated "
                        "in Smartling."
                    )
                    % {"locales": ", ".join(locale.get_display_name() for locale in locales)},
                )
            return None

        messages.error(
            request,
            _(
                "This page is being translated in Smartling. Changing a "
                "field now would create a mismatch between the changed "
                "text, and the text translated in Smartling."
            ),
        )
        return redirect(reverse("wagtailadmin_pages:edit", args=[instance.id]))
