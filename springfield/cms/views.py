# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.decorators.http import etag

from wagtail.models import Locale as WagtailLocale, Site

from springfield.base.views import page_not_found_view
from springfield.cms.models.documents import PDF_MAGIC, StableDocumentURL
from springfield.cms.utils import find_fallback_page_for_locale, mark_locale_fallback_exempt

logger = logging.getLogger(__name__)


def stable_document_not_found(request):
    """Render the 404 page for a ``/documents/`` path, marked never to be cached."""
    response = page_not_found_view(request)
    response["Cache-Control"] = "no-store"
    return response


def serve_stable_document(request, stable_path):
    """
    Stream the PDF of the document assigned to ``/documents/<stable_path>``.

    Unlike Wagtail's own ``/_documents/`` route, this runs no
    ``before_serve_document`` hooks and sends no ``document_served`` signal.

    A refusal returns ``stable_document_not_found`` rather than raising
    ``Http404``, so that the response carries the ``no-store`` header a miss
    needs. Raising would hand the response to ``handler404``, which builds a
    fresh one and would discard any header set here.
    """
    if stable_path != stable_path.lower():
        # Paths are stored lowercased, but Django's slug converter accepts
        # uppercase, so /documents/Subprocessors reaches this view. Lowercasing
        # the lookup instead would publish one document at two URLs. The redirect
        # is not permanent because the pattern matches any slug, including ones
        # no record holds.
        return redirect("stable_document", stable_path=stable_path.lower())

    record = StableDocumentURL.objects.filter(path=stable_path).select_related("document", "document__collection").first()
    if record is None:
        return stable_document_not_found(request)

    document = record.document
    if not document.filename.lower().endswith(".pdf"):
        return stable_document_not_found(request)
    if document.collection.get_view_restrictions().exists():
        return stable_document_not_found(request)

    # The stored file_hash is read rather than get_file_hash() called, because
    # get_file_hash() saves the document when the hash is empty
    # (wagtail/documents/models.py), which would be a database write on an
    # anonymous GET.
    @etag(lambda request: document.file_hash or None)
    def serve_pdf(request):
        try:
            content_length = document.file.size
            document_file = document.file.open("rb")
            leading_bytes = document_file.read(len(PDF_MAGIC))
            # FileResponse measures the body from the handle's current position
            # to EOF, so an unrewound sniff ships a body short by those bytes
            # behind a Content-Length claiming the whole file.
            document_file.seek(0)
        except OSError:
            # Deliberately not turned into a 404: an unreadable file is an
            # outage, and a 404 on this URL reads as a record retired on purpose.
            logger.exception(
                "Cannot read the file of document %s (%s), held by /documents/%s",
                document.pk,
                document.file.name,
                stable_path,
            )
            raise

        if leading_bytes != PDF_MAGIC:
            document_file.close()
            # The last line of defence, for a record written straight through the
            # ORM. The editor-facing gate is the record's own clean().
            return stable_document_not_found(request)

        response = FileResponse(document_file, content_type=document.content_type)
        response["Content-Disposition"] = document.content_disposition
        response["Content-Length"] = content_length
        # CacheMiddleware returns early on a streaming response, so the cache
        # lifetime this whole feature rests on has to be set here.
        response["Cache-Control"] = "max-age=600, public"
        response["Content-Security-Policy"] = "default-src 'none'"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    return serve_pdf(request)


def wagtail_serve(request, path):
    """Serve ``path`` with Wagtail's page-serving view."""
    # Imported inline to break an import cycle: wagtail.views loads the Page model on import,
    # and this module is imported while the cms models are still being registered.
    from wagtail.views import serve

    return serve(request, path)


def _alias_needs_prewagtail_intercept(lang_prefix):
    """
    Return True if the alias locale requires interception before Wagtail handles the request:

        1. if lang_prefix is not a configured alias locale, then we do not intercept the request
        2. Otherwise, pre-Wagtail interception is needed when Wagtail cannot correctly
           serve pages for this alias locale on its own. Either of these:
           a. No Locale DB record exists, OR
           b. The Locale record exists but site.root_page has no live translation in this locale
    Wagtail's default behavior would serve the en-US homepage, which is not
    what we want to happen for alias locales. Instead, we would want to serve
    the fallback locale's Page for the request's URL.
    """
    # 1. If the lang_prefix is not a fallback locale, then we do not need to intercept the request.
    fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})
    if lang_prefix not in fallback_locales:
        return False

    # 2a. We know that the lang_prefix is an alias locale; if the locale deosn't
    # exist, then we intercept the request.
    alias_locale = WagtailLocale.objects.filter(language_code=lang_prefix).first()
    if not alias_locale:
        return True

    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if not site:
        return False

    # 2b. If site.root_page has no live translation in this locale, then we
    # intercept the request.
    alias_root = site.root_page.get_translation_or_none(alias_locale)
    return not alias_root or not alias_root.live


