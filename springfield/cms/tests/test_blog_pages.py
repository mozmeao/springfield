# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.blog_fixtures import (
    FEATURED_DESCRIPTIONS,
    FEATURED_TITLES,
    NUM_FEATURED,
    NUM_FEATURED_INDEX_SHOWN,
    NUM_LIST_ARTICLES,
    PRIVACY_EXTRA_FEATURED_DESCRIPTIONS,
    PRIVACY_EXTRA_FEATURED_TITLES,
    REGULAR_DESCRIPTIONS,
    REGULAR_TITLES,
    _create_blog_article,
    get_blog_article_content,
    get_blog_index_page,
    get_blog_pages,
    get_blog_topics,
)
from springfield.cms.models import BlogArticlePage
from springfield.cms.models.snippets import Tag

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def index_page(minimal_site):
    """Blog index page only — no articles."""
    return get_blog_index_page()


@pytest.fixture
def single_article(minimal_site):
    """Index page + one privacy article with all content block types."""
    image, _, _, _ = get_placeholder_images()
    idx = get_blog_index_page()
    privacy = get_blog_topics()["privacy"]
    article = _create_blog_article(
        index_page=idx,
        title=FEATURED_TITLES[0],
        slug="test-single-article",
        featured=False,
        topic=privacy,
        tags=[privacy],
        image=image,
        description=FEATURED_DESCRIPTIONS[0],
        content=get_blog_article_content(image),
    )
    return idx, article


@pytest.fixture
def privacy_articles(minimal_site):
    """Index page + 4 featured + 5 regular privacy articles.

    4 featured satisfies the >= 4 threshold so the all page shows
    1 hero + 3 cards (not just 1 hero). 5 regular ensures the
    image-on-every-fourth check has enough list articles.
    """
    image, dark_image, _, _ = get_placeholder_images()
    idx = get_blog_index_page()
    privacy = get_blog_topics()["privacy"]
    content = get_blog_article_content(image)

    articles = []
    featured_data = [
        (FEATURED_TITLES[0], FEATURED_DESCRIPTIONS[0]),
        (FEATURED_TITLES[1], FEATURED_DESCRIPTIONS[1]),
        (PRIVACY_EXTRA_FEATURED_TITLES[0], PRIVACY_EXTRA_FEATURED_DESCRIPTIONS[0]),
        (PRIVACY_EXTRA_FEATURED_TITLES[1], PRIVACY_EXTRA_FEATURED_DESCRIPTIONS[1]),
    ]
    for i, (title, description) in enumerate(featured_data):
        articles.append(
            _create_blog_article(
                index_page=idx,
                title=title,
                slug=f"test-privacy-featured-{i + 1}",
                featured=True,
                topic=privacy,
                tags=[privacy],
                image=image,
                description=description,
                content=content,
            )
        )
    for i in range(5):
        articles.append(
            _create_blog_article(
                index_page=idx,
                title=REGULAR_TITLES[i],
                slug=f"test-privacy-regular-{i + 1}",
                featured=False,
                topic=privacy,
                tags=[privacy],
                image=dark_image,
                description=REGULAR_DESCRIPTIONS[i],
                content=content,
            )
        )
    return idx, articles


@pytest.fixture
def blog_setup(minimal_site):
    """Full blog setup (8 featured + 20 regular across 5 topics) for index/pagination tests."""
    articles = get_blog_pages()
    return get_blog_index_page(), articles


# ---------------------------------------------------------------------------
# Blog index page (/)
# ---------------------------------------------------------------------------


def test_blog_index_renders_200(index_page, rf):
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    assert response.status_code == 200


def test_blog_index_renders_headline(index_page, rf):
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and index_page.title in h1.get_text()


