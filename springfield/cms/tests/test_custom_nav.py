# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import override_settings

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, Site

from springfield.cms.fixtures.navigation_fixtures import build_top_level_link
from springfield.cms.models import NavigationSnippet
from springfield.cms.models.pages import FreeFormPage2026
from springfield.cms.tests.factories import DownloadPageFactory, FlareDocsIndexPageFactory, FreeFormPage2026Factory, LocaleFactory

pytestmark = [pytest.mark.django_db]


def make_snippet(name="Custom nav", live=True, locale=None, is_default=False):
    """Create a NavigationSnippet with a single distinctive top-level link."""
    snippet = NavigationSnippet.objects.create(
        locale=locale or Locale.get_default(),
        name=name,
        items=[build_top_level_link("Custom Nav Link", custom_url="/custom-nav/", block_id="b1")],
        live=live,
        is_default=is_default,
    )
    if live:
        snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


def test_get_context_includes_localized_snippet_for_custom_navigation(rf):
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] == snippet


def test_get_context_returns_none_for_custom_navigation(rf):
    site = Site.objects.get(is_default_site=True)
    page = FreeFormPage2026Factory(parent=site.root_page)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] is None


def test_get_context_returns_none_for_custom_navigation_when_snippet_is_not_live(rf):
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet(live=False)
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] is None


def get_nav_soup(client, page):
    response = client.get(page.url)
    assert response.status_code == 200
    return BeautifulSoup(response.content.decode("utf-8"), "html.parser")


def test_page_without_header_template_override_renders_custom_nav(client):
    # FlareDocsIndexPage inherits base-flare's flare_header block.
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    page = FlareDocsIndexPageFactory(parent=site.root_page, custom_navigation=snippet)
    page.save_revision().publish()

    soup = get_nav_soup(client, page)
    cms_menu = soup.find("ul", class_="fl-nav-menu-cms")
    assert cms_menu is not None
    assert "Custom Nav Link" in cms_menu.get_text()


def test_page_without_header_override_falls_back_to_static_nav_if_no_snippet(client):
    site = Site.objects.get(is_default_site=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-static-nav")
    page.save_revision().publish()

    soup = get_nav_soup(client, page)
    assert soup.find("ul", class_="fl-nav-menu-cms") is None
    # The static header still renders its nav container.
    assert soup.find("nav", class_="fl-nav") is not None


def test_page_without_header_override_uses_default_navigation_snippet(client):
    # No custom_navigation on the page or its ancestors, the header template
    # supplies the published default snippet.
    site = Site.objects.get(is_default_site=True)
    make_snippet(name="Default nav", is_default=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-default-nav")
    page.save_revision().publish()

    soup = get_nav_soup(client, page)
    cms_menu = soup.find("ul", class_="fl-nav-menu-cms")
    assert cms_menu is not None
    assert "Custom Nav Link" in cms_menu.get_text()


def test_page_with_override_header_template_renders_custom_nav(client):
    # FreeFormPage2026 overrides flare_header (theme="dark") and shows the menu
    # (show_navigation defaults to True).
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet, slug="freeform-custom-nav")
    page.save_revision().publish()

    soup = get_nav_soup(client, page)
    cms_menu = soup.find("ul", class_="fl-nav-menu-cms")
    assert cms_menu is not None
    assert "Custom Nav Link" in cms_menu.get_text()


def test_child_page_renders_inherited_ancestor_custom_nav(client):
    # The child has no custom_navigation of its own, so it must inherit the
    # parent's custom navigation snippet.
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    parent = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet, slug="freeform-nav-parent")
    parent.save_revision().publish()
    child = FreeFormPage2026Factory(parent=parent, custom_navigation=None, slug="freeform-nav-child")
    child.save_revision().publish()

    soup = get_nav_soup(client, child)
    cms_menu = soup.find("ul", class_="fl-nav-menu-cms")
    assert cms_menu is not None
    assert "Custom Nav Link" in cms_menu.get_text()


def test_page_header_options_propagate_through_include_template(client):
    # DownloadPage sets theme="dark" in its flare_header block. Both the theme
    #  and the custom nav must render.
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    page = DownloadPageFactory(parent=site.root_page, custom_navigation=snippet, slug="download-dark-nav")
    page.save_revision().publish()

    soup = get_nav_soup(client, page)
    header = soup.find("header", class_="fl-header")
    assert header is not None
    assert "fl-force-dark-theme" in header.get("class", [])
    assert soup.find("ul", class_="fl-nav-menu-cms") is not None


@override_settings(FALLBACK_LOCALES={"es-CL": "es-MX"})
def test_alias_locale_renders_fallback_locale_snippet(client):
    """Requesting an alias-locale (es-CL) URL renders the fallback-locale (es-MX) snippet."""
    es_mx_locale = LocaleFactory(language_code="es-MX")
    LocaleFactory(language_code="es-CL")  # alias: Locale record, no page tree

    site = Site.objects.get(is_default_site=True)
    en_us_root = site.root_page

    es_mx_root = en_us_root.copy_for_translation(es_mx_locale)
    es_mx_root.save_revision().publish()

    # en-US base snippet + its es-MX translation (same translation_key).
    en_us_snippet = make_snippet(name="Nav en-US")
    es_mx_snippet = NavigationSnippet.objects.create(
        locale=es_mx_locale,
        translation_key=en_us_snippet.translation_key,
        name="Nav es-MX",
        items=[build_top_level_link("Enlace es-MX", custom_url="/es-mx-nav/", block_id="b2")],
    )
    es_mx_snippet.save_revision().publish()

    # Synchronized FK points at the same base snippet for the es-MX page.
    es_mx_page = FreeFormPage2026(slug="alias-nav-test", title="ES-MX Page", locale=es_mx_locale, custom_navigation=en_us_snippet)
    es_mx_root.add_child(instance=es_mx_page)
    es_mx_page.save_revision().publish()

    es_cl_url = es_mx_page.url.replace("es-MX", "es-CL")
    response = client.get(es_cl_url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")
    cms_menu = soup.find("ul", class_="fl-nav-menu-cms")
    assert cms_menu is not None
    # The es-MX (fallback) snippet renders, not the en-US base snippet.
    assert "Enlace es-MX" in cms_menu.get_text()
    assert "Custom Nav Link" not in cms_menu.get_text()