def _serve_fallback_page(request, lang_prefix, sub_path, fallback_locales):
    """
    Find and serve the fallback locale's page for an alias locale URL.

    Returns an HttpResponse if a fallback page is found, or None if the alias
    locale has no configured fallback page (allowing the caller to fall through
    to other checks).

    View-restricted pages are never transparently served; they redirect to the
    canonical URL so Wagtail's restriction enforcement fires there.
    """
    fallback_page = find_fallback_page_for_locale(lang_prefix, sub_path)
    if not fallback_page:
        return None

    if fallback_page.get_view_restrictions():
        return HttpResponseRedirect(fallback_page.url)

    specific_page = fallback_page.specific
    request.content_locale = fallback_locales[lang_prefix]
    # Note: we intentionally do NOT call translation.activate(request.content_locale)
    # here, even though it would make SpringfieldLocale.get_active() resolve
    # to the fallback locale's Wagtail Locale object.
    # The reason: Django's LocalePrefixPattern.language_prefix reads
    # translation.get_language() directly, so activating a different
    # locale (e.g. es-MX while serving /es-AR/) would cause all url()
    # template calls to generate links with the wrong locale prefix (es-MX).
    # Setting request.content_locale carries the fallback locale
    # into the render pipeline without disturbing URL generation.
    return specific_page.serve(request)


def wagtail_serve_with_locale_fallback(request, path=""):
    """
    Wagtail serve wrapper that handles alias-locale fallback.

    This can be used both as the Wagtail catch-all URL pattern (replacing
    ``wagtail.views.serve``) and by ``prefer_cms`` (replacing its direct
    ``wagtail_serve`` call).

    For alias locales that Wagtail cannot serve correctly on its own
    (no Locale DB record, or no live root page translation), this view
    tries to serve the fallback locale's page before deferring to Wagtail.

    For alias locales with a live root page in Wagtail, but no page at the specific
    path (Wagtail would Http404), the fallback locale's page is also tried.

    If no fallback page exists either, raises Http404 so that callers
    (prefer_cms, middleware) can apply their own fallback logic.
    """
    _path = request.path.lstrip("/")
    lang_prefix, _, sub_path = _path.partition("/")
    fallback_locales = getattr(settings, "FALLBACK_LOCALES", {})

    if _alias_needs_prewagtail_intercept(lang_prefix):
        response = _serve_fallback_page(request, lang_prefix, sub_path, fallback_locales)
        if response is not None:
            return response
        # No fallback page and Wagtail can't serve this alias locale
        # correctly — raise 404 so:
        #  - prefer_cms can fall through to its Django view
        #  - CMSLocaleFallbackMiddleware can try the Accept-Language redirect
        raise Http404

    # Try to serve the response with Wagtail, but if Wagtail gives us a 404 for
    # an alias locale, then we try to serve the fallback page.
    # If we can't serve the fallback page, then keep Wagtail's 404, so:
    #    - prefer_cms can fall through to its Django view
    #    - CMSLocaleFallbackMiddleware can try the Accept-Language redirect
    try:
        wagtail_response = wagtail_serve(request, path)
    except Http404:
        if lang_prefix in fallback_locales:
            response = _serve_fallback_page(request, lang_prefix, sub_path, fallback_locales)
            if response is not None:
                return response
        raise
    except AttributeError as error:
        # Without the admin there is no session or auth middleware, so Wagtail's check for
        # private pages fails reading request.session or request.user. Those pages can't
        # be viewed here, and the locale fallback must not redirect back to the same page.
        if settings.WAGTAIL_ENABLE_ADMIN or error.obj is not request or error.name not in ("session", "user"):
            raise
        logger.warning("Private page requested without the admin enabled: %s", request.path)
        mark_locale_fallback_exempt(request)
        raise Http404
    return wagtail_response
