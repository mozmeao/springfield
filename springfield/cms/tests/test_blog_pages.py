# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db.models import Count
from django.http import Http404

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
    image, _, mobile_image, _ = get_placeholder_images()
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
        featured_image=mobile_image,
        description=FEATURED_DESCRIPTIONS[0],
        content=get_blog_article_content(image),
    )
    return idx, article


@pytest.fixture
def privacy_articles(minimal_site):
    """Index page + 4 featured + 5 regular privacy articles.

    4 featured satisfies the >= 4 threshold so the topic page shows
    1 hero + 3 cards (not just 1 hero). 5 regular ensures the
    image-on-every-fourth check has enough list articles.
    """
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
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
                featured_image=mobile_image,
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
                featured_image=dark_mobile_image,
                description=REGULAR_DESCRIPTIONS[i],
                content=content,
            )
        )
    return idx, articles


@pytest.fixture
def blog_setup(minimal_site):
    """Full blog setup (5 featured + 12 regular across 5 topics) for index/pagination tests."""
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
    assert list_articles.paginator.count == NUM_LIST_ARTICLES
    assert list_articles.paginator.num_pages == 3
    assert list_articles.number == 1
    assert len(list_articles.object_list) == 10


def test_blog_index_context_list_articles_page_2(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url(), {"page": "2"})
    context = index_page.get_context(request)

    list_articles = context["list_articles"]
    assert list_articles.number == 2
    assert len(list_articles.object_list) == 10


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


def test_blog_index_renders_top_topics(blog_setup, rf):
    index_page, _ = blog_setup
    base_qs = BlogArticlePage.objects.child_of(index_page).live().public()
    top_topics = list(
        Tag.objects.filter(blog_articles__in=base_qs.values("pk")).annotate(article_count=Count("blog_articles")).order_by("-article_count")[:5]
    )

    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == len(top_topics)

    for topic in top_topics:
        expected_href = index_page.url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": topic.slug})
        link = soup.find("a", class_="fl-blog-topic-link", href=expected_href)
        assert link, f"No link found for topic '{topic.name}'"

        # Topic name is in a separate span outside the tag
        name_span = link.find("span", class_="fl-blog-topic-name")
        assert name_span and topic.name in name_span.get_text()

        # Tag shows the article count
        tag_el = link.find("span", class_="fl-tag")
        assert tag_el and tag_el.get_text(strip=True) == str(topic.article_count)


