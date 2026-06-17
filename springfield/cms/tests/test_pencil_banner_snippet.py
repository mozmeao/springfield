# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale

from springfield.cms.fixtures.feature_page_fixtures import get_features_theme_page
from springfield.cms.fixtures.freeformpage import get_freeform_page_test_page
from springfield.cms.fixtures.homepage_fixtures import get_home_test_page
from springfield.cms.fixtures.snippet_fixtures import get_pencil_banner_snippet
from springfield.cms.models import ArticleDetailPage
from springfield.cms.models.pages import (
    ArticleDetailPagePencilBannerPlacement,
    ArticleThemePagePencilBannerPlacement,
    HomePagePencilBannerPlacement,
)

pytestmark = [pytest.mark.django_db]


def test_freeform_page_renders_pencil_banner(minimal_site, rf):
    page = get_freeform_page_test_page()
    snippet = get_pencil_banner_snippet()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    banner = soup.find("div", class_="fl-pencil-banner")
    assert banner, "Pencil banner should be rendered on the page"

    link = banner.find("a", class_="fl-pencil-banner-link")
    assert link, "Pencil banner should contain a link"
    assert link["href"] == snippet.link, "Pencil banner link should have the correct URL"

    title = banner.find("span", class_="fl-pencil-banner-title")
    assert title, "Pencil banner title should be rendered"
    assert BeautifulSoup(snippet.title, "html.parser").get_text() in title.get_text()
    assert title.find("i"), "Italic badge should be rendered inside the title"
    assert "has-badge-start" in title.get("class", []), "Title should have has-badge-start class when badge is first"

    description = banner.find("span", class_="fl-pencil-banner-description")
    assert description, "Pencil banner description should be rendered"
    assert BeautifulSoup(snippet.description, "html.parser").get_text() in description.get_text()

    assert banner.find("button"), "Dismiss button should be rendered when dismissable=True"


def test_unpublished_snippet_does_not_render(minimal_site, rf):
    page = get_freeform_page_test_page()
    snippet = get_pencil_banner_snippet()
    snippet.unpublish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not soup.find("div", class_="fl-pencil-banner"), "Pencil banner should not render when snippet is unpublished"


def test_translated_page_renders_translated_snippet(minimal_site, rf):
    en_page = get_freeform_page_test_page()
    en_snippet = get_pencil_banner_snippet()

    fr_locale = Locale.objects.get(language_code="fr")

    fr_snippet = en_snippet.copy_for_translation(fr_locale)
    fr_snippet.title = '<p data-block-key="fr001">Nouveau Firefox est là</p>'
    fr_snippet.save()
    fr_snippet.save_revision().publish()
    fr_snippet.refresh_from_db()

    fr_page = en_page.copy_for_translation(fr_locale, copy_parents=True)
    fr_page.save_revision().publish()

    translation.activate("fr")
    request = rf.get(fr_page.get_full_url())
    response = fr_page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    banner = soup.find("div", class_="fl-pencil-banner")
    assert banner, "Pencil banner should be rendered on translated page"
    assert "Nouveau Firefox" in banner.get_text()
    assert "Firefox is here" not in banner.get_text(), "English snippet content should not appear on French page"


def test_page_without_pencil_banner_placement_does_not_render_banner(minimal_site, rf):
    page = get_freeform_page_test_page()
    page.pencil_banner_placements.all().delete()
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not soup.find("div", class_="fl-pencil-banner"), "Pencil banner should not render when no placement exists"


def _make_home_page():
    return get_home_test_page(), HomePagePencilBannerPlacement


def _make_article_theme_page():
    return get_features_theme_page(), ArticleThemePagePencilBannerPlacement


def _make_article_detail_page():
    theme_page = get_features_theme_page()
    page = ArticleDetailPage.objects.child_of(theme_page).filter(slug="test-pencil-detail").first()
    if not page:
        page = ArticleDetailPage(
            slug="test-pencil-detail",
            title="Test Pencil Detail",
            content=[],
        )
        theme_page.add_child(instance=page)
    return page, ArticleDetailPagePencilBannerPlacement


PAGES_WITH_PENCIL_BANNER = [
    pytest.param(_make_home_page, id="home"),
    pytest.param(_make_article_theme_page, id="article_theme"),
    pytest.param(_make_article_detail_page, id="article_detail"),
]


@pytest.mark.parametrize("page_factory", PAGES_WITH_PENCIL_BANNER)
def test_page_renders_pencil_banner(page_factory, minimal_site, rf):
    page, placement_cls = page_factory()
    snippet = get_pencil_banner_snippet()
    placement_cls.objects.get_or_create(page=page, snippet=snippet)
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find("div", class_="fl-pencil-banner"), f"Pencil banner should render on {page.__class__.__name__}"
