# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.test import override_settings
from django.utils import translation

import pytest
from bs4 import BeautifulSoup
from waffle.testutils import override_switch
from wagtail.models import Locale, Page, Site

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import (
    AbstractSpringfieldCMSPage,
    SimpleRichTextPage,
    StructuralPage,
    Tag,
    ThanksPage,
)
from springfield.cms.tests.factories import (
    ArticleDetailPageFactory,
    ArticleIndexPageFactory,
    ArticleThemePageFactory,
    DownloadIndexPageFactory,
    DownloadPageFactory,
    FreeFormPage2026Factory,
    FreeFormPageFactory,
    LocaleFactory,
    SimpleRichTextPageFactory,
    StructuralPageFactory,
    WhatsNewIndexPageFactory,
    WhatsNewPage2026Factory,
    WhatsNewPageFactory,
)

pytestmark = [
    pytest.mark.django_db,
]


@mock.patch("springfield.cms.models.SimpleRichTextPage.get_view_restrictions")
@pytest.mark.parametrize(
    "fake_restrictions, expected_headers",
    (
        ([], "max-age=600"),
        ([mock.Mock()], "max-age=0, no-cache, no-store, must-revalidate, private"),
    ),
    ids=[
        "Default, unrestricted-page behaviour",
        "Restricted-page behaviour",
    ],
)
def test_cache_control_headers_on_pages_with_view_restrictions(
    mock_get_view_restrictions,
    fake_restrictions,
    expected_headers,
    client,
    minimal_site,
):
    mock_get_view_restrictions.return_value = fake_restrictions

    page = SimpleRichTextPage.objects.last()  # made by the minimal_site fixture

    # Confirm we're using the base page
    assert isinstance(page, AbstractSpringfieldCMSPage)

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/test-page/"

    response = client.get(_relative_url)

    assert response.get("Cache-Control") == expected_headers


def test_StructuralPage_serve_methods(
    minimal_site,
    rf,
):
    "Show that structural pages redirect to their parent rather than serve anything"

    root_page = SimpleRichTextPage.objects.first()
    sp = StructuralPageFactory(parent=root_page, slug="folder-page")
    sp.save()

    _relative_url = sp.relative_url(minimal_site)
    assert _relative_url == "/en-US/folder-page/"

    request = rf.get(_relative_url)
    live_result = sp.serve(request)
    assert live_result.headers["location"].endswith(root_page.url)

    preview_result = sp.serve_preview(request)
    assert preview_result.headers["location"].endswith(root_page.url)


@pytest.mark.parametrize(
    "config, page_class, success_expected",
    (
        ("__all__", SimpleRichTextPage, True),  # same as default
        ("firefox.SomeOtherPageClass,cms.StructuralPage,cms.SimpleRichTextPage", StructuralPage, True),
        ("cms.SimpleRichTextPage", SimpleRichTextPage, True),
        ("cms.SimpleRichTextPage,firefox.SomeOtherPageClass", SimpleRichTextPage, True),
        ("firefox.SomeOtherPageClass,cms.SimpleRichTextPage", SimpleRichTextPage, True),
        ("firefox.SomeOtherPageClass,firefox.SomeOtherPageClass", SimpleRichTextPage, False),
        ("firefox.SomeOtherPageClass", SimpleRichTextPage, False),
        ("firefox.SomeOtherPageClass,legal.SomeLegalPageClass", StructuralPage, False),
    ),
)
def test_CMS_ALLOWED_PAGE_MODELS_controls_Page_can_create_at(
    config,
    page_class,
    success_expected,
    minimal_site,
):
    home_page = SimpleRichTextPage.objects.last()
    with override_settings(Dev=False, CMS_ALLOWED_PAGE_MODELS=config.split(",")):
        assert page_class.can_create_at(home_page) == success_expected


@mock.patch("springfield.cms.models.base.compute_cms_page_locales")
def test__patch_request_for_springfield__locales_available_via_cms(
    mock_compute_cms_page_locales,
    minimal_site,
    rf,
):
    request = rf.get("/some-path/that/is/irrelevant")

    page = SimpleRichTextPage.objects.last()  # made by the minimal_site fixture

    mock_compute_cms_page_locales.return_value = (["en-US", "fr", "pt-BR"], ["en-US", "fr", "pt-BR"])

    patched_request = page.specific._patch_request_for_springfield(request)
    assert sorted(patched_request._locales_available_via_cms) == ["en-US", "fr", "pt-BR"]
    assert sorted(patched_request._content_locales_via_cms) == ["en-US", "fr", "pt-BR"]


def test__patch_request_for_springfield_annotates_is_cms_page(tiny_localized_site, rf):
    request = rf.get("/some-path/that/is/irrelevant")
    en_us_homepage = Page.objects.get(locale__language_code="en-US", slug="home")
    en_us_test_page = en_us_homepage.get_children()[0]
    assert en_us_test_page.specific.__class__ == SimpleRichTextPage

    patched_request = en_us_test_page.specific._patch_request_for_springfield(request)
    assert patched_request.is_cms_page is True


# ---------------------------------------------------------------------------
# get_active_locale_url
# ---------------------------------------------------------------------------


def test_get_active_locale_url_returns_original_url(tiny_localized_site):
    """Page in the active locale: URL is returned as-is."""
    page = Page.objects.get(locale__language_code="en-US", slug="child-page").specific
    with translation.override("en-US"):
        url = page.get_active_locale_url()
    assert url == page.get_url()


