# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Count

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.blog_fixtures import (
    FEATURED_DESCRIPTIONS,
    FEATURED_TITLES,
    NUM_FEATURED_INDEX_SHOWN,
    NUM_LIST_ARTICLES,
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
        topic=privacy,
        tags=[privacy],
        image=image,
        description=FEATURED_DESCRIPTIONS[0],
        content=get_blog_article_content(image),
    )
    return idx, article


@pytest.fixture
def privacy_articles(minimal_site):
    """Index page + 9 privacy articles with varied titles, descriptions, and display_image values."""
    image, dark_image, _, _ = get_placeholder_images()
    idx = get_blog_index_page()
    privacy = get_blog_topics()["privacy"]
    content = get_blog_article_content(image)

    all_titles = FEATURED_TITLES + REGULAR_TITLES[:4]
    all_descriptions = FEATURED_DESCRIPTIONS + REGULAR_DESCRIPTIONS[:4]

    articles = []
    for i in range(9):
        articles.append(
            _create_blog_article(
                index_page=idx,
                title=all_titles[i],
                slug=f"test-privacy-{i + 1}",
                display_image=(i % 2 == 0),
                topic=privacy,
                tags=[privacy],
                image=image if i < 5 else dark_image,
                description=all_descriptions[i],
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


def test_blog_index_topic_links_point_to_all_route(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")
    all_topics = Tag.objects.filter(blog_articles__isnull=False).annotate(article_count=Count("blog_articles")).order_by("-article_count").distinct()

    all_route_url = index_page.url + index_page.reverse_subpage("all_route")
    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == len(all_topics)

    for index, topic in enumerate(all_topics):
        link = topic_links[index]
        assert topic.name in link.get_text()
        assert link["href"] == f"{all_route_url}?topic={topic.slug}"


def test_blog_index_view_all_topics_link(blog_setup, rf):
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

    heading = hero.find("h2", class_="fl-heading")
    assert heading and first_article.title in heading.get_text()

    topic = hero.find(class_="fl-superheading")
    assert topic and first_article.topic.name in topic.get_text()

    description = hero.find("p", class_="fl-body")
    assert description and BeautifulSoup(first_article.description, "html.parser").get_text() in description

    button = hero.find("a", class_="fl-button")
    assert button and button["href"] == first_article.get_url()


def test_blog_index_renders_three_featured_articles_as_articles_list(blog_setup, rf):
    index_page, articles = blog_setup
    articles = articles[1:4]
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    featured_row = soup.find("div", class_="fl-blog-featured")
    assert featured_row
    articles_list = featured_row.find("div", class_="fl-blog-article-list")
    assert articles_list, "Featured articles 1 - 4 should render as fl-blog-article-list inside the featured row"

    article_items = articles_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(article_items) == len(articles)
    for article, item in zip(articles, article_items):
        heading = item.find("h2", class_="fl-heading")
        assert heading and article.title in heading.get_text()
        link = heading.find("a", class_="fl-link")
        assert link and link["href"] == article.url

        topic = item.find(class_="fl-superheading")
        assert topic and article.topic.name in topic.get_text()

        description = item.find("div", class_="fl-body")
        assert description and BeautifulSoup(article.description, "html.parser").get_text() in description.get_text()

        assert item.find("p", class_="fl-blog-article-date")
        assert item.find("span", class_="fl-tag")


def test_blog_index_renders_remaining_featured_as_illustration_cards(blog_setup, rf):
    # articles[0] is the hero; articles[1:4] are list items; articles[4:8] are illustration cards
    index_page, all_articles = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find("div", class_="fl-blog-featured").find_all("article", class_="fl-illustration-card")
    assert len(cards) == NUM_FEATURED_INDEX_SHOWN - 4  # 8 total - 1 hero - 3 list items = 4 cards

    for fixture_article, card in zip(all_articles[4:8], cards):
        assert "fl-card-expand-link" in card.get("class", [])

        media = card.find("div", class_="fl-card-media")
        assert media and media.find("img")

        topic = card.find("p", class_="fl-superheading")
        assert topic and fixture_article.topic.name in topic.get_text()

        heading = card.find(class_="fl-heading")
        assert heading and fixture_article.title in heading.get_text()
        expand_link = heading.find("a", class_="fl-link-expand")
        assert expand_link and expand_link["href"] == fixture_article.url

        body = card.find("div", class_="fl-body")
        assert body and body.get_text(strip=True)

        assert card.find("span", class_="fl-tag")


def test_blog_index_renders_cards_lists(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards_list_divs = soup.find_all("div", class_="fl-blog-cards-list")
    assert len(cards_list_divs) == 3

    for cards_list in cards_list_divs:
        assert cards_list.find(class_="fl-heading")
        assert cards_list.find("a", class_="fl-blog-cards-list-link")
        cards = cards_list.find_all("article", class_="fl-illustration-card")
        assert cards
        for card in cards:
            assert "fl-card-expand-link" in card.get("class", [])

            media = card.find("div", class_="fl-card-media")
            assert media and media.find("img")

            assert card.find("p", class_="fl-superheading")

            expand_link = card.find("a", class_="fl-link-expand")
            assert expand_link and expand_link["href"]

            body = card.find("div", class_="fl-body")
            assert body and body.get_text(strip=True)

            assert card.find("span", class_="fl-tag")


def test_blog_index_renders_more_articles_heading(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    # Fixture sets more_articles_heading to "Looking for more?"
    headings = [h.get_text(strip=True) for h in soup.find_all(class_="fl-heading")]
    assert any("Looking for more?" in text for text in headings)


def test_blog_index_renders_view_all_button(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    all_url = index_page.url + index_page.reverse_subpage("all_route")
    buttons_div = soup.find("div", class_="fl-buttons")
    assert buttons_div
    view_all = buttons_div.find("a", class_="fl-button")
    assert view_all and view_all["href"] == all_url
    assert index_page.view_all_label in view_all.get_text()


def test_blog_index_cards_list_links_use_label_and_filter(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    all_route_url = index_page.url + index_page.reverse_subpage("all_route")
    cards_list_divs = soup.find_all("div", class_="fl-blog-cards-list")

    # First list: link_label with topic label, link_filter appended to URL
    link = cards_list_divs[0].find("a", class_="fl-blog-cards-list-link")
    assert link.get_text(strip=True) == "View all Privacy"
    assert link["href"] == f"{all_route_url}?topic=privacy"

    # Second list: different topic
    link = cards_list_divs[1].find("a", class_="fl-blog-cards-list-link")
    assert link.get_text(strip=True) == "View all Security"
    assert link["href"] == f"{all_route_url}?topic=security"

    # Third list: no filter — link points to plain all_route URL
    link = cards_list_divs[2].find("a", class_="fl-blog-cards-list-link")
    assert link.get_text(strip=True) == "View all"
    assert link["href"] == all_route_url


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
        assert item.find("div", class_="fl-body")
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


def test_blog_all_list_articles_display_image(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    items = soup.find("div", class_="fl-blog-article-list").find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == 10  # first page

    items_with_image = []
    for item in items:
        has_image_class = "fl-blog-article-list-item-with-image" in item.get("class", [])
        has_img = bool(item.find("div", class_="fl-blog-article-list-item-image"))
        assert has_image_class == has_img, "Image class and image div should be consistent"
        if has_img:
            items_with_image.append(item)

    assert len(items_with_image) > 0, "Some list articles should display an image"


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
    assert article_list
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


def test_blog_article_renders_header_image(single_article, rf):
    _, article = single_article
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    assert header
    image_div = header.find("div", class_="image-variants-display")
    assert image_div and image_div.find("img")


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
        assert item.find("p", class_="fl-blog-article-date")
        assert item.find("span", class_="fl-tag")


def test_blog_article_excludes_self_from_related(privacy_articles, rf):
    index_page, articles = privacy_articles
    article = articles[0]
    request = rf.get(article.get_full_url())
    context = article.get_context(request)
    assert article not in context["related_articles"]


def test_blog_article_related_articles_display_image(privacy_articles, rf):
    index_page, articles = privacy_articles
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    section = soup.find("section", class_="fl-blog-related-articles")
    assert section

    items = section.find_all("article", class_="fl-blog-article-list-item")
    items_with_image = []
    for item in items:
        has_image_class = "fl-blog-article-list-item-with-image" in item.get("class", [])
        has_img = bool(item.find("div", class_="fl-blog-article-list-item-image"))
        assert has_image_class == has_img, "Image class and image div should be consistent"
        if has_img:
            items_with_image.append(item)

    assert len(items_with_image) > 0, "At least one related article should display an image"


# ---------------------------------------------------------------------------
# N+1 query tests
# ---------------------------------------------------------------------------


def test_blog_index_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog index page should fetch all related data in bulk, not per article."""
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    with django_assert_max_num_queries(17):
        index_page.serve(request)


def test_blog_all_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog all-articles page should fetch all related data in bulk, not per article."""
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    with django_assert_max_num_queries(20):
        index_page.all_route(request)
