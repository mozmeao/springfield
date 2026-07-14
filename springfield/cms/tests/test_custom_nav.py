# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Locale, Site

from springfield.cms.fixtures.navigation_fixtures import build_top_level_link
from springfield.cms.models import NavigationSnippet
from springfield.cms.models.pages import (
    ArticleDetailPage,
    ArticleIndexPage,
    ArticleThemePage,
    BlogArticlePage,
    BlogIndexPage,
    ContactPage,
    CustomNavPageMixin,
    DownloadPage,
    FlareDocsIndexPage,
    FreeFormPage2026,
    HomePage,
    RoadmapPage,
    SmartWindowPage,
    ThanksPage,
    WhatsNewPage2026,
)
from springfield.cms.tests.factories import FreeFormPage2026Factory

pytestmark = [pytest.mark.django_db]

CUSTOM_NAV_PAGES = [
    HomePage,
    DownloadPage,
    ThanksPage,
    ArticleIndexPage,
    ArticleDetailPage,
    ArticleThemePage,
    FreeFormPage2026,
    WhatsNewPage2026,
    SmartWindowPage,
    BlogIndexPage,
    BlogArticlePage,
    RoadmapPage,
    ContactPage,
    FlareDocsIndexPage,
]


def make_snippet(name="Custom nav", live=True, locale=None):
    """Create a NavigationSnippet with a single distinctive top-level link."""
    snippet = NavigationSnippet.objects.create(
        locale=locale or Locale.get_default(),
        name=name,
        items=[build_top_level_link("Custom Nav Link", custom_url="/custom-nav/", block_id="b1")],
        live=live,
    )
    if live:
        snippet.save_revision().publish()
    snippet.refresh_from_db()
    return snippet


@pytest.mark.parametrize("page_model", CUSTOM_NAV_PAGES)
def test_target_pages_use_mixin_and_have_fk(page_model):
    assert issubclass(page_model, CustomNavPageMixin)
    field = page_model._meta.get_field("custom_navigation")
    assert field.related_model is NavigationSnippet
    assert field.null is True


def test_get_context_includes_localized_snippet(rf):
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet()
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] == snippet


def test_get_context_none_when_unset(rf):
    site = Site.objects.get(is_default_site=True)
    page = FreeFormPage2026Factory(parent=site.root_page)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] is None


def test_get_context_none_when_snippet_not_live(rf):
    site = Site.objects.get(is_default_site=True)
    snippet = make_snippet(live=False)
    page = FreeFormPage2026Factory(parent=site.root_page, custom_navigation=snippet)
    context = page.get_context(rf.get("/"))
    assert context["custom_navigation"] is None
