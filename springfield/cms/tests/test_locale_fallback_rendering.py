# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import html as html_library
import os

from django.conf import settings
from django.template import engines
from django.test import override_settings
from django.urls import path

import pytest
from wagtail.models import Locale, Page, Site

from lib import l10n_utils
from springfield.base.i18n import springfield_i18n_patterns
from springfield.cms.tests.factories import (
    LocaleFactory,
    SimpleRichTextPageFactory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
    WhatsNewPageFactory,
)
from springfield.urls import urlpatterns as springfield_urlpatterns

pytestmark = [pytest.mark.django_db]

TEST_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _hreflang_test_view(request):
    return l10n_utils.render(
        request,
        "test-hreflang.html",
        {"active_locales": ["en-US", "es-MX", "fr", "de"]},
    )


urlpatterns = (
    springfield_i18n_patterns(
        path("test-hreflang/", _hreflang_test_view, name="test-hreflang"),
    )
    + springfield_urlpatterns
)


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_canonical_link_and_index_for_alias_page(client, tiny_localized_site):
    """
    Test canonical and index when serving content from an aliased Page.

    If the user requests the pt-PT page, but it does not exist, the user is served
    content from the pt-BR page at the pt-PT URL (since pt-BR is the fallback
    URL for pt-PT).
    The <link rel="canonical"> href should use the CANONICAL_LANG (pt-BR), not LANG (pt-PT).
    The page should not be indexed.

    When the middleware transparently serves pt-BR content at the pt-PT URL,
    the canonical link must point to the pt-BR URL so search engines know
    where the authoritative content lives.
    """
    # Make sure that the pt-PT locale exists and has an empty home page,
    # so that Wagtail correctly 404s for pt-PT paths instead of falling back
    # to the en-US tree.
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page
    pt_pt_root_page = en_us_root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root_page.live = True
    pt_pt_root_page.save()

    en_us_homepage = en_us_root_page.get_children()[0]
    pt_pt_homepage = en_us_homepage.copy_for_translation(pt_pt_locale)
    pt_pt_homepage.title = "Página de Teste"
    pt_pt_homepage.live = True
    pt_pt_homepage.save()
    rev = pt_pt_homepage.save_revision()
    pt_pt_homepage.publish(rev)

    # Determine the URL for the non-existent page in the pt-PT locale.
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    pt_pt_url = pt_br_child.url.replace("pt-BR", "pt-PT")

    response = client.get(pt_pt_url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/test-page/child-page/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' not in html
    # Since the page content (pt-BR) is different from the URL (pt-PT), the URL
    # should not be indexed.
    assert '<meta name="robots" content="noindex,follow">' in html
    # Note: while response.context["LANG"] and response.context["CANONICAL_LANG"]
    # are correctly used to render the templates, we do not assert them here,
    # because they are incorrectly cached in the tests from the 1st request (the
    # request for a pt-PT page, which returns a 404 response).


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_canonical_link_and_index_for_non_alias_page(client, tiny_localized_site):
    """
    Test canonical and index when serving content from a regular non-alias Page.

    The <link rel="canonical"> href should use the lang from the request.
    The page should be indexed.
    """
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")

    response = client.get(pt_br_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/test-page/child-page/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    # Since the page content (pt-BR) is the same as the URL (pt-BR), the URL
    # should be indexed.
    assert '<meta name="robots" content="noindex,follow">' not in html
    # The response context has both the LANG and the CANONICAL_LANG.
    assert response.context["LANG"] == "pt-BR"
    assert response.context["CANONICAL_LANG"] == "pt-BR"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_canonical_link_and_index_for_alias_without_locale_db_record(client, tiny_localized_site):
    """
    Test canonical and index when the alias locale has no Wagtail Locale DB record.

    When pt-PT has no Locale DB record, we serve the pt-BR content at the pt-PT URL,
    because pt-BR is the fallback locale for pt-PT.
    """
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    pt_pt_url = pt_br_child.url.replace("pt-BR", "pt-PT")

    response = client.get(pt_pt_url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f"<title>{pt_br_child.title}" in html
    page_path = "/test-page/child-page/"
    # Canonical must point to pt-BR (the fallback locale), not pt-PT.
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' not in html
    # Since content (pt-BR) differs from the URL locale (pt-PT), the page should not be indexed.
    assert '<meta name="robots" content="noindex,follow">' in html


@override_settings(FALLBACK_LOCALES={"es-CL": "es-MX"})
def test_canonical_link_and_index_when_alias_and_fallback_have_no_locale_db_record(client, tiny_localized_site):
    """
    Test canonical and index when the alias & fallback locales have no Wagtail Locale DB record.

    When es-CL has no Locale DB record, we try to serve the es-MX content at the es-CL URL,
    because es-MX is the fallback locale for es-CL. But, if the es-MX Locale also
    doesn't exist, we redirect to the settings.LANGUAGE_CODE content.
    """
    assert not Locale.objects.filter(language_code="es-CL").exists()
    assert not Locale.objects.filter(language_code="es-MX").exists()

    en_us_child = Page.objects.get(locale__language_code=settings.LANGUAGE_CODE, slug="child-page")
    es_cl_url = en_us_child.url.replace("en-US", "es-CL")

    response = client.get(es_cl_url)

    # Since the es-CL and the es-MX locales do not exist, the user is redirected
    # to the page in the settings.LANGUAGE_CODE locale.
    assert response.status_code == 302
    assert response.url == en_us_child.url


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_pt_br_hreflang_block_emits_bare_hreflang_pt(client, tiny_localized_site):
    """The pt-BR hreflang block emits hreflang="pt" in addition to hreflang="pt-BR".

    pt-BR is the primary Portuguese locale; it should claim the bare hreflang="pt"
    tag, which search engines treat as the default Portuguese variant.
    """
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f'hreflang="pt" href="{settings.CANONICAL_URL}/pt-BR/' in html
    # hreflang="pt" must appear exactly once (from pt-BR block only)
    count = html.count('hreflang="pt"')
    assert count == 1, f'Expected exactly one hreflang="pt" link, found {count}'
    # That one occurrence must point to pt-BR, not pt-PT
    idx = html.index('hreflang="pt"')
    surrounding = html[idx : idx + 120]
    assert f"{settings.CANONICAL_URL}/pt-BR/" in surrounding
    assert f"{settings.CANONICAL_URL}/pt-PT/" not in surrounding


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_pt_pt_hreflang_block_does_not_emit_bare_hreflang_pt(client, tiny_localized_site):
    """The pt-PT hreflang block only emits hreflang="pt-PT", not hreflang="pt".

    pt-PT is an alias locale; the bare hreflang="pt" belongs to pt-BR exclusively.
    Emitting hreflang="pt" for pt-PT would conflict with the pt-BR entry.
    """
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f'hreflang="pt" href="{settings.CANONICAL_URL}/pt-PT/' not in html


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX", "es-CL": "es-MX"})
def test_alias_locales_excluded_from_hreflang_on_all_pages(client, tiny_localized_site):
    """
    Alias locales without their own content must not appear in hreflang alternates.

    When es-AR and es-CL both fall back to es-MX with no content of their own,
    neither should appear in hreflang alternates — regardless of which page is
    being viewed (canonical, fallback target, or alias).
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page
    en_us_test_page = en_us_root_page.get_children()[0]  # slug "test-page"
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    # Create es-MX locale with a full translation tree including child-page.
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_mx_test_page = en_us_test_page.copy_for_translation(es_mx_locale, copy_parents=True)
    es_mx_test_page.save_revision().publish()

    es_mx_child = en_us_child.copy_for_translation(es_mx_locale)
    es_mx_child.save_revision().publish()

    # Create es-AR locale with a root page and test-page but NO child-page —
    # it will fall back to es-MX via the middleware, matching the real-world scenario.
    es_ar_locale = LocaleFactory(language_code="es-AR")
    es_ar_root_page = en_us_root_page.copy_for_translation(es_ar_locale)
    es_ar_root_page.live = True
    es_ar_root_page.save()

    es_ar_test_page = en_us_test_page.copy_for_translation(es_ar_locale)
    es_ar_test_page.live = True
    es_ar_test_page.save()
    es_ar_test_page.save_revision().publish()

    page_path = "/test-page/child-page/"

    # --- 1. Request the en-US page (a page with its own content) ---
    response = client.get(en_us_child.url)
    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Canonical should be self-referencing (en-US).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # es-MX has actual content — must appear in alternates.
    assert f'hreflang="es-MX" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    # es-AR and es-CL have no content — must NOT appear in alternates.
    assert f'hreflang="es-AR" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    assert f'hreflang="es-CL" href="{settings.CANONICAL_URL}/es-CL{page_path}"' not in html

    # --- 2. Request the es-MX page (the fallback target, has its own content) ---
    es_mx_child.refresh_from_db()
    response = client.get(es_mx_child.url)
    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Canonical should be self-referencing (es-MX).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # es-MX itself should appear in alternates.
    assert f'hreflang="es-MX" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    # es-AR and es-CL have no content — must NOT appear in alternates.
    assert f'hreflang="es-AR" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    assert f'hreflang="es-CL" href="{settings.CANONICAL_URL}/es-CL{page_path}"' not in html

    # --- 3. Request the es-AR page (alias locale, served via fallback middleware) ---
    es_ar_url = es_mx_child.url.replace("es-MX", "es-AR")
    response = client.get(es_ar_url)
    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Canonical must point to es-MX (the fallback locale), not es-AR.
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    # The alias page should be noindexed.
    assert '<meta name="robots" content="noindex,follow">' in html
    # es-MX has actual content — must appear in alternates.
    assert f'hreflang="es-MX" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    # es-AR and es-CL have no content — must NOT appear in alternates.
    assert f'hreflang="es-AR" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    assert f'hreflang="es-CL" href="{settings.CANONICAL_URL}/es-CL{page_path}"' not in html


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_promoted_alias_locale_included_in_hreflang_alternates(client, tiny_localized_site):
    """
    An alias locale that has its own content SHOULD appear in hreflang alternates.

    When pt-PT has been "promoted" (has its own translated page), it is a real
    translation — not a fallback — and should appear in the alternates.
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page
    en_us_test_page = en_us_root_page.get_children()[0]  # slug "test-page"
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    # Create a real pt-PT translation tree (not an alias)
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    pt_pt_root_page = en_us_root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root_page.live = True
    pt_pt_root_page.save()

    pt_pt_test_page = en_us_test_page.copy_for_translation(pt_pt_locale)
    pt_pt_test_page.live = True
    pt_pt_test_page.save()
    pt_pt_test_page.save_revision().publish()

    pt_pt_child = en_us_child.copy_for_translation(pt_pt_locale)
    pt_pt_child.live = True
    pt_pt_child.save()
    pt_pt_child.save_revision().publish()

    # --- 1. Request the en-US page (a page with its own content) ---
    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # Both pt-BR and pt-PT have their own content — both should appear.
    assert f'hreflang="pt-BR" href="{settings.CANONICAL_URL}/pt-BR/' in html
    assert f'hreflang="pt-PT" href="{settings.CANONICAL_URL}/pt-PT/' in html

    # --- 2. Request the pt-BR page (the fallback target, has its own content) ---
    pt_br_child = Page.objects.get(locale__language_code="pt-BR", slug="child-page")
    response = client.get(pt_br_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/test-page/child-page/"
    # Canonical should be self-referencing (pt-BR).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # Both pt-BR and pt-PT have their own content — both should appear.
    assert f'hreflang="pt-BR" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert f'hreflang="pt-PT" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' in html

    # --- 3. Request the pt-PT page (promoted alias locale, has its own content) ---
    pt_pt_child.refresh_from_db()
    response = client.get(pt_pt_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # Canonical should be self-referencing (pt-PT has its own content).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # Both pt-BR and pt-PT have their own content — both should appear.
    assert f'hreflang="pt-BR" href="{settings.CANONICAL_URL}/pt-BR{page_path}"' in html
    assert f'hreflang="pt-PT" href="{settings.CANONICAL_URL}/pt-PT{page_path}"' in html


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_unsupported_locale_not_in_hreflang_alternates(client, tiny_localized_site):
    """
    A locale with no content and no fallback configured must not appear in alternates.

    When ja has no page for child-page and is not listed in FALLBACK_LOCALES,
    it should not appear in hreflang alternates on any page. Requesting the ja
    URL should redirect since there is no content or fallback for it.
    """
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    # --- 1. Request the en-US page — ja must not appear in alternates ---
    response = client.get(en_us_child.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert 'hreflang="ja"' not in html

    # --- 2. Request the ja URL — should redirect (no content, no fallback) ---
    ja_url = en_us_child.url.replace("en-US", "ja")
    response = client.get(ja_url)
    assert response.status_code == 302
    assert response.url == en_us_child.url


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_homepage_fallback_for_alias_locale(client):
    """
    If the homepage at an alias locale URL (e.g. /pt-PT/) is not live, GETting the
    /pt-PT/ URL should serve fallback locale content (pt-BR) with a pt-BR canonical link.

    When the pt-PT locale has a Locale DB record and a non-live root page
    (as created by the alias locale migration), requesting /pt-PT/ should
    serve the pt-BR homepage content via the fallback middleware.
    """
    en_us_locale = Locale.objects.get(language_code="en-US")
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    pt_pt_locale = LocaleFactory(language_code="pt-PT")

    site = Site.objects.get(is_default_site=True)
    wagtail_root_page = site.root_page  # plain Page at depth 2

    # Create a SimpleRichTextPage as the homepage (depth 3) for en-US,
    # so that the CMS template (with canonical/hreflang) is used.
    en_us_homepage = SimpleRichTextPageFactory(
        title="English Home",
        slug="home-page",
        parent=wagtail_root_page,
        locale=en_us_locale,
    )
    en_us_homepage.save_revision().publish()

    # Point the site root to the homepage.
    site.root_page = en_us_homepage
    site.save()

    # Create a pt-BR translation of the homepage.
    wagtail_root_page.copy_for_translation(pt_br_locale)
    pt_br_homepage = en_us_homepage.copy_for_translation(pt_br_locale)
    pt_br_homepage.title = "Página Inicial pt-BR"
    pt_br_homepage.save()
    pt_br_homepage.save_revision().publish()

    # Create pt-PT locale with a non-live root page (mimics migration 0053).
    pt_pt_root = wagtail_root_page.copy_for_translation(pt_pt_locale)
    pt_pt_root.live = False
    pt_pt_root.save()

    response = client.get("/pt-PT/")
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # The response should serve pt-BR content, not the default Wagtail page.
    assert "Página Inicial pt-BR" in html
    # Canonical must point to pt-BR (the fallback locale), not pt-PT.
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-BR/"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/pt-PT/"' not in html
    # Since content (pt-BR) differs from the URL locale (pt-PT), should be noindexed.
    assert '<meta name="robots" content="noindex,follow">' in html


@pytest.fixture()
def _add_test_templates_dir():
    """Temporarily add the test templates directory to the Jinja2 FileSystemLoader.

    Modifies the loader's searchpath directly instead of resetting
    engines._engines, which would invalidate module-level references
    to the Jinja2 environment used by other tests' mock patches.
    """
    jinja2_loader = engines["jinja2"].env.loader
    jinja2_loader.searchpath.insert(0, TEST_TEMPLATES_DIR)
    try:
        yield
    finally:
        jinja2_loader.searchpath.remove(TEST_TEMPLATES_DIR)


@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("_add_test_templates_dir")
@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX", "es-CL": "es-MX"})
def test_non_cms_page_hreflang_alternates(client):
    """Non-CMS (Django/Fluent) pages should render correct hreflang alternates.

    Uses a test-only view with controlled active_locales to verify that hreflang
    alternate links are rendered correctly for non-Wagtail pages. Alias locales
    that are not in active_locales but whose fallback is present should not appear
    in alternates.
    """
    page_path = "/test-hreflang/"

    # --- 1. Request the en-US page ---
    response = client.get(f"/en-US{page_path}")
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # Canonical should be self-referencing (en-US).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # en-US should emit both hreflang="en" and hreflang="en-US".
    assert f'hreflang="en" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html
    assert f'hreflang="en-US" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html
    # Locales in active_locales should appear.
    assert f'hreflang="fr" href="{settings.CANONICAL_URL}/fr{page_path}"' in html
    assert f'hreflang="de" href="{settings.CANONICAL_URL}/de{page_path}"' in html
    assert f'hreflang="es-MX" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    # es-AR and es-CL are alias locales not in active_locales — should NOT appear.
    assert 'hreflang="es-AR"' not in html
    assert 'hreflang="es-CL"' not in html
    # ja is not in active_locales and has no fallback — should not appear.
    assert 'hreflang="ja"' not in html

    # --- 2. Request the es-MX page (fallback target, has its own content) ---
    response = client.get(f"/es-MX{page_path}")
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # Canonical should be self-referencing (es-MX).
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # es-AR and es-CL should NOT appear.
    assert 'hreflang="es-AR"' not in html
    assert 'hreflang="es-CL"' not in html

    # --- 3. Request the es-AR page (alias locale, served via fallback) ---
    response = client.get(f"/es-AR{page_path}")
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    # Canonical must point to es-MX (the fallback locale), not es-AR.
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    # The alias page should be noindexed.
    assert '<meta name="robots" content="noindex,follow">' in html
    # es-AR and es-CL should NOT appear in alternates.
    assert 'hreflang="es-AR"' not in html
    assert 'hreflang="es-CL"' not in html


# ---------------------------------------------------------------------------
# Alias-locale fallback serving — alias root page state
# ---------------------------------------------------------------------------


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_alias_locale_with_live_root_page_serves_fallback_transparently(client):
    """
    The full stack serves the fallback locale's page when the alias locale has a live root page.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()
    es_mx_page = SimpleRichTextPageFactory(title="ES-MX Test Page", slug="test-page", locale=es_mx_locale, parent=es_mx_root)

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()
    es_ar_root.refresh_from_db()
    assert es_ar_root.live is True
    assert not Page.objects.filter(locale=es_ar_locale, slug="test-page").exists()

    es_mx_page.refresh_from_db()
    response = client.get(es_mx_page.url.replace("es-MX", "es-AR"))

    assert response.status_code == 200
    assert es_mx_page.title in response.content.decode("utf-8")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_alias_locale_with_draft_root_page_serves_fallback_transparently(client):
    """
    The full stack serves the fallback locale's page when the alias locale has a draft root page.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()
    es_mx_page = SimpleRichTextPageFactory(title="ES-MX Test Page", slug="test-page", locale=es_mx_locale, parent=es_mx_root)

    # copy_for_translation creates a draft by default — do not publish.
    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.refresh_from_db()
    assert es_ar_root.live is False
    assert not Page.objects.filter(locale=es_ar_locale, slug="test-page").exists()

    es_mx_page.refresh_from_db()
    response = client.get(es_mx_page.url.replace("es-MX", "es-AR"))

    assert response.status_code == 200
    assert es_mx_page.title in response.content.decode("utf-8")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_alias_locale_with_no_root_page_serves_fallback_transparently(client):
    """
    The full stack serves the fallback locale's page when the alias locale has no root page.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()
    es_mx_page = SimpleRichTextPageFactory(title="ES-MX Test Page", slug="test-page", locale=es_mx_locale, parent=es_mx_root)

    # No root page created for es-AR.
    assert not Page.objects.filter(translation_key=en_us_root.translation_key, locale=es_ar_locale).exists()
    assert not Page.objects.filter(locale=es_ar_locale, slug="test-page").exists()

    es_mx_page.refresh_from_db()
    response = client.get(es_mx_page.url.replace("es-MX", "es-AR"))

    assert response.status_code == 200
    assert es_mx_page.title in response.content.decode("utf-8")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_promoted_alias_locale_serves_own_page_directly(client):
    """
    When an alias locale has its own content, it is served directly without fallback.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()
    es_mx_page = SimpleRichTextPageFactory(title="ES-MX Test Page", slug="test-page", locale=es_mx_locale, parent=es_mx_root)

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()
    es_ar_root.refresh_from_db()
    assert es_ar_root.live is True

    es_ar_page = es_mx_page.copy_for_translation(es_ar_locale)
    es_ar_page.title = "ES-AR Test Page"
    es_ar_page.save_revision().publish()
    es_ar_page.refresh_from_db()

    response = client.get(es_ar_page.url)

    assert response.status_code == 200
    assert es_ar_page.title in response.content.decode("utf-8")
    assert es_mx_page.title not in response.content.decode("utf-8")


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_alias_to_nonexistent_cms_fallback_page_redirects(client):
    """
    When a CMS page does not exist in the fallback locale (es-MX), an
    alias-locale (es-AR) request is redirected to the best available locale.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()

    # The page exists only in en-US; es-MX has no equivalent.
    SimpleRichTextPageFactory(parent=en_us_root, slug="features-page", title="Features")

    response = client.get("/es-AR/features-page/")
    assert response.status_code == 302
    # No canonical-link logic applies since no page is served
    assert "/en-US/features-page/" in response.url

    response = client.get("/es-AR/features-page/", follow=True)
    assert response.status_code == 200
    # The indexable en-US page is served
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="features-page")
    html = response.content.decode("utf-8")
    assert f"<title>{en_us_page.title}" in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/en-US/features-page/"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR/features-page/"' not in html
    assert '<meta name="robots" content="noindex,follow">' not in html


def test_noindex_page_has_canonical(client):
    """
    A page with noindex=True using base-flare26.html served directly should emit
    both a self-referencing canonical link and the noindex meta tag.
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    en_us_wnp_index = WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew", live=True)
    en_us_wnp2026 = WhatsNewPage2026Factory(parent=en_us_wnp_index, slug="149", version="149")
    en_us_wnp2026.refresh_from_db()

    assert en_us_wnp2026.noindex is True

    response = client.get(en_us_wnp2026.url)
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    page_path = "/whatsnew/149/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html
    assert '<meta name="robots" content="noindex,follow">' in html


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_noindex_page_alias_request_gets_canonical(client):
    """A page with noindex=True on base-flare26.html served via an alias locale
    should emit a canonical link to the fallback locale alongside the noindex meta tag.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()

    WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew", live=True)
    WhatsNewPage2026Factory(parent=en_us_root.get_children().get(slug="whatsnew"), slug="149", version="149")

    es_mx_wnp_index = WhatsNewIndexPageFactory(parent=es_mx_root, slug="whatsnew", live=True, locale=es_mx_locale)
    es_mx_wnp2026 = WhatsNewPage2026Factory(parent=es_mx_wnp_index, slug="149", version="149", locale=es_mx_locale)
    assert es_mx_wnp2026.noindex is True

    page_path = "/whatsnew/149/"
    response = client.get(f"/es-AR{page_path}")
    assert response.status_code == 200

    html_content = html_library.unescape(response.content.decode("utf-8"))
    assert f"<title>{es_mx_wnp2026.title}" in html_content
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html_content
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html_content
    assert '<meta name="robots" content="noindex,follow">' in html_content


def test_whatsnew_page_direct_request_has_canonical(client):
    """
    A WhatsNewPage (which has noindex=True) served directly should emit
    both a self-referencing canonical link and the noindex meta tag.
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    en_us_wnp_index = WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew", live=True)
    en_us_wnp = WhatsNewPageFactory(parent=en_us_wnp_index, slug="149", version="149")
    en_us_wnp.refresh_from_db()
    assert en_us_wnp.noindex is True

    response = client.get(en_us_wnp.url)
    assert response.status_code == 200

    html_content = html_library.unescape(response.content.decode("utf-8"))
    assert f"<title>{en_us_wnp.title}" in html_content
    page_path = "/whatsnew/149/"
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/en-US{page_path}"' in html_content
    assert '<meta name="robots" content="noindex,follow">' in html_content


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_whatsnew_page_alias_request_gets_canonical(client):
    """
    A WhatsNewPage (noindex=True, base-flare.html) served via an alias locale
    should emit a canonical link pointing to the fallback locale URL.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()

    WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew", live=True)
    WhatsNewPageFactory(parent=en_us_root.get_children().get(slug="whatsnew"), slug="149", version="149")

    es_mx_wnp_index = WhatsNewIndexPageFactory(parent=es_mx_root, slug="whatsnew", live=True, locale=es_mx_locale)
    es_mx_wnp = WhatsNewPageFactory(parent=es_mx_wnp_index, slug="149", version="149", locale=es_mx_locale)
    assert es_mx_wnp.noindex is True

    page_path = "/whatsnew/149/"
    response = client.get(f"/es-AR{page_path}")
    assert response.status_code == 200

    html = response.content.decode("utf-8")
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-MX{page_path}"' in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR{page_path}"' not in html
    assert '<meta name="robots" content="noindex,follow">' in html


@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_alias_to_nonexistent_whatsnew_fallback_page_uses_django_view(client):
    """
    When a WhatsNewPage does not exist in the fallback locale (es-MX), an
    alias-locale (es-AR) request is handled by the Django WhatsnewView (not the CMS).

    Unlike CMS-only pages (which would 302 via CMSLocaleFallbackMiddleware), whatsnew
    URLs are registered with prefer_cms(WhatsnewView). When no CMS fallback page exists,
    prefer_cms falls through to the Django view, which returns 200.
    """
    es_mx_locale = LocaleFactory(language_code="es-MX")
    es_ar_locale = LocaleFactory(language_code="es-AR")

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()

    es_ar_root = en_us_root.copy_for_translation(es_ar_locale)
    es_ar_root.save_revision().publish()

    # WNP exists only in en-US; es-MX has no CMS equivalent.
    # Since the URL is wrapped in prefer_cms(), it falls through to the Django WhatsnewView.
    en_us_wnp_index = WhatsNewIndexPageFactory(parent=en_us_root, slug="whatsnew", live=True)
    WhatsNewPageFactory(parent=en_us_wnp_index, slug="149", version="149")

    response = client.get("/es-AR/whatsnew/149/")

    # The Django WhatsnewView handles the request
    assert response.status_code == 200
    assert [template.name for template in response.templates] == ["firefox/whatsnew/evergreen.html"]
    assert response.context["view"].__class__.__name__ == "WhatsnewView"
    # The response has a canonical tag, and is not indexable
    html = response.content.decode("utf-8")
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/es-AR/whatsnew/149/"' in html
    assert '<meta name="robots" content="noindex,follow">' in html
