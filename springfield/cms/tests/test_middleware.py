# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.test import override_settings

import pytest
from wagtail.models import Page, PageViewRestriction

from springfield.cms.middleware import CMSLocaleFallbackMiddleware
from springfield.cms.tests.factories import LocaleFactory

pytestmark = [pytest.mark.django_db]


def get_200_response(*args, **kwargs):
    return HttpResponse()


def get_404_response(*args, **kwargs):
    return HttpResponseNotFound()


def test_CMSLocaleFallbackMiddleware_200_response_means_middleware_does_not_fire(
    rf,
):
    request = rf.get("/en-US/some/page/path/")
    middleware = CMSLocaleFallbackMiddleware(get_response=get_200_response)
    response = middleware(request)
    assert response.status_code == 200


def test_CMSLocaleFallbackMiddleware__no_accept_language_header(
    rf,
    tiny_localized_site,
):
    request = rf.get("/es-MX/test-page/child-page/")  # page does not exist in es-MX
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/en-US/test-page/child-page/"


def test_CMSLocaleFallbackMiddleware_fallback_to_most_preferred_and_existing_locale(
    rf,
    tiny_localized_site,
):
    # tiny_localized_site supports en-US, fr and pt-BR, but not de
    request = rf.get(
        "/pl/test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="de-DE,pt-BR;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/pt-BR/test-page/child-page/"


def test_CMSLocaleFallbackMiddleware_en_US_selected_because_is_in_accept_language_headers(
    rf,
    tiny_localized_site,
):
    # tiny_localized_site supports en-US, fr and pt-BR, but not de, so en-US should get picked
    request = rf.get(
        "/pl/test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="de-DE,en-US;q=0.9,fr;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/en-US/test-page/child-page/"


def test_CMSLocaleFallbackMiddleware_en_US_is_selected_as_fallback_locale(
    rf,
    tiny_localized_site,
):
    # tiny_localized_site supports en-US, fr and pt-BR, but not de, es-MX or sco
    # so we should fall back to en-US
    assert settings.LANGUAGE_CODE == "en-US"
    request = rf.get(
        "/fr-CA//test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="de-DE,es-MX;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/en-US/test-page/child-page/"


def test_CMSLocaleFallbackMiddleware_url_path_without_trailing_slash(
    rf,
    tiny_localized_site,
):
    # Unlikely that this code path will get triggered in reality, but worth
    # testing just in case

    # tiny_localized_site supports en-US, fr and pt-BR, but not de
    request = rf.get(
        "/sv/test-page/child-page",
        HTTP_ACCEPT_LANGUAGE="de-DE,fr;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/fr/test-page/child-page/"


def test_CMSLocaleFallbackMiddleware_404_when_no_page_exists_in_any_locale(
    rf,
    tiny_localized_site,
):
    request = rf.get(
        "/en-GB/non-existent/page/",
        HTTP_ACCEPT_LANGUAGE="de-DE,fr;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 404


def test_CMSLocaleFallbackMiddleware_404_when_no_page_exists_in_any_locale__more_exacting(
    rf,
    tiny_localized_site,
):
    request = rf.get(
        "/en-GB/child-page/grandchild-page/",  # this doesn't match as a full path, only a sub-path
        HTTP_ACCEPT_LANGUAGE="de-DE,fr;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 404


def test_CMSLocaleFallbackMiddleware_accept_language_header_lang_codes_are_converted(
    rf,
    tiny_localized_site,
):
    # Use /sv/ here specifically because it is not in FALLBACK_LOCALES, so that we can
    # exercise Accept-Language header normalisation.
    request = rf.get(
        "/sv/test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="de-DE,Pt-bR;q=0.8,sco;q=0.6",  # note misformatted pt-BR
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 302
    assert response.headers["Location"] == "/pt-BR/test-page/child-page/"


@pytest.mark.parametrize(
    "bad_url_path",
    [
        "/bad/\x00/path",
        "/bad/path/\x00",
        "/bad/path/\x00/",
        "/bad/\x00/path/\x00",
        "is/download/badfilename\x00.jpg/some-follow-on/path/",
    ],
)
def test_CMSLocaleFallbackMiddleware_404_with_null_byte_in_url(
    rf,
    tiny_localized_site,
    bad_url_path,
):
    # See https://github.com/mozilla/bedrock/issues/16222

    request = rf.get(
        bad_url_path,
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 404  # rather than a 500 when using postgres


def test_CMSLocaleFallbackMiddleware_404_when_no_live_page_exists_only_drafts(
    rf,
    tiny_localized_site,
):
    # See https://github.com/mozilla/bedrock/issues/16202

    # Unpublish all pages with the matching slug, so only drafts exist - and
    # we don't expect to be served any of those, of course
    child_pages = Page.objects.filter(slug="child-page")
    child_pages.unpublish()

    request = rf.get(
        "/pt-BR/test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="Pt-bR,de-DE,fr;q=0.8,sco;q=0.6",
    )
    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)
    assert response.status_code == 404  # rather than a redirect to `child_page`


# ---------------------------------------------------------------------------
# Alias-locale transparent serving
# ---------------------------------------------------------------------------


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_CMSLocaleFallbackMiddleware_alias_locale_serves_fallback_page_transparently(
    rf,
    tiny_localized_site,
):
    """
    Requesting a Page in a locale that doesn't have it, serves content in fallback locale.

    pt-PT is the alias locale; pt-BR is the fallback. tiny_localized_site provides
    pt-BR pages but no pt-PT pages, so the middleware must serve the pt-BR content
    transparently at the pt-PT URL.
    """
    # Verify the test data: pt-BR page exists, pt-PT page does not
    pt_br_page = Page.objects.filter(locale__language_code="pt-BR", slug="child-page").first()
    assert pt_br_page is not None
    assert not Page.objects.filter(locale__language_code="pt-PT", slug="child-page").exists()

    # Create a request for the pt-PT alias URL (same path as for pt_br_page, but
    # a different locale prefix).
    pt_PT_page_url = pt_br_page.url.replace("pt-BR", "pt-PT")
    request = rf.get(pt_PT_page_url)
    request.locale = "pt-PT"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # The user is served the pt_br_page content at the URL for the pt-PR locale.
    assert response.status_code == 200
    assert request.content_locale == "pt-BR"
    assert pt_br_page.title in response.content.decode("utf-8")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_CMSLocaleFallbackMiddleware_promoted_alias_locale_serves_own_page_directly(
    rf,
    tiny_localized_site,
):
    """
    Requesting a Page in an alias locale that has it, serves the Page in the expected locale.

    When an alias locale (es-AR is in FALLBACK_LOCALES) has the Page, then
    requesting it should result in that Page being served.

    The inner handler (Wagtail) returns 200 for the es-AR page, so the middleware passes
    through without setting content_locale. The user receives the es-AR content directly.
    """
    # Create es-AR locale and pages (tiny_localized_site only has en-US, fr, pt-BR).
    es_ar_locale = LocaleFactory(language_code="es-AR")
    en_us_root_page = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    en_us_child_page = Page.objects.get(locale__language_code="en-US", slug="child-page")

    en_us_root_page.copy_for_translation(es_ar_locale)

    es_ar_test_page = en_us_test_page.copy_for_translation(es_ar_locale)
    es_ar_test_page.title = "Página de Prueba AR"
    es_ar_test_page.save()
    es_ar_test_page.save_revision().publish()

    es_ar_child_page = en_us_child_page.copy_for_translation(es_ar_locale)
    es_ar_child_page.title = "Página Hija AR"
    es_ar_child_page.save()
    es_ar_child_page.save_revision().publish()
    es_ar_child_page.refresh_from_db()

    # Verify the test data: es-AR child page exists.
    assert Page.objects.filter(locale__language_code="es-AR", slug="child-page").exists()

    # The inner handler simulates Wagtail serving the es-AR page directly (200).
    def serve_es_ar_page(request):
        return es_ar_child_page.specific.serve(request)

    request = rf.get(es_ar_child_page.url)
    request.locale = "es-AR"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=serve_es_ar_page)
    response = middleware(request)

    # The user is served the es_AR_page content at the es_AR_page_url.
    assert response.status_code == 200
    assert es_ar_child_page.title in response.content.decode("utf-8")
    # The content_locale attribute is only set when we serve content from the fallback locale Page
    assert not hasattr(request, "content_locale")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_CMSLocaleFallbackMiddleware_alias_locale_no_fallback_page(
    rf,
    tiny_localized_site,
):
    """
    Requesting a Page in a locale that doesn't have it, when fallback locale also doesn't have it.
    """
    # Verify the test data: the "child-page" page does not exist in es-AR or es-MX locales.
    assert not Page.objects.filter(locale__language_code="es-AR", slug="child-page").exists()
    assert not Page.objects.filter(locale__language_code="es-MX", slug="child-page").exists()
    # The "child-page" does exist in the pt-BR locale.
    pt_br_page = Page.objects.filter(locale__language_code="pt-BR", slug="child-page").first()

    # Create a request for the es-MX alias URL (same path, different locale prefix).
    es_MX_page_url = pt_br_page.url.replace("pt-BR", "es-MX")
    request = rf.get(es_MX_page_url)
    request.locale = "es-MX"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # Since the page does not exist in the es-MX 'canonical' locale, the user
    # is redirected to the en-US locale.
    assert response.status_code == 302
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="child-page")
    assert response.url == en_us_page.url

    # Create a request for the es-AR alias URL (same path, different locale prefix).
    es_AR_page_url = pt_br_page.url.replace("pt-BR", "es-AR")
    request = rf.get(es_AR_page_url)
    request.locale = "es-AR"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # Since the page does not exist in the es-AR locale or the es-MX locale (the fallback
    # locale for the es-AR locale), the user is redirected to the en-US locale Page.
    assert response.status_code == 302
    assert response.url == en_us_page.url


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_CMSLocaleFallbackMiddleware_alias_locale_no_fallback_page_falls_through_to_redirect(
    rf,
    tiny_localized_site,
):
    """When the alias locale's fallback page is not found, falls through to Accept-Language redirect.

    pt-PT → pt-BR; "non-existent/page/" has no page in any locale, so falls through to 404.
    """
    # Verify the test data: neither pt-BR nor pt-PT has this page
    assert not Page.objects.filter(locale__language_code="pt-BR", slug="non-existent").exists()

    request = rf.get(
        "/pt-PT/non-existent/page/",
        HTTP_ACCEPT_LANGUAGE="pt-BR;q=0.9,fr;q=0.8",
    )
    request.locale = "pt-PT"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # No page at this path in any locale → 404; content_locale was never set
    assert response.status_code == 404
    assert not hasattr(request, "content_locale")


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_CMSLocaleFallbackMiddleware_alias_locale_no_fallback_page_falls_through_to_accept_language_redirect(
    rf,
    tiny_localized_site,
):
    """When the alias locale's fallback page is not found, Accept-Language redirect logic fires.

    pt-PT → pt-BR; the pt-BR page is unpublished so the fallback lookup returns nothing.
    The fr page exists and is in the Accept-Language header, so the middleware redirects there.
    """
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    fr_child = Page.objects.get(locale__language_code="fr", slug="child-page")
    pt_br_child.unpublish()

    request = rf.get(
        "/pt-PT/test-page/child-page/",
        HTTP_ACCEPT_LANGUAGE="fr;q=0.9",
    )
    request.locale = "pt-PT"  # normally set by SpringfieldLangCodeFixupMiddleware

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # Falls through to Accept-Language redirect: fr page exists and is preferred.
    assert response.status_code == 302
    assert response.headers["Location"] == fr_child.url
    # The content_locale attribute is only set when we serve content from the fallback locale Page
    assert not hasattr(request, "content_locale")


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_CMSLocaleFallbackMiddleware_alias_locale_view_restricted_page_redirects_to_canonical(
    rf,
    tiny_localized_site,
):
    """A view-restricted fallback page is never transparently served — redirects to its canonical URL.

    When the fallback page (pt-BR) has a view restriction, the middleware must redirect to
    the canonical pt-BR URL rather than serving it transparently, so that Wagtail's restriction
    enforcement fires at the canonical URL.
    """
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    # Verify no pt-PT page exists (pt-PT is the alias locale)
    assert not Page.objects.filter(locale__language_code="pt-PT", slug="child-page").exists()
    # Add a login restriction to the pt-BR fallback page
    PageViewRestriction.objects.create(page=pt_br_child, restriction_type=PageViewRestriction.LOGIN)

    # Request the pt-PT alias URL (same path, different locale prefix)
    pt_PT_child_page_url = pt_br_child.url.replace("pt-BR", "pt-PT")
    request = rf.get(pt_PT_child_page_url)
    request.locale = "pt-PT"

    middleware = CMSLocaleFallbackMiddleware(get_response=get_404_response)
    response = middleware(request)

    # Redirects to canonical URL so Wagtail's restriction enforcement fires there
    assert response.status_code == 302
    assert response.headers["Location"] == pt_br_child.url