@override_settings(FALLBACK_LOCALES={})
def test_get_active_locale_url_returns_original_url_if_no_fallback_locales(tiny_localized_site):
    """No FALLBACK_LOCALES: URL retains the page's own locale prefix even when active lang differs."""
    fr_page = Page.objects.get(locale__language_code="fr", slug="child-page").specific
    with translation.override("en-US"):
        url = fr_page.get_active_locale_url()
    assert url == fr_page.get_url()


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_active_locale_url_returns_url_with_fallback_locale(tiny_localized_site):
    """Active language is alias (pt-PT → pt-BR): URL prefix is rewritten to pt-PT."""
    LocaleFactory(language_code="pt-PT")
    pt_br_page = Page.objects.get(locale__language_code="pt-BR", slug="child-page").specific
    with translation.override("pt-PT"):
        url = pt_br_page.get_active_locale_url()
    assert "/pt-PT/" in url
    assert "/pt-BR/" not in url


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_active_locale_url_returns_original_url_if_same_as_active_locale(tiny_localized_site):
    """Active language is pt-PT but page is already in pt-PT locale: no substitution."""
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    site.root_page.copy_for_translation(pt_pt_locale)
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    pt_pt_page = en_us_page.copy_for_translation(pt_pt_locale)
    pt_pt_page.save_revision().publish()
    with translation.override("pt-PT"):
        url = pt_pt_page.specific.get_active_locale_url()
    assert "/pt-PT/" in url
    assert "/pt-BR/" not in url


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_active_locale_url_returns_original_url_if_active_language_not_in_fallback_locales(tiny_localized_site):
    """Active language (fr) is not in FALLBACK_LOCALES: URL is unchanged."""
    fr_page = Page.objects.get(locale__language_code="fr", slug="child-page").specific
    with translation.override("fr"):
        url = fr_page.get_active_locale_url()
    assert "/fr/" in url
    assert "/pt-BR/" not in url


def test_whats_new_index_page_redirects_to_latest_whats_new(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    v123_page = WhatsNewPageFactory(parent=index_page, slug="123", version="123")
    v123_page.save()
    v124_page = WhatsNewPageFactory(parent=index_page, slug="124", version="124")
    v124_page.save()

    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v124_page.url)

    v125_page = WhatsNewPage2026Factory(parent=index_page, slug="125", version="125")
    v125_page.save()

    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v125_page.url)


def test_whats_new_index_page_excludes_general_page_from_latest_redirect(
    minimal_site,
    rf,
):
    """General WNP (slug='general') must not be treated as the 'latest' version.
    The index page should redirect to the highest numeric version, not to the
    general page (which sorts after digits lexicographically)."""
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew-2")

    v150_page = WhatsNewPage2026Factory(parent=index_page, slug="150", version="150")
    v150_page.save()

    from springfield.cms.tests.factories import GeneralWhatsNewPage2026Factory

    general_page = GeneralWhatsNewPage2026Factory(parent=index_page)
    general_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    request = rf.get(_relative_url)

    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(v150_page.url)