def test_blog_index_top_topics_have_view_all_link(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    view_all = soup.find("div", class_="fl-blog-topics-all")
    assert view_all
    link = view_all.find("a")
    assert link
    assert link["href"] == index_page.url + index_page.reverse_subpage("topics_route")


def test_blog_index_renders_first_featured_article_as_media_content(blog_setup, rf):
    index_page, _ = blog_setup
    first_featured = BlogArticlePage.objects.child_of(index_page).live().public().filter(featured=True).order_by("-first_published_at").first()
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
    assert heading and first_featured.title in heading.get_text()

    # Has a "Read more" button
    button = mediacontent.find("a", class_="fl-button")
    assert button


def test_blog_index_renders_remaining_featured_as_illustration_cards(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    cards = soup.find_all("article", class_="fl-illustration-card")
    # Index shows 1 hero + up to 4 cards (NUM_FEATURED_INDEX_SHOWN total)
    assert len(cards) == NUM_FEATURED_INDEX_SHOWN - 1

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

    # Page 1: prev button is disabled, next button has an href
    prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
    next_button = pagination.find("div", class_="fl-pagination-next").find("a")
    assert prev_button.get("aria-disabled") == "true"
    assert next_button.get("href")

    # Page indicator shows current/total
    indicator = pagination.find("span", class_="fl-pagination-indicator")
    assert indicator.get_text(strip=True) == "1/3"


def test_blog_index_pagination_last_page(blog_setup, rf):
    index_page, _ = blog_setup
    num_pages = (NUM_LIST_ARTICLES + 9) // 10
    request = rf.get(index_page.get_full_url(), {"page": str(num_pages)})
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list
    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == NUM_LIST_ARTICLES - (num_pages - 1) * 10

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination

    # Last page: prev button has an href, next button is disabled
    prev_button = pagination.find("div", class_="fl-pagination-prev").find("a")
    next_button = pagination.find("div", class_="fl-pagination-next").find("a")
    assert prev_button.get("href")
    assert next_button.get("aria-disabled") == "true"

    # Page indicator shows current/total
    indicator = pagination.find("span", class_="fl-pagination-indicator")
    assert indicator.get_text(strip=True) == f"{num_pages}/{num_pages}"


def test_blog_index_list_articles_image_on_every_fourth(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
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
# Blog topics page (/topics/)
# ---------------------------------------------------------------------------


def test_blog_topics_page_renders_200(single_article, rf):
    index_page, _ = single_article
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    assert response.status_code == 200


def test_blog_topics_page_renders_heading(single_article, rf):
    index_page, _ = single_article
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and "All Topics" in h1.get_text()


def test_blog_topics_page_renders_back_link(index_page, rf):
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    back_link = soup.find("a", class_="fl-blog-back-link")
    assert back_link
    assert back_link["href"] == index_page.url
    assert back_link.find("span", class_="fl-icon-back")
    assert "Back" in back_link.get_text()


def test_blog_topics_page_lists_all_topics_with_name_and_count(blog_setup, rf):
    index_page, _ = blog_setup
    base_qs = BlogArticlePage.objects.child_of(index_page).live().public()
    expected_topics = Tag.objects.filter(blog_articles__in=base_qs.values("pk")).annotate(article_count=Count("blog_articles")).order_by("name")

    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topics_list = soup.find("div", class_="fl-blog-topics-list")
    assert topics_list

    links = topics_list.find_all("a")
    assert len(links) == expected_topics.count()

    for topic in expected_topics:
        # Each topic renders as a large tag containing the name and a nested count tag
        matching = [
            tag
            for tag in topics_list.find_all("span", class_="fl-blog-selected-topic")
            if topic.name in tag.get_text() and str(topic.article_count) in tag.get_text()
        ]
        assert matching, f"No tag found for topic '{topic.name}' with count {topic.article_count}"


def test_blog_topics_page_links_to_topic_detail(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    links = soup.find("div", class_="fl-blog-topics-list").find_all("a")
    expected_hrefs = {index_page.url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": slug}) for slug in topics}
    rendered_hrefs = {link["href"] for link in links}
    assert rendered_hrefs == expected_hrefs


# ---------------------------------------------------------------------------
# Blog topic detail page (/topics/{slug}/)
# ---------------------------------------------------------------------------


def test_blog_topic_detail_renders_200(privacy_articles, rf):
    index_page, _ = privacy_articles
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    assert response.status_code == 200


def test_blog_topic_detail_renders_404_for_unknown_topic(index_page, rf):
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "nonexistent"})
    request = rf.get(url)
    with pytest.raises(Http404):
        index_page.topic_route(request, topic_slug="nonexistent")


def test_blog_topic_detail_renders_selected_topic(privacy_articles, rf):
    index_page, _ = privacy_articles
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    selected = soup.find("span", class_="fl-blog-selected-topic")
    assert selected and "Privacy" in selected.get_text()


def test_blog_topic_detail_selected_topic_links_back_to_index(privacy_articles, rf):
    index_page, _ = privacy_articles
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    selected = soup.find("span", class_="fl-blog-selected-topic")
    assert selected
    close_link = selected.find("a")
    assert close_link and close_link["href"] == index_page.url


def test_blog_topic_detail_renders_featured_as_illustration_cards(privacy_articles, rf):
    index_page, _ = privacy_articles
    topic = Tag.objects.get(slug="privacy")
    featured_articles = list(
        BlogArticlePage.objects.child_of(index_page)
        .live()
        .public()
        .filter(topic=topic, featured=True)
        .prefetch_related("tags")
        .order_by("-first_published_at")[:4]
    )

    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    # The first featured article renders as media-content; the rest become illustration cards
    cards = soup.find_all("article", class_="fl-illustration-card")
    assert len(cards) == len(featured_articles) - 1

    for article, card in zip(featured_articles[1:], cards):
        # Card has expand-link class
        assert "fl-card-expand-link" in card.get("class", [])
        # Card has an image
        assert card.find("img")
        # Card heading contains the article title with an expand link to the article URL
        heading = card.find("h3", class_="fl-heading")
        assert heading and article.title in heading.get_text()
        expand_link = heading.find("a", class_="fl-link-expand")
        assert expand_link and expand_link["href"] == article.url
        # Card body contains article description
        body = card.find("div", class_="fl-card-content").find("div", class_="fl-body")
        assert body
        # Card body contains each tag
        tag_names = {t.name for t in article.tags.all()}
        card_tag_texts = {el.get_text(strip=True) for el in card.find_all("span", class_="fl-tag")}
        assert tag_names <= card_tag_texts


def test_blog_topic_detail_renders_list_articles(privacy_articles, rf):
    index_page, _ = privacy_articles
    topic = Tag.objects.get(slug="privacy")
    base_qs = BlogArticlePage.objects.child_of(index_page).live().public().filter(topic=topic)
    featured_ids = list(base_qs.filter(featured=True).order_by("-first_published_at").values_list("id", flat=True)[:4])
    list_articles = list(base_qs.exclude(id__in=featured_ids).prefetch_related("tags").order_by("-first_published_at"))

    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    article_list = soup.find("div", class_="fl-blog-article-list")
    assert article_list

    items = article_list.find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == len(list_articles)

    for article, item in zip(list_articles, items):
        # Title heading with a link to the article URL
        heading = item.find("h2", class_="fl-heading")
        assert heading and article.title in heading.get_text()
        link = heading.find("a", class_="fl-link")
        assert link and link["href"] == article.url
        # Description body
        assert item.find("div", class_="fl-body")
        # Published date
        assert item.find("p", class_="fl-blog-article-date")
        # Each tag rendered
        tag_names = {t.name for t in article.tags.all()}
        item_tag_texts = {el.get_text(strip=True) for el in item.find_all("span", class_="fl-tag")}
        assert tag_names <= item_tag_texts


def test_blog_topic_detail_list_articles_image_on_every_fourth(privacy_articles, rf):
    index_page, _ = privacy_articles
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    items = soup.find("div", class_="fl-blog-article-list").find_all("article", class_="fl-blog-article-list-item")
    for i, item in enumerate(items):
        has_image_class = "fl-blog-article-list-item-with-image" in item.get("class", [])
        has_img = bool(item.find("div", class_="fl-blog-article-list-item-image"))
        if i % 4 == 3:
            assert has_image_class, f"Item {i} should have image class"
            assert has_img, f"Item {i} should render an image"
        else:
            assert not has_image_class, f"Item {i} should not have image class"
            assert not has_img, f"Item {i} should not render an image"


def test_blog_topic_detail_no_pagination_when_single_page(privacy_articles, rf):
    index_page, _ = privacy_articles
    url = index_page.full_url + index_page.reverse_subpage("topic_route", kwargs={"topic_slug": "privacy"})
    request = rf.get(url)
    response = index_page.topic_route(request, topic_slug="privacy")
    soup = BeautifulSoup(response.content, "html.parser")

    assert not soup.find("nav", class_="fl-pagination")
