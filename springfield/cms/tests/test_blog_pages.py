# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.blog_fixtures import (
    NUM_FEATURED,
    NUM_REGULAR,
    get_blog_index_page,
    get_blog_pages,
    get_blog_topics,
)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def blog_setup(minimal_site):
    """Create the full set of blog articles and return ``(index_page, articles)``."""
    articles = get_blog_pages()
    return get_blog_index_page(), articles


# ---------------------------------------------------------------------------
# Blog index page
# ---------------------------------------------------------------------------


def test_blog_index_context_featured_articles(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    context = index_page.get_context(request)

    assert len(context["featured_articles"]) == NUM_FEATURED
    assert all(a.featured for a in context["featured_articles"])


def test_blog_index_context_list_articles_are_paginated(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    context = index_page.get_context(request)

    list_articles = context["list_articles"]
    assert list_articles.paginator.count == NUM_REGULAR
    assert list_articles.paginator.num_pages == 2
    assert list_articles.number == 1
    assert len(list_articles.object_list) == 10


def test_blog_index_context_list_articles_page_2(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url(), {"page": "2"})
    context = index_page.get_context(request)

    list_articles = context["list_articles"]
    assert list_articles.number == 2
    assert len(list_articles.object_list) == NUM_REGULAR - 10


def test_blog_index_context_top_topics(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    request = rf.get(index_page.get_full_url())
    context = index_page.get_context(request)

    top_topics = context["top_topics"]
    assert len(top_topics) == len(topics)
    # Each topic has an article_count annotation
    assert all(hasattr(t, "article_count") for t in top_topics)
    # Topics are ordered by most articles first
    counts = [t.article_count for t in top_topics]
    assert counts == sorted(counts, reverse=True)


def test_blog_index_renders_200(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    assert response.status_code == 200


def test_blog_index_renders_headline(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and index_page.title in h1.get_text()


def test_blog_index_renders_top_topics(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_section = soup.find("div", class_="fl-blog-topics")
    assert topic_section

    rendered_tags = topic_section.find_all("span", class_="fl-tag")
    assert len(rendered_tags) == len(topics)

    # Each tag contains a topic name and a count in parentheses
    for tag_el in rendered_tags:
        text = tag_el.get_text(strip=True)
        assert "(" in text and ")" in text


def test_blog_index_renders_first_featured_article_as_media_content(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    # First featured article uses the media-content component
    mediacontent = soup.find("div", class_="fl-mediacontent")
    assert mediacontent, "First featured article should render as fl-mediacontent"

    # Has an image in the media slot
    assert mediacontent.find("img"), "Media content should contain an image"

    # Has the topic as superheading
    superheading = mediacontent.find("p", class_="fl-superheading")
    assert superheading

    # Has a heading for the article title (most recently published featured article)
    heading = mediacontent.find(["h2", "h3"], class_="fl-heading")
    assert heading and "Featured Blog Article" in heading.get_text()

    # Has a "Read more" button
    button = mediacontent.find("a", class_="fl-button")
    assert button


def test_blog_index_renders_remaining_featured_as_illustration_cards(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find_all("article", class_="fl-illustration-card")
    # Articles 2-5 render as illustration cards
    assert len(cards) == NUM_FEATURED - 1

    for card in cards:
        # Each card has an expand link
        assert "fl-card-expand-link" in card.get("class", [])
        # Each card has an image
        assert card.find("img")
        # Each card has a topic superheading
        assert card.find("p", class_="fl-superheading")
        # Each card has a heading with the expand link
        expand_link = card.find("a", class_="fl-link-expand")
        assert expand_link


def test_blog_index_renders_list_articles(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list

    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == 10  # first page

    for item in items:
        # Topic superheading
        assert item.find("p", class_="fl-superheading")
        # Title link
        heading = item.find("h2", class_="fl-heading")
        assert heading and heading.find("a")
        # Date
        assert item.find("p", class_="fl-blog-article-date")
        # Tags
        assert item.find("span", class_="fl-tag")


def test_blog_index_renders_pagination(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination, "Pagination nav should appear when there are more than 10 list articles"

    # Page 1 has no Previous link, but has a Next link
    prev_link = pagination.find("a", string=lambda t: t and "Previous" in t)
    next_link = pagination.find("a", string=lambda t: t and "Next" in t)
    assert prev_link is None
    assert next_link


def test_blog_index_pagination_page_2(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url(), {"page": "2"})
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list
    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == NUM_REGULAR - 10

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination
    prev_link = pagination.find("a", string=lambda t: t and "Previous" in t)
    next_link = pagination.find("a", string=lambda t: t and "Next" in t)
    assert prev_link
    assert next_link is None


# ---------------------------------------------------------------------------
# Blog article page
# ---------------------------------------------------------------------------


def test_blog_article_renders_200(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    assert response.status_code == 200


def test_blog_article_renders_title_and_topic(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and article.title in h1.get_text()

    superheading = soup.find("p", class_="fl-superheading")
    assert superheading and article.topic.name in superheading.get_text()


def test_blog_article_renders_text_block(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    rich_text_section = soup.find("section", class_="fl-rich-text")
    assert rich_text_section
    assert "Lorem ipsum" in rich_text_section.get_text()


def test_blog_article_renders_media_block(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    rich_text_section = soup.find("section", class_="fl-rich-text")
    assert rich_text_section
    assert rich_text_section.find("img"), "Media block should render an image"


def test_blog_article_renders_code_block(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    code_block = soup.find("div", class_="fl-code-block")
    assert code_block

    pre = code_block.find("pre")
    code = pre.find("code") if pre else None
    assert code
    assert "Hello, Firefox!" in code.get_text()


def test_blog_article_renders_quote_block(blog_setup, rf):
    _, articles = blog_setup
    article = articles[0]
    request = rf.get(article.get_full_url())
    response = article.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    quote_block = soup.find("figure", class_="fl-quote")
    assert quote_block

    blockquote = quote_block.find("blockquote")
    assert blockquote and "The web is for everyone." in blockquote.get_text()

    figcaption = quote_block.find("figcaption", class_="fl-quote-author")
    assert figcaption and "Mozilla Foundation" in figcaption.get_text()