def test_whats_new_index_page_redirects_to_home_if_no_children(
    minimal_site,
    rf,
):
    root_page = SimpleRichTextPage.objects.first()
    index_page = WhatsNewIndexPageFactory(parent=root_page, slug="whatsnew")
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/whatsnew/"

    request = rf.get(_relative_url)

    # No WhatsNewPage exists yet, so should redirect to /
    response = index_page.specific.serve(request)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_whats_new_index_page_redirects_to_locale_appropriate_child(
    tiny_localized_site,
    rf,
):
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page

    pt_br_locale = Locale.objects.get(language_code="pt-BR")
    pt_br_root_page = en_us_root_page.get_translation(pt_br_locale)

    assert pt_br_root_page

    en_us_index_page = WhatsNewIndexPageFactory(parent=en_us_root_page, slug="whatsnew")
    en_us_index_page.save()

    pt_br_index_page = en_us_index_page.copy_for_translation(pt_br_locale)
    pt_br_index_page.title = "O que há de novo no Firefox"
    pt_br_index_page.save()
    pt_br_index_page.save_revision().publish()

    _en_us_relative_url = en_us_index_page.relative_url(tiny_localized_site)
    assert _en_us_relative_url == "/en-US/whatsnew/"

    _pt_br_relative_url = pt_br_index_page.relative_url(tiny_localized_site)
    assert _pt_br_relative_url == "/pt-BR/whatsnew/"

    en_us_v123_page = WhatsNewPageFactory(parent=en_us_index_page, slug="123", version="123")
    en_us_v123_page.save()
    en_us_v124_page = WhatsNewPageFactory(parent=en_us_index_page, slug="124", version="124")
    en_us_v124_page.save()

    pt_br_v123_page = en_us_v123_page.copy_for_translation(pt_br_locale)
    pt_br_v123_page.title = "O que tem de novo no Firefox 123"
    pt_br_v123_page.save_revision().publish()

    pt_br_v124_page = en_us_v124_page.copy_for_translation(pt_br_locale)
    pt_br_v124_page.title = "O que tem de novo no Firefox 124"
    pt_br_v124_page.save_revision().publish()

    pt_br_index_page.refresh_from_db()

    en_us_request = rf.get(_en_us_relative_url)

    response = en_us_index_page.specific.serve(en_us_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(en_us_v124_page.url)

    pt_br_request = rf.get(_pt_br_relative_url)
    response = pt_br_index_page.specific.serve(pt_br_request)
    assert response.status_code == 302
    assert response.headers["location"].endswith(pt_br_v124_page.url)


def test_freeform_page(minimal_site, rf):
    root_page = SimpleRichTextPage.objects.first()
    page = FreeFormPageFactory(parent=root_page, slug="freeform-page")
    page.save()

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/freeform-page/"

    request = rf.get(_relative_url)
    response = page.specific.serve(request)
    assert response.status_code == 200


def test_freeform_page_2026(minimal_site, rf):
    root_page = SimpleRichTextPage.objects.first()
    page = FreeFormPage2026Factory(parent=root_page, slug="freeform-2026-page")
    page.save()

    _relative_url = page.relative_url(minimal_site)
    assert _relative_url == "/en-US/freeform-2026-page/"

    request = rf.get(_relative_url)
    response = page.specific.serve(request)
    assert response.status_code == 200


@override_switch("FLARE26_ENABLED", active=False)
def test_article_index_and_detail_pages(minimal_site, rf):
    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="All the Articles",
        sub_title="A collection of all articles.",
        other_articles_heading="<p data-block-key='c1bc4d7eadf0'>More Articles</p>",
        other_articles_subheading="<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>",
    )
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/articles/"

    request = rf.get(_relative_url)
    response = index_page.specific.serve(request)
    assert response.status_code == 200

    image, _, _, _ = get_placeholder_images()

    for i in range(1, 3):
        featured_page = ArticleDetailPageFactory(
            parent=index_page,
            title=f"Featured Article {i}",
            slug=f"featured-article-{i}",
            description=f"Description for Featured Article {i}",
            featured=True,
            image=image,
        )
        featured_page.save()

        _featured_relative_url = featured_page.relative_url(minimal_site)
        assert _featured_relative_url == f"/en-US/articles/featured-article-{i}/"

        featured_request = rf.get(_featured_relative_url)
        featured_response = featured_page.specific.serve(featured_request)
        assert featured_response.status_code == 200

        article = ArticleDetailPageFactory(
            parent=index_page,
            title=f"Article {i}",
            slug=f"article-{i}",
            description=f"Description for Article {i}",
            featured=False,
            image=image,
        )
        article.save()

        _article_relative_url = article.relative_url(minimal_site)
        assert _article_relative_url == f"/en-US/articles/article-{i}/"

        article_request = rf.get(_article_relative_url)
        article_response = article.specific.serve(article_request)
        assert article_response.status_code == 200

    index_page.refresh_from_db()
    request = rf.get(_relative_url)
    response = index_page.specific.serve(request)
    page_content = response.content

    soup = BeautifulSoup(page_content, "html.parser")

    assert "All the Articles" in soup.find("h1").text

    card_grids = soup.find_all("div", class_="fl-card-grid")
    assert len(card_grids) == 2

    featured_cards = card_grids[0].find_all(class_="fl-illustration-card")
    assert len(featured_cards) == 2
    # Articles are ordered by the first_published_at field in descending order,
    # but in this test we only verify their presence on the page.
    for i in range(1, 3):
        matching_card = next(c for c in featured_cards if f"Featured Article {i}" in c.find("h3").text)
        assert f"Description for Featured Article {i}" in matching_card.text
        assert matching_card.find("a")["href"].endswith(f"/en-US/articles/featured-article-{i}/")

    article_cards = card_grids[1].find_all(class_="fl-card")
    assert len(article_cards) == 2
    # Articles are ordered by the first_published_at field in descending order,
    # but in this test we only verify their presence on the page.
    for i in range(1, 3):
        matching_card = next(c for c in article_cards if f"Article {i}" in c.find("h3").text)
        assert f"Description for Article {i}" in matching_card.text
        assert matching_card.find("a")["href"].endswith(f"/en-US/articles/article-{i}/")