def test_blog_index_context_all_topics(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    request = rf.get(index_page.get_full_url())
    context = index_page.get_context(request)

    all_topics = context["all_topics"]
    assert len(all_topics) == len(topics)
    assert all(hasattr(t, "article_count") for t in all_topics)
    counts = [t.article_count for t in all_topics]
    assert counts == sorted(counts, reverse=True)


def test_blog_index_renders_top_5_topics(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == 5


def test_blog_index_topic_links_point_to_all_route(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    all_route_url = index_page.url + index_page.reverse_subpage("all_route")
    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    for link in topic_links:
        href = link["href"]
        assert href.startswith(all_route_url) and "?topic=" in href


def test_blog_index_view_all_articles_link(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topics_route_url = index_page.url + index_page.reverse_subpage("topics_route")
    view_all = soup.find("div", class_="fl-blog-topics-all")
    assert view_all
    link = view_all.find("a")
    assert link and link["href"] == topics_route_url


def test_blog_index_renders_first_featured_as_hero(blog_setup, rf):
    index_page, articles = blog_setup
    first_article = articles[0]  # first article placed in the StreamField
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    hero = soup.find("div", class_="fl-blog-featured-main")
    assert hero, "First featured article should render as fl-blog-featured-main"

    heading = hero.find(["h2", "h3"], class_="fl-heading")
    assert heading and first_article.title in heading.get_text()

    button = hero.find("a", class_="fl-button")
    assert button


def test_blog_index_renders_remaining_featured_as_illustration_cards(blog_setup, rf):
    # articles[0] is the hero; articles[1:4] are list items; articles[4:8] are illustration cards
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find("div", class_="fl-blog-featured").find_all("article", class_="fl-illustration-card")
    assert len(cards) == NUM_FEATURED_INDEX_SHOWN - 4  # 8 total - 1 hero - 3 list items = 4 cards

    for card in cards:
        assert "fl-card-expand-link" in card.get("class", [])
        expand_link = card.find("a", class_="fl-link-expand")
        assert expand_link


def test_blog_index_renders_cards_lists(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards_list_divs = soup.find_all("div", class_="fl-blog-cards-list")
    assert len(cards_list_divs) >= 1


# ---------------------------------------------------------------------------
# Blog all articles page (/all/)
# ---------------------------------------------------------------------------


def test_blog_all_renders_200(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    assert response.status_code == 200


def test_blog_all_renders_all_articles_heading(index_page, rf):
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and "All Articles" in h1.get_text()


def test_blog_all_renders_back_link(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    back_link = soup.find("a", class_="fl-blog-back-link")
    assert back_link
    assert back_link["href"] == index_page.url


def test_blog_all_renders_full_topics_list(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == len(topics)


def test_blog_all_renders_featured_as_media_content(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    mediacontent = soup.find("div", class_="fl-mediacontent")
    assert mediacontent, "First featured article should render as fl-mediacontent"
    assert mediacontent.find("img"), "Media content should contain an image"
    button = mediacontent.find("a", class_="fl-button")
    assert button


def test_blog_all_renders_remaining_featured_as_illustration_cards(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find_all("article", class_="fl-illustration-card")
    # _featured_db_articles returns up to 5 from DB; fixture has 8 featured → 1 hero + 4 cards
    assert len(cards) == NUM_FEATURED - 1

    for card in cards:
        assert "fl-card-expand-link" in card.get("class", [])
        assert card.find("img")
        assert card.find("p", class_="fl-superheading")
        expand_link = card.find("a", class_="fl-link-expand")
        assert expand_link


def test_blog_all_renders_list_articles(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list

    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == 10  # first page

    for item in items:
        assert item.find("p", class_="fl-superheading")
        heading = item.find("h2", class_="fl-heading")
        assert heading and heading.find("a")
        assert item.find("p", class_="fl-blog-article-date")
        assert item.find("span", class_="fl-tag")


def test_blog_all_renders_pagination(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination, "Pagination nav should appear when there are more than 10 list articles"

    prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
    next_button = pagination.find("div", class_="fl-pagination-next").find("a")
    assert prev_button.get("aria-disabled") == "true"
    assert next_button.get("href")

    indicator = pagination.find("span", class_="fl-pagination-indicator")
    assert indicator.get_text(strip=True) == "1/3"


def test_blog_all_pagination_last_page(blog_setup, rf):
    index_page, _ = blog_setup
    num_pages = (NUM_LIST_ARTICLES + 9) // 10
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"page": str(num_pages)})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list
    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == NUM_LIST_ARTICLES - (num_pages - 1) * 10

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination

    prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
    next_button = pagination.find("div", class_="fl-pagination-next").find("a")
    assert prev_button.get("href")
    assert next_button.get("aria-disabled") == "true"

    indicator = pagination.find("span", class_="fl-pagination-indicator")
    assert indicator.get_text(strip=True) == f"{num_pages}/{num_pages}"


def test_blog_all_list_articles_image_on_every_fourth(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    items = soup.find("div", class_="fl-blog-article-list").find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == 10  # first page

    for i, item in enumerate(items):
        has_image_class = "fl-blog-article-list-item-with-image" in item.get("class", [])
        has_img = bool(item.find("div", class_="fl-blog-article-list-item-image"))
        if i % 4 == 3:
            assert has_image_class, f"Item {i} should have image class"
            assert has_img, f"Item {i} should render an image"
        else:
            assert not has_image_class, f"Item {i} should not have image class"
            assert not has_img, f"Item {i} should not render an image"


def test_blog_all_topic_filter_shows_selected_topic(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"topic": "privacy"})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    selected = soup.find("span", class_="fl-blog-selected-topic")
    assert selected and "Privacy" in selected.get_text()


def test_blog_all_topic_filter_selected_topic_has_close_link(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"topic": "privacy"})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    selected = soup.find("span", class_="fl-blog-selected-topic")
    assert selected
    close_link = selected.find("a")
    all_route_url = index_page.url + index_page.reverse_subpage("all_route")
    assert close_link and close_link["href"] == all_route_url


def test_blog_all_unknown_topic_shows_all_articles(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"topic": "nonexistent"})
    response = index_page.all_route(request)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    assert not soup.find("span", class_="fl-blog-selected-topic")


def test_blog_all_topic_filter_filters_articles(privacy_articles, rf):
    index_page, articles = privacy_articles
    topic = Tag.objects.get(slug="privacy")
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"topic": "privacy"})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    if article_list:
        items = article_list.find_all("article", class_="fl-blog-article-list-item")
        for item in items:
            superheading = item.find("p", class_="fl-superheading")
            assert superheading and topic.name in superheading.get_text()


def test_blog_all_topic_filter_count_in_selected_tag(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"topic": "privacy"})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    selected = soup.find("span", class_="fl-blog-selected-topic")
    assert selected
    count_tag = selected.find("span", class_="fl-tag-white")
    assert count_tag and count_tag.get_text(strip=True).isdigit()


def test_blog_all_topic_filter_pagination_urls_include_topic_param(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    # Privacy has 11 regular articles in the full setup, triggering pagination
    request = rf.get(url, {"topic": "privacy"})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    pagination = soup.find("nav", class_="fl-pagination")
    if pagination:
        next_button = pagination.find("div", class_="fl-pagination-next").find("a")
        if next_button and next_button.get("href"):
            assert "topic=privacy" in next_button["href"]


# ---------------------------------------------------------------------------
# Blog article page
# ---------------------------------------------------------------------------


def test_blog_article_renders_200(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    assert response.status_code == 200


def test_blog_article_renders_title_and_topic(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and article.title in h1.get_text()

    superheading = soup.find("p", class_="fl-superheading")
    assert superheading and article.topic.name in superheading.get_text()


def test_blog_article_renders_text_block(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    rich_text_section = soup.find("section", class_="fl-rich-text")
    assert rich_text_section
    assert "Lorem ipsum" in rich_text_section.get_text()


def test_blog_article_renders_media_block(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    rich_text_section = soup.find("section", class_="fl-rich-text")
    assert rich_text_section
    assert rich_text_section.find("img"), "Media block should render an image"


def test_blog_article_renders_code_block(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    code_block = soup.find("div", class_="fl-code-block")
    assert code_block

    pre = code_block.find("pre")
    code = pre.find("code") if pre else None
    assert code
    assert "Hello, Firefox!" in code.get_text()


def test_blog_article_renders_quote_block(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    quote_block = soup.find("figure", class_="fl-quote")
    assert quote_block

    blockquote = quote_block.find("blockquote")
    assert blockquote and "The web is for everyone." in blockquote.get_text()

    figcaption = quote_block.find("figcaption", class_="fl-quote-author")
    assert figcaption and "Mozilla Foundation" in figcaption.get_text()


def test_blog_article_renders_back_link(single_article, rf):
    index_page, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    back_link = soup.find("a", class_="fl-blog-back-link")
    assert back_link
    assert back_link["href"] == index_page.url
    assert back_link.find("span", class_="fl-icon-back")
    assert "Back" in back_link.get_text()


def test_blog_article_renders_related_articles(privacy_articles, rf):
    index_page, articles = privacy_articles
    article = articles[0]
    expected_related = list(
        BlogArticlePage.objects.child_of(index_page)
        .live()
        .public()
        .filter(topic=article.topic)
        .exclude(pk=article.pk)
        .order_by("-first_published_at")[:4]
    )

    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    section = soup.find("section", class_="fl-blog-related-articles")
    assert section

    heading = section.find("h2", class_="fl-heading")
    assert heading and "Related Articles" in heading.get_text()

    items = section.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == len(expected_related)

    for related, item in zip(expected_related, items):
        superheading = item.find("p", class_="fl-superheading")
        assert superheading and related.topic.name in superheading.get_text()
        heading = item.find("h3", class_="fl-heading")
        assert heading and related.title in heading.get_text()
        link = heading.find("a", class_="fl-link")
        assert link and link["href"] == related.url
        body = item.find("div", class_="fl-body")
        assert body and body.get_text(strip=True)


def test_blog_article_excludes_self_from_related(privacy_articles, rf):
    index_page, articles = privacy_articles
    article = articles[0]
    request = rf.get(article.get_full_url())
    context = article.get_context(request)
    assert article not in context["related_articles"]


def test_blog_article_related_articles_image_on_every_fourth(privacy_articles, rf):
    index_page, articles = privacy_articles
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    section = soup.find("section", class_="fl-blog-related-articles")
    assert section

    items = section.find_all("article", class_="fl-blog-article-list-item")
    for i, item in enumerate(items):
        has_image_class = "fl-blog-article-list-item-with-image" in item.get("class", [])
        has_img = bool(item.find("div", class_="fl-blog-article-list-item-image"))
        if i % 4 == 3:
            assert has_image_class, f"Item {i} should have image class"
            assert has_img, f"Item {i} should render an image"
        else:
            assert not has_image_class, f"Item {i} should not have image class"
            assert not has_img, f"Item {i} should not render an image"


# ---------------------------------------------------------------------------
# N+1 query tests
# ---------------------------------------------------------------------------


def test_blog_index_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog index page should fetch all related data in bulk, not per article."""
    idx, _ = blog_setup
    request = rf.get(idx.get_full_url())
    with django_assert_max_num_queries(19):
        idx.serve(request)


def test_blog_all_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog all-articles page should fetch all related data in bulk, not per article."""
    idx, _ = blog_setup
    url = idx.full_url + idx.reverse_subpage("all_route")
    request = rf.get(url)
    with django_assert_max_num_queries(19):
        idx.all_route(request)
