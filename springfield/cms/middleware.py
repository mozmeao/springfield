# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import logging
from collections import defaultdict
from http import HTTPStatus

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation.trans_real import parse_accept_lang_header

from wagtail.models import Page, Site

from springfield.base.i18n import normalize_language
from springfield.cms.views import _serve_fallback_page

logger = logging.getLogger(__name__)


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
            if not _url_path.endswith("/"):
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
                        return HttpResponseRedirect(page.url)

                # Note: we can make this more efficient by leveraging the cached page tree
                # (once the work to pre-cache the page tree lands)

        return response

    def _has_null_byte(self, request):
        if "\x00" in request.path:
            logger.warning("Null byte found in request path: %s", request.path)
            # This gets called as a 404, so let's just treat it as Not Found
            return True
        return False