@override_switch("FLARE26_ENABLED", active=True)
def test_article_index_and_detail_pages_2026(minimal_site, rf):
    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="All the Articles",
        sub_title="A collection of all articles.",
        other_articles_heading="<p data-block-key='c1bc4d7eadf0'>More Articles</p>",
        other_articles_subheading="<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>",
    )
    index_page.save()

    _relative_url = index_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/articles/"

    request = rf.get(_relative_url)
    response = index_page.specific.serve(request)
    assert response.status_code == 200

    image, dark_image, mobile_image, mobile_dark_image = get_placeholder_images()

    for i in range(1, 3):
        tag = Tag.objects.create(name=f"Tag {i}", slug=f"tag-{i}", locale=index_page.locale)

        featured_page = ArticleDetailPageFactory(
            parent=index_page,
            title=f"Featured Article {i}",
            slug=f"featured-article-{i}",
            description=f"Description for Featured Article {i}",
            featured=True,
            image=image,
            tag=tag,
            sticker=dark_image,
        )
        featured_page.save()

        _featured_relative_url = featured_page.relative_url(minimal_site)
        assert _featured_relative_url == f"/en-US/articles/featured-article-{i}/"

        featured_request = rf.get(_featured_relative_url)
        featured_response = featured_page.specific.serve(featured_request)
        assert featured_response.status_code == 200

        article = ArticleDetailPageFactory(
            parent=index_page,
            title=f"Article {i}",
            slug=f"article-{i}",
            description=f"Description for Article {i}",
            featured=False,
            image=image,
            tag=tag,
            sticker=dark_image,
        )
        article.save()

        _article_relative_url = article.relative_url(minimal_site)
        assert _article_relative_url == f"/en-US/articles/article-{i}/"

        article_request = rf.get(_article_relative_url)
        article_response = article.specific.serve(article_request)
        assert article_response.status_code == 200

    index_page.refresh_from_db()
    request = rf.get(_relative_url)
    response = index_page.specific.serve(request)
    page_content = response.content

    soup = BeautifulSoup(page_content, "html.parser")

    assert "All the Articles" in soup.find("h1").text

    card_grids = soup.find_all("div", class_="fl-card-grid")
    assert len(card_grids) == 2

    featured_cards = card_grids[0].find_all(class_="fl-sticker-card")
    assert len(featured_cards) == 2
    # Articles are ordered by the first_published_at field in descending order,
    # but in this test we only verify their presence on the page.
    for i in range(1, 3):
        matching_card = next(c for c in featured_cards if f"Featured Article {i}" in c.find("h2").text)
        assert f"Description for Featured Article {i}" in matching_card.text
        assert matching_card.find("a")["href"].endswith(f"/en-US/articles/featured-article-{i}/")
        superheading = matching_card.find(class_="fl-superheading")
        assert superheading and f"Tag {i}" in superheading.text

    sticker_cards = card_grids[1].find_all(class_="fl-illustration-card")
    assert len(sticker_cards) == 2
    # Articles are ordered by the first_published_at field in descending order,
    # but in this test we only verify their presence on the page.
    for i in range(1, 3):
        card = next(c for c in sticker_cards if f"Article {i}" in c.find("h3").text)
        assert f"Description for Article {i}" in card.text
        assert card.find("a")["href"].endswith(f"/en-US/articles/article-{i}/")


def test_article_detail_content(minimal_site, rf):
    image, _, _, _ = get_placeholder_images()
    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="All the Articles",
        sub_title="A collection of all articles.",
        other_articles_heading="<p data-block-key='c1bc4d7eadf0'>More Articles</p>",
        other_articles_subheading="<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>",
    )
    index_page.save()

    article_page = ArticleDetailPageFactory(
        parent=index_page,
        title="Test Article Detail Page",
        slug="article-detail-page",
        description="Test Article Description for Index Page",
        content=[
            {
                "type": "text",
                "value": f'<p>This is the content of the test article. With a link to the <a id="{index_page.id}" linktype="page">Index Page</a></p>',
            },
        ],
        image=image,
    )
    article_page.save()

    _relative_url = article_page.relative_url(minimal_site)
    assert _relative_url == "/en-US/articles/article-detail-page/"

    request = rf.get(_relative_url)
    response = article_page.specific.serve(request)
    assert response.status_code == 200

    page_content = response.content
    soup = BeautifulSoup(page_content, "html.parser")

    assert "Test Article Detail Page" in soup.find("h1").text
    content = soup.find("section", class_="fl-rich-text").find("p")
    assert "This is the content of the test article. With a link to the Index Page" in content.text
    link = content.find("a")
    assert link["href"].endswith(index_page.url)


def test_article_index_page_shows_sibling_and_child_articles(minimal_site, rf):
    """ArticleIndexPage should include ArticleDetailPages that are siblings
    (co-children of an ArticleThemePage) as well as its own children."""
    root_page = SimpleRichTextPage.objects.first()

    theme_page = ArticleThemePageFactory(parent=root_page, slug="theme", title="Article Theme")
    theme_page.save()

    index_page = ArticleIndexPageFactory(
        parent=theme_page,
        slug="articles",
        title="All the Articles",
        other_articles_heading="<p>More Articles</p>",
        show_sibling_detail_pages=True,
    )
    index_page.save()

    image, _, _, _ = get_placeholder_images()

    sibling_featured = ArticleDetailPageFactory(
        parent=theme_page,
        slug="sibling-featured",
        title="Sibling Featured Article",
        featured=True,
        image=image,
    )
    sibling_featured.save()

    sibling_article = ArticleDetailPageFactory(
        parent=theme_page,
        slug="sibling-article",
        title="Sibling Article",
        featured=False,
        image=image,
    )
    sibling_article.save()

    child_article = ArticleDetailPageFactory(
        parent=index_page,
        slug="child-article",
        title="Child Article",
        featured=False,
        image=image,
    )
    child_article.save()

    index_page.refresh_from_db()
    request = rf.get(index_page.relative_url(minimal_site))
    context = index_page.specific.get_context(request)

    assert sibling_featured in context["featured_articles"]
    assert sibling_article in context["list_articles"]
    assert child_article in context["list_articles"]


@pytest.mark.parametrize(
    "django_locale,expected_locale_code",
    [
        ("en-gb", "en-GB"),  # Lowercase from Django -> mixed-case
        ("en-ca", "en-CA"),  # Another mixed-case example
        ("pt-br", "pt-BR"),  # Another mixed-case example
        ("de", "de"),  # Simple code stays the same
        ("fr", "fr"),  # Simple code stays the same
    ],
)
def test_springfield_locale_get_active_normalizes_case(django_locale, expected_locale_code):
    """
    Test that SpringfieldLocale.get_active() normalizes Django's lowercase
    language codes to match Springfield's mixed-case Locale records.

    This is a unit test for the SpringfieldLocale.get_active() method that
    verifies it properly handles the case mismatch between Django's internal
    lowercase language codes (e.g., 'en-gb') and Springfield's mixed-case
    Locale records (e.g., 'en-GB').

    Without this normalization, Wagtail's routing would fail to find the
    correct Locale and fall back to the default locale.
    """
    # Create the Locale record with mixed-case code
    locale = LocaleFactory(language_code=expected_locale_code)
    assert locale.language_code == expected_locale_code

    # Mock Django's translation.get_language() to return lowercase
    with mock.patch("django.utils.translation.get_language", return_value=django_locale):
        # Call SpringfieldLocale.get_active() (which is patched onto Locale)
        active_locale = Locale.get_active()

        # Verify it found the correct Locale despite the case mismatch
        assert active_locale.id == locale.id
        assert active_locale.language_code == expected_locale_code


def test_springfield_locale_get_active_falls_back_to_default():
    """
    Test that SpringfieldLocale.get_active() falls back to the default locale
    when the requested locale doesn't exist.
    """
    # Ensure en-US exists as the default
    default_locale = Locale.objects.get(language_code="en-US")

    # Mock Django returning a locale that doesn't exist
    with mock.patch("django.utils.translation.get_language", return_value="xx-YY"):
        active_locale = Locale.get_active()

        # Should fall back to en-US
        assert active_locale.id == default_locale.id
        assert active_locale.language_code == "en-US"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_springfield_locale_get_active_uses_configured_fallback_locale():
    """
    When an alias locale (pt-PT) has no Locale DB record, get_active() should
    return the configured fallback locale (pt-BR) rather than jumping straight
    to en-US.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    # Deliberately do NOT create a pt-PT Locale record
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    # Django returns lowercase codes; pt-PT becomes "pt-pt"
    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        active_locale = Locale.get_active()

    assert active_locale.id == pt_br_locale.id
    assert active_locale.language_code == "pt-BR"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_springfield_locale_get_active_falls_back_to_default_when_fallback_locale_also_missing():
    """
    When the alias locale has no DB record and the configured fallback locale
    also has no DB record, get_active() should still fall back safely to en-US.
    """
    # Neither pt-PT nor pt-BR exists
    assert not Locale.objects.filter(language_code="pt-PT").exists()
    assert not Locale.objects.filter(language_code="pt-BR").exists()

    default_locale = Locale.objects.get(language_code="en-US")

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        active_locale = Locale.get_active()

    assert active_locale.id == default_locale.id
    assert active_locale.language_code == "en-US"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_page_localized_returns_fallback_locale_page_when_alias_locale_has_no_db_record():
    """
    When Django's active language is an alias locale (pt-PT) with no Locale DB
    record, page.localized should return the fallback locale's (pt-BR)
    translation rather than the en-US original.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    assert not Locale.objects.filter(language_code="pt-PT").exists()

    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    # copy_for_translation requires the parent to exist in the target locale
    root_page.copy_for_translation(pt_br_locale)

    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-localized-test",
        parent=root_page,
    )
    pt_br_page = en_us_page.copy_for_translation(pt_br_locale)
    pt_br_page.title = "pt-BR Article"
    pt_br_page.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        localized = en_us_page.localized

    assert localized.id == pt_br_page.id
    assert localized.locale == pt_br_locale


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_page_localized_uses_fallback_locale_when_alias_locale_exists_but_no_translation():
    """
    When the alias locale (pt-PT) has a Locale DB record but the page has no
    pt-PT translation, page.localized should return the fallback locale's (pt-BR)
    translation rather than the en-US original.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    _pt_pt_locale = LocaleFactory(language_code="pt-PT")  # Locale exists in DB
    # Deliberately do NOT create a pt-PT translation of the article

    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    root_page.copy_for_translation(pt_br_locale)

    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-fallback-test",
        parent=root_page,
    )
    pt_br_page = en_us_page.copy_for_translation(pt_br_locale)
    pt_br_page.title = "pt-BR Article"
    pt_br_page.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        result = en_us_page.localized

    assert result.id == pt_br_page.id
    assert result.locale == pt_br_locale


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_page_localized_returns_translation_when_active_locale_has_one():
    """
    When the active locale (pt-BR) has a published translation, localized
    returns it directly without consulting FALLBACK_LOCALES.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    root_page.copy_for_translation(pt_br_locale)

    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-normal-locale-test",
        parent=root_page,
    )
    pt_br_page = en_us_page.copy_for_translation(pt_br_locale)
    pt_br_page.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-br"):
        result = en_us_page.localized

    assert result.id == pt_br_page.id
    assert result.locale == pt_br_locale


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_page_localized_returns_translation_when_fallback_locale_has_translation():
    """
    When the active locale (pt-PT) has a translation, localized returns the locale's translation.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    pt_pt_locale = LocaleFactory(language_code="pt-PT")
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    root_page.copy_for_translation(pt_br_locale)
    root_page.copy_for_translation(pt_pt_locale)

    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-normal-locale-test",
        parent=root_page,
    )
    pt_br_page = en_us_page.copy_for_translation(pt_br_locale)
    pt_br_page.title = "pt-BR Article"
    pt_br_page.save_revision().publish()
    pt_pt_page = en_us_page.copy_for_translation(pt_pt_locale)
    pt_pt_page.title = "pt-PT Article"
    pt_pt_page.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        result = en_us_page.localized

    assert result.id == pt_pt_page.id
    assert result.locale == pt_pt_locale


def test_page_localized_returns_self_when_no_translation_and_locale_not_in_fallback_locales():
    """
    When the active locale (fr) is not in FALLBACK_LOCALES and the page has no
    French translation, localized returns the source page unchanged.
    """
    _fr_locale = LocaleFactory(language_code="fr")
    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-no-fallback-test",
    )

    with mock.patch("django.utils.translation.get_language", return_value="fr"):
        result = en_us_page.localized

    assert result.id == en_us_page.id
    assert result.locale.language_code == "en-US"


def test_page_localized_returns_self_for_source_locale():
    """
    When the active locale is the source locale (en-US), localized returns
    the page unchanged without any extra lookups.
    """
    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-source-locale-test",
    )

    with mock.patch("django.utils.translation.get_language", return_value="en-us"):
        result = en_us_page.localized

    assert result.id == en_us_page.id
    assert result.locale.language_code == "en-US"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_page_localized_returns_self_when_fallback_locale_also_has_no_translation():
    """
    When the alias locale (pt-PT) maps to pt-BR via FALLBACK_LOCALES but the
    page has no pt-BR translation either, localized returns the source page.
    """
    _pt_pt_locale = LocaleFactory(language_code="pt-PT")
    _pt_br_locale = LocaleFactory(language_code="pt-BR")
    # No pt-PT or pt-BR translation created for the page

    en_us_page = SimpleRichTextPageFactory(
        title="en-US Article",
        slug="en-us-article-no-fallback-translation-test",
    )

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        result = en_us_page.localized

    assert result.id == en_us_page.id
    assert result.locale.language_code == "en-US"


def test_thanks_page_get_template_default(rf):
    page = ThanksPage()
    request = rf.get("/thanks/")
    assert page.get_template(request) == "cms/thanks_page.html"


def test_thanks_page_get_template_direct(rf):
    page = ThanksPage()
    request = rf.get("/thanks/?s=direct")
    assert page.get_template(request) == "cms/thanks_page__direct.html"


@pytest.mark.parametrize(
    "s_value",
    ["other", "", "DIRECT"],
    ids=["other", "empty", "uppercase"],
)
def test_thanks_page_get_template_ignores_other_s_values(rf, s_value):
    page = ThanksPage()
    request = rf.get(f"/thanks/?s={s_value}")
    assert page.get_template(request) == "cms/thanks_page.html"


# ---- Image variant CSS class tests ----
#
# These tests verify that model-level image variant fields produce the correct
# CSS display classes in the rendered HTML.
def _check_image_variant_classes(container, primary_classes, dark_classes, mobile_classes, dark_mobile_classes):
    """Assert img tags inside an image-variants-display container carry the expected CSS classes.

    Pass None for a variant to assert it is absent.  Class strings use space-separated
    BS4 multi-class matching, e.g. "display-dark display-sm-up".
    """
    if primary_classes:
        assert container.find("img", class_=primary_classes), f"Primary img missing expected classes: '{primary_classes}'"

    if dark_classes:
        dark_img = container.find("img", class_=dark_classes)
        assert dark_img is not None, f"Dark-mode desktop img missing expected classes: '{dark_classes}'"
        # The dark-mode desktop image must never appear on mobile-sized viewports.
        assert "display-xs" not in (dark_img.get("class") or []), "Dark-mode desktop img must not carry display-xs"

    if mobile_classes:
        assert container.find("img", class_=mobile_classes), f"Mobile img missing expected classes: '{mobile_classes}'"

    if dark_mobile_classes:
        assert container.find("img", class_=dark_mobile_classes), f"Dark-mode mobile img missing expected classes: '{dark_mobile_classes}'"


_IMAGE_VARIANT_PARAMS = pytest.mark.parametrize(
    "has_dark, has_mobile, has_dark_mobile, primary_classes, dark_classes, mobile_classes, dark_mobile_classes",
    [
        pytest.param(
            True,
            False,
            False,
            "display-light",  # primary: light-mode only, unrestricted size
            "display-dark",  # dark: dark-mode only, unrestricted size
            None,  # mobile: absent
            None,  # dark-mobile: absent
            id="dark-only",
        ),
        pytest.param(
            False,
            True,
            False,
            "display-sm-up",  # primary: shown on sm-and-up only
            None,  # dark: absent
            "display-xs",  # mobile: shown on xs only
            None,  # dark-mobile: absent
            id="mobile-only",
        ),
        pytest.param(
            True,
            True,
            False,
            "display-light display-sm-up",  # primary: light-mode, sm-and-up
            "display-dark display-sm-up",  # dark desktop: dark-mode, sm-and-up (must NOT be just "display-dark")
            "display-xs",  # mobile: xs only (serves as fallback on dark mobile too)
            None,  # dark-mobile: absent
            id="dark-and-mobile",
        ),
        pytest.param(
            True,
            True,
            True,
            "display-light display-sm-up",  # primary: light-mode, sm-and-up
            "display-dark display-sm-up",  # dark desktop: dark-mode, sm-and-up
            "display-light display-xs",  # mobile: light-mode, xs only
            "display-dark display-xs",  # dark-mobile: dark-mode, xs only
            id="all-variants",
        ),
        pytest.param(
            False,
            False,
            False,
            None,  # primary: no CSS classes (unrestricted, no variants to conflict with)
            None,  # dark: absent
            None,  # mobile: absent
            None,  # dark-mobile: absent
            id="primary-only",
        ),
        pytest.param(
            False,
            False,
            True,
            "display-sm-up",  # primary: restricted to sm-and-up because dark-mobile covers xs
            None,  # dark: absent
            None,  # mobile: absent (mobile variant not set, only dark-mobile is)
            "display-dark display-xs",  # dark-mobile: dark-mode xs only
            id="dark-mobile-only",
        ),
        pytest.param(
            True,
            False,
            True,
            "display-light display-sm-up",  # primary: light-mode, sm-and-up
            "display-dark display-sm-up",  # dark desktop: dark-mode, sm-and-up (dark-mobile triggers sm-up)
            None,  # mobile: absent
            "display-dark display-xs",  # dark-mobile: dark-mode xs only
            id="dark-and-dark-mobile",
        ),
        pytest.param(
            False,
            True,
            True,
            "display-sm-up",  # primary: sm-and-up (mobile variant covers xs)
            None,  # dark: absent
            "display-light display-xs",  # mobile: light-mode xs only
            "display-dark display-xs",  # dark-mobile: dark-mode xs only
            id="mobile-and-dark-mobile",
        ),
    ],
)


@_IMAGE_VARIANT_PARAMS
@override_switch("FLARE26_ENABLED", active=True)
def test_article_detail_page_image_variants(
    minimal_site,
    rf,
    has_dark,
    has_mobile,
    has_dark_mobile,
    primary_classes,
    dark_classes,
    mobile_classes,
    dark_mobile_classes,
):
    """ArticleDetailPage.image and its variants are rendered with correct CSS classes."""
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()

    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="Articles",
        other_articles_heading="<p>Other Articles</p>",
    )
    index_page.save()

    kwargs = dict(parent=index_page, title="Test Article", slug="test-article", image=image)
    if has_dark:
        kwargs["image_dark_mode"] = dark_image
    if has_mobile:
        kwargs["image_mobile"] = mobile_image
    if has_dark_mobile:
        kwargs["image_dark_mode_mobile"] = dark_mobile_image

    article_page = ArticleDetailPageFactory(**kwargs)
    article_page.save()

    request = rf.get(article_page.relative_url(minimal_site))
    response = article_page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    container = soup.find("div", class_="image-variants-display")
    assert container is not None, "Expected image-variants-display container in article detail page"

    expected_img_count = 1 + has_dark + has_mobile + has_dark_mobile
    assert len(container.find_all("img")) == expected_img_count

    _check_image_variant_classes(container, primary_classes, dark_classes, mobile_classes, dark_mobile_classes)


@_IMAGE_VARIANT_PARAMS
@override_switch("FLARE26_ENABLED", active=True)
def test_article_index_page_sticker_variants_flare26(
    minimal_site,
    rf,
    has_dark,
    has_mobile,
    has_dark_mobile,
    primary_classes,
    dark_classes,
    mobile_classes,
    dark_mobile_classes,
):
    """ArticleDetailPage sticker variants are rendered with correct CSS classes on the index page (flare26)."""
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()

    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="Articles",
        other_articles_heading="<p>Other Articles</p>",
    )
    index_page.save()

    sticker_kwargs = dict(sticker=image)
    if has_dark:
        sticker_kwargs["sticker_dark_mode"] = dark_image
    if has_mobile:
        sticker_kwargs["sticker_mobile"] = mobile_image
    if has_dark_mobile:
        sticker_kwargs["sticker_dark_mode_mobile"] = dark_mobile_image

    featured_page = ArticleDetailPageFactory(
        parent=index_page,
        title="Featured Article",
        slug="featured-article",
        featured=True,
        image=image,
        **sticker_kwargs,
    )
    featured_page.save()

    index_page.refresh_from_db()
    request = rf.get(index_page.relative_url(minimal_site))
    response = index_page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    # The featured card section is the first fl-card-grid.
    featured_grid = soup.find("div", class_="fl-card-grid")
    assert featured_grid is not None

    featured_card = featured_grid.find(class_="fl-sticker-card")
    assert featured_card is not None, "Expected a fl-sticker-card in the featured grid"

    container = featured_card.find("div", class_="image-variants-display")
    assert container is not None, "Expected image-variants-display in sticker card"

    expected_img_count = 1 + has_dark + has_mobile + has_dark_mobile
    assert len(container.find_all("img")) == expected_img_count

    _check_image_variant_classes(container, primary_classes, dark_classes, mobile_classes, dark_mobile_classes)


@_IMAGE_VARIANT_PARAMS
@override_switch("FLARE26_ENABLED", active=False)
def test_article_index_page_featured_image_variants(
    minimal_site,
    rf,
    has_dark,
    has_mobile,
    has_dark_mobile,
    primary_classes,
    dark_classes,
    mobile_classes,
    dark_mobile_classes,
):
    """ArticleDetailPage featured_image variants are rendered with correct CSS classes on the index page (non-flare26)."""
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()

    root_page = SimpleRichTextPage.objects.first()
    index_page = ArticleIndexPageFactory(
        parent=root_page,
        slug="articles",
        title="Articles",
        other_articles_heading="<p>Other Articles</p>",
    )
    index_page.save()

    featured_image_kwargs = dict(featured_image=image)
    if has_dark:
        featured_image_kwargs["featured_image_dark_mode"] = dark_image
    if has_mobile:
        featured_image_kwargs["featured_image_mobile"] = mobile_image
    if has_dark_mobile:
        featured_image_kwargs["featured_image_dark_mode_mobile"] = dark_mobile_image

    featured_page = ArticleDetailPageFactory(
        parent=index_page,
        title="Featured Article",
        slug="featured-article",
        featured=True,
        image=image,
        **featured_image_kwargs,
    )
    featured_page.save()

    index_page.refresh_from_db()
    request = rf.get(index_page.relative_url(minimal_site))
    response = index_page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    featured_grid = soup.find("div", class_="fl-card-grid")
    assert featured_grid is not None

    featured_card = featured_grid.find(class_="fl-illustration-card")
    assert featured_card is not None, "Expected a fl-illustration-card in the featured grid"

    container = featured_card.find("div", class_="image-variants-display")
    assert container is not None, "Expected image-variants-display in illustration card"

    expected_img_count = 1 + has_dark + has_mobile + has_dark_mobile
    assert len(container.find_all("img")) == expected_img_count

    _check_image_variant_classes(container, primary_classes, dark_classes, mobile_classes, dark_mobile_classes)


@_IMAGE_VARIANT_PARAMS
def test_download_page_featured_image_variants(
    minimal_site,
    rf,
    has_dark,
    has_mobile,
    has_dark_mobile,
    primary_classes,
    dark_classes,
    mobile_classes,
    dark_mobile_classes,
):
    """DownloadPage.featured_image variants are rendered with correct CSS classes."""
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()

    root_page = SimpleRichTextPage.objects.first()
    download_index = DownloadIndexPageFactory(parent=root_page, slug="download-index")
    download_index.save()

    featured_image_kwargs = dict(featured_image=image)
    if has_dark:
        featured_image_kwargs["featured_image_dark_mode"] = dark_image
    if has_mobile:
        featured_image_kwargs["featured_image_mobile"] = mobile_image
    if has_dark_mobile:
        featured_image_kwargs["featured_image_dark_mode_mobile"] = dark_mobile_image

    download_page = DownloadPageFactory(
        parent=download_index,
        slug="windows",
        platform="windows",
        **featured_image_kwargs,
    )
    download_page.save()

    request = rf.get(download_page.relative_url(minimal_site))
    response = download_page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    container = soup.find("div", class_="fl-download-intro-featured-image")
    assert container is not None, "Expected fl-download-intro-featured-image section"

    variants_div = container.find("div", class_="image-variants-display")
    assert variants_div is not None, "Expected image-variants-display inside featured image section"

    expected_img_count = 1 + has_dark + has_mobile + has_dark_mobile
    assert len(variants_div.find_all("img")) == expected_img_count

    _check_image_variant_classes(variants_div, primary_classes, dark_classes, mobile_classes, dark_mobile_classes)


# Snippets
def test_get_localized_snippet_returns_translation(minimal_site):
    en_us_locale = Locale.objects.get(language_code="en-US")
    fr_locale = Locale.objects.get(language_code="fr")

    original_snippet = Tag.objects.create(name="Original Snippet", slug="original-snippet", locale=en_us_locale)
    translated_snippet = original_snippet.copy_for_translation(fr_locale)
    translated_snippet.name = "Extrait traduit"
    translated_snippet.save()
    translated_snippet.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="fr"):
        localized_snippet = original_snippet.get_localized()
        assert localized_snippet.id == translated_snippet.id
        assert localized_snippet.name == "Extrait traduit"


def test_get_localized_snippet_returns_none_if_translation_is_not_published(minimal_site):
    en_us_locale = Locale.objects.get(language_code="en-US")
    fr_locale = Locale.objects.get(language_code="fr")

    original_snippet = Tag.objects.create(name="Original Snippet", slug="original-snippet", locale=en_us_locale)
    translated_snippet = original_snippet.copy_for_translation(fr_locale)
    translated_snippet.name = "Extrait traduit"
    translated_snippet.live = False
    translated_snippet.save()

    with mock.patch("django.utils.translation.get_language", return_value="fr"):
        localized_snippet = original_snippet.get_localized()
        assert localized_snippet is None


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_localized_snippet_returns_translation_fallback(minimal_site):
    en_us_locale = Locale.objects.get(language_code="en-US")
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    LocaleFactory(language_code="pt-PT")

    original_snippet = Tag.objects.create(name="Original Snippet", slug="original-snippet", locale=en_us_locale)
    translated_snippet = original_snippet.copy_for_translation(pt_br_locale)
    translated_snippet.name = "Snippet traduzido"
    translated_snippet.save()
    translated_snippet.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        localized_snippet = original_snippet.get_localized()
        assert localized_snippet.id == translated_snippet.id
        assert localized_snippet.name == "Snippet traduzido"


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_get_localized_snippet_returns_translation_translated_instance_despite_fallback(minimal_site):
    en_us_locale = Locale.objects.get(language_code="en-US")
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    pt_pt_locale = LocaleFactory(language_code="pt-PT")

    original_snippet = Tag.objects.create(name="Original Snippet", slug="original-snippet", locale=en_us_locale)

    pt_br_snippet = original_snippet.copy_for_translation(pt_br_locale)
    pt_br_snippet.name = "Snippet traduzido"
    pt_br_snippet.save()
    pt_br_snippet.save_revision().publish()

    pt_pt_snippet = original_snippet.copy_for_translation(pt_pt_locale)
    pt_pt_snippet.name = "Trecho traduzido"
    pt_pt_snippet.save()
    pt_pt_snippet.save_revision().publish()

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        localized_snippet = original_snippet.get_localized()
        assert localized_snippet.id == pt_pt_snippet.id
        assert localized_snippet.name == "Trecho traduzido"
