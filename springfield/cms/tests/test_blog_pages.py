# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from datetime import UTC, date, datetime

from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils.translation import override

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, Site
from wagtail.rich_text import RichText
from wagtail_localize.fields import TranslatableField, get_translatable_fields
from wagtail_localize.operations import translate_object

from springfield.cms.blocks import BlogArticleBlock
from springfield.cms.fixtures.base_fixtures import get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.blog_fixtures import (
    FEATURED_DESCRIPTIONS,
    FEATURED_TITLES,
    NUM_LIST_ARTICLES,
    REGULAR_DESCRIPTIONS,
    REGULAR_TITLES,
    blog_article_block,
    create_blog_article,
    featured_topics_stream,
    get_blog_article_content,
    get_blog_authors,
    get_blog_index_page,
    get_blog_pages,
    get_blog_tags,
    get_blog_topics,
)
from springfield.cms.models import BlogArticleAuthor, BlogArticlePage, BlogTopicPage
from springfield.cms.models.images import SpringfieldImage
from springfield.cms.models.pages import ARTICLES_PER_PAGE, MAX_HEADER_TOPICS, BlogIndexPage, HeroStyle
from springfield.cms.models.snippets import BlogTag, BlogTopic

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def blog_index(minimal_site):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = BlogIndexPage(
        title="Blog",
        slug="test-unit-blog",
        locale=Locale.objects.get(language_code="en-US"),
    )
    root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def blog_topic(blog_index):
    return BlogTopic.objects.create(name="Privacy", slug="test-unit-privacy", locale=blog_index.locale)


@pytest.fixture
def blog_tag(blog_index):
    return BlogTag.objects.create(name="VPN", slug="test-unit-vpn", locale=blog_index.locale)


@pytest.fixture
def excluded_index(blog_index, blog_topic, blog_tag):
    """Index page excluding one topic and one tag."""
    blog_index.feed_exclusions = [
        {"type": "topic", "value": blog_topic.pk, "id": "fx000001-0000-0000-0000-000000000001"},
        {"type": "tag", "value": blog_tag.pk, "id": "fx000002-0000-0000-0000-000000000002"},
    ]
    blog_index.save()
    return blog_index


@pytest.fixture
def make_article(blog_index, blog_topic):
    slug_numbers = itertools.count(1)

    def make_article(**fields):
        fields.setdefault("topic", blog_topic)
        if not fields.get("image"):
            fields.setdefault("hero_style", HeroStyle.TEXT_ONLY)
        article = BlogArticlePage(
            title=fields.pop("title", "Test article"),
            slug=f"test-unit-article-{next(slug_numbers)}",
            locale=blog_index.locale,
            **fields,
        )
        blog_index.add_child(instance=article)
        return article

    return make_article


@pytest.fixture
def tagged_articles(make_article, blog_tag):
    """One article carrying blog_tag, one without it."""
    tagged = make_article(title="Tagged article")
    tagged.tags.add(blog_tag)
    tagged.save()
    return tagged, make_article(title="Untagged article")


@pytest.fixture
def articles_for_exclusion(blog_index, blog_topic, blog_tag, make_article):
    """Three articles: one in the excluded topic, one carrying the excluded tag, and one
    clear of both."""
    other_topic = BlogTopic.objects.create(name="Security", slug="test-unit-security", locale=blog_index.locale)
    in_excluded_topic = make_article(title="Excluded topic")
    with_excluded_tag = make_article(title="Excluded tag", topic=other_topic)
    with_excluded_tag.tags.add(blog_tag)
    with_excluded_tag.save()
    clear = make_article(title="Not excluded", topic=other_topic)
    return in_excluded_topic, with_excluded_tag, clear


@pytest.fixture
def paginated_tagged_topic(blog_index, blog_topic, blog_tag, make_article):
    """One topic and tag carrying enough articles to fill two pages."""
    for position in range(ARTICLES_PER_PAGE + 1):
        article = make_article(title=f"Tagged article {position}")
        article.tags.add(blog_tag)
        article.save()
    return blog_index, blog_topic, blog_tag


@pytest.fixture
def stub_images(db):
    """Two images with no files — never rendered. Use bulk_create since
    SpringfieldImage.save() pre-generates renditions, which needs a real image file."""
    return tuple(
        SpringfieldImage.objects.bulk_create(
            [
                SpringfieldImage(title="Featured", width=800, height=450),
                SpringfieldImage(title="Listing", width=800, height=450),
            ]
        )
    )


@pytest.fixture
def real_images(db):
    """Two image rows with real files, for tests that render an `<img>`."""
    image, dark_image, _, _ = get_placeholder_images()
    return image, dark_image


@pytest.fixture
def bare_article(make_article):
    return make_article(title="Bare article")


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
    privacy_tag = get_blog_tags()["privacy"]
    article = create_blog_article(
        index_page=idx,
        title=FEATURED_TITLES[0],
        slug="test-single-article",
        topic=privacy,
        tags=[privacy_tag],
        image=image,
        description=FEATURED_DESCRIPTIONS[0],
        content=get_blog_article_content(image),
    )
    return idx, article


@pytest.fixture
def privacy_articles(minimal_site):
    """Index page + 9 privacy articles with varied titles, descriptions and images."""
    image, dark_image, _, _ = get_placeholder_images()
    idx = get_blog_index_page()
    privacy = get_blog_topics()["privacy"]
    privacy_tag = get_blog_tags()["privacy"]
    content = get_blog_article_content(image)

    all_titles = FEATURED_TITLES + REGULAR_TITLES[:4]
    all_descriptions = FEATURED_DESCRIPTIONS + REGULAR_DESCRIPTIONS[:4]

    articles = []
    for i in range(9):
        articles.append(
            create_blog_article(
                index_page=idx,
                title=all_titles[i],
                slug=f"test-privacy-{i + 1}",
                topic=privacy,
                tags=[privacy_tag],
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


@pytest.fixture
def index_page_and_topics(minimal_site):
    """Index page + topic snippets, no articles."""
    return get_blog_index_page(), get_blog_topics()


@pytest.fixture
def topics_with_article_counts(minimal_site):
    """Index page + three topics with 3, 2 and 1 published articles, for the
    count-based header fallback."""
    index_page = get_blog_index_page()
    topics = get_blog_topics()
    article_counts = {"privacy": 3, "security": 2, "tips": 1}
    for slug, count in article_counts.items():
        for number in range(count):
            create_blog_article(
                index_page=index_page,
                title=f"{slug} article {number}",
                slug=f"test-{slug}-{number}",
                topic=topics[slug],
                tags=[],
                image=None,
                description="",
                content=[],
            )
    return index_page, topics


@pytest.fixture
def more_topics_than_the_header_shows(minimal_site):
    """Index page + one more topic than the header can show, each with one article."""
    index_page = get_blog_index_page()
    for number in range(MAX_HEADER_TOPICS + 1):
        topic = BlogTopic.objects.create(name=f"Topic {number}", slug=f"topic-{number}", locale=index_page.locale)
        create_blog_article(
            index_page=index_page,
            title=f"Article {number}",
            slug=f"test-article-{number}",
            topic=topic,
            tags=[],
            image=None,
            description="",
            content=[],
        )
    return index_page


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


def test_blog_index_topic_links_point_to_topic_route(blog_setup, rf):
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    response = index_page.serve(request)
    soup = BeautifulSoup(response.content, "html.parser")
    header_topics = index_page.get_header_topics()

    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == len(header_topics)

    for index, topic in enumerate(header_topics):
        link = topic_links[index]
        assert topic.name in link.get_text()
        assert link["href"] == index_page.url + index_page.reverse_subpage("topic_route", args=[topic.slug])


def test_blog_index_header_topics_use_featured_topics_in_order(index_page_and_topics):
    index_page, topics = index_page_and_topics
    index_page.featured_topics = featured_topics_stream([topics["tips"], topics["open-source"]])
    index_page.save_revision().publish()

    assert [topic.slug for topic in index_page.get_header_topics()] == ["tips", "open-source"]


def test_blog_index_header_topics_fall_back_to_topics_with_most_articles(topics_with_article_counts):
    index_page, _ = topics_with_article_counts

    header_topics = index_page.get_header_topics()

    assert [topic.slug for topic in header_topics] == ["privacy", "security", "tips"]
    assert [topic.article_count for topic in header_topics] == [3, 2, 1]


def test_blog_index_header_topics_fallback_stops_at_the_maximum(more_topics_than_the_header_shows):
    """The count-based fallback shows no more topics than the featured field allows."""
    index_page = more_topics_than_the_header_shows

    assert BlogTopic.objects.count() > MAX_HEADER_TOPICS
    assert len(index_page.get_header_topics()) == MAX_HEADER_TOPICS


def test_blog_index_header_topics_skip_unpublished_featured_topic(index_page_and_topics):
    index_page, topics = index_page_and_topics
    unpublished_topic = topics["security"]
    unpublished_topic.live = False
    unpublished_topic.save()
    index_page.featured_topics = featured_topics_stream([topics["tips"], unpublished_topic])
    index_page.save_revision().publish()

    assert [topic.slug for topic in index_page.get_header_topics()] == ["tips"]


def test_blog_index_header_topics_use_the_page_locale(index_page_and_topics):
    """A translated index page shows the published topic translations for its own
    locale. Translating a page creates the topic translations as drafts, so only
    the published ones reach the header."""
    index_page, topics = index_page_and_topics
    index_page.featured_topics = featured_topics_stream([topics["tips"], topics["security"]])
    index_page.save_revision().publish()

    fr_locale = Locale.objects.get_or_create(language_code="fr")[0]
    translate_object(index_page, [fr_locale])
    fr_tips = BlogTopic.objects.get(translation_key=topics["tips"].translation_key, locale=fr_locale)
    fr_tips.name = "Astuces"
    fr_tips.save_revision().publish()

    fr_index_page = index_page.get_translation(fr_locale)
    header_topics = fr_index_page.get_header_topics()

    assert [topic.name for topic in header_topics] == ["Astuces"]
    assert [topic.locale_id for topic in header_topics] == [fr_locale.pk]


def test_all_context_tag_filter_keeps_only_articles_with_the_tag(blog_index, blog_tag, tagged_articles, rf):
    tagged, _ = tagged_articles

    context = blog_index.get_all_context(rf.get("/", {"tag": blog_tag.slug}))

    assert list(context["list_articles"]) == [tagged]
    assert context["tag"] == blog_tag


def test_all_context_unknown_tag_is_ignored(blog_index, tagged_articles, rf):
    tagged, untagged = tagged_articles

    context = blog_index.get_all_context(rf.get("/", {"tag": "nonexistent"}))

    assert set(context["list_articles"]) == {tagged, untagged}
    assert context["tag"] is None


def test_all_context_topic_and_tag_filters_combine(blog_index, blog_topic, blog_tag, make_article, rf):
    other_topic = BlogTopic.objects.create(name="Security", slug="test-unit-security", locale=blog_index.locale)
    both = make_article(title="Right topic and tag")
    both.tags.add(blog_tag)
    both.save()
    wrong_topic = make_article(title="Wrong topic", topic=other_topic)
    wrong_topic.tags.add(blog_tag)
    wrong_topic.save()
    make_article(title="Right topic, no tag")

    context = blog_index.get_all_context(rf.get("/", {"topic": blog_topic.slug, "tag": blog_tag.slug}))

    assert list(context["list_articles"]) == [both]


def test_topic_context_tag_filter_narrows_within_the_topic(blog_index, blog_topic, blog_tag, tagged_articles, rf):
    tagged, _ = tagged_articles

    context = blog_index.get_topic_context(rf.get("/", {"tag": blog_tag.slug}), blog_topic)

    assert list(context["list_articles"]) == [tagged]


def test_feed_exclusions_are_empty_by_default(blog_index):
    exclusions = blog_index.get_feed_exclusions()

    assert exclusions.topic_keys == set()
    assert exclusions.tag_keys == set()


def test_feed_exclusions_report_chosen_topics_and_tags(excluded_index, blog_topic, blog_tag):
    exclusions = excluded_index.get_feed_exclusions()

    assert exclusions.topic_keys == {blog_topic.translation_key}
    assert exclusions.tag_keys == {blog_tag.translation_key}


def test_all_context_drops_excluded_topics_and_tags(excluded_index, articles_for_exclusion, rf):
    _, _, clear = articles_for_exclusion

    context = excluded_index.get_all_context(rf.get("/"))

    assert list(context["list_articles"]) == [clear]


def test_all_context_topic_filter_exempts_that_topic(excluded_index, articles_for_exclusion, blog_topic, rf):
    """?topic=X means the reader asked for X, so X's exclusion is spared."""
    in_excluded_topic, _, _ = articles_for_exclusion

    context = excluded_index.get_all_context(rf.get("/", {"topic": blog_topic.slug}))

    assert list(context["list_articles"]) == [in_excluded_topic]


def test_all_context_tag_filter_exempts_that_tag(excluded_index, articles_for_exclusion, blog_tag, rf):
    _, with_excluded_tag, _ = articles_for_exclusion

    context = excluded_index.get_all_context(rf.get("/", {"tag": blog_tag.slug}))

    assert list(context["list_articles"]) == [with_excluded_tag]


def test_all_context_exempts_only_what_was_named(excluded_index, articles_for_exclusion, blog_topic, blog_tag, make_article, rf):
    """?tag=Y spares tag Y and nothing else — an article in an excluded topic stays
    hidden even when it also carries Y."""
    both = make_article(title="Excluded topic and tag", topic=blog_topic)
    both.tags.add(blog_tag)
    both.save()
    _, with_excluded_tag, _ = articles_for_exclusion

    context = excluded_index.get_all_context(rf.get("/", {"tag": blog_tag.slug}))

    assert list(context["list_articles"]) == [with_excluded_tag]


def test_topic_context_shows_its_own_excluded_topic(excluded_index, articles_for_exclusion, blog_topic, rf):
    """Applying the topic exclusion here would leave the page empty."""
    in_excluded_topic, _, _ = articles_for_exclusion

    context = excluded_index.get_topic_context(rf.get("/"), blog_topic)

    assert list(context["list_articles"]) == [in_excluded_topic]


def test_topic_context_still_drops_excluded_tags(excluded_index, articles_for_exclusion, rf):
    """The topic exemption spares one exclusion, not all of them."""
    _, with_excluded_tag, clear = articles_for_exclusion

    context = excluded_index.get_topic_context(rf.get("/"), with_excluded_tag.topic)

    assert list(context["list_articles"]) == [clear]


def test_blog_index_featured_section_holds_at_most_four():
    """One hero plus up to three list items."""
    stream_block = BlogIndexPage._meta.get_field("featured_articles").stream_block

    assert stream_block.meta.max_num == 4


def test_topic_slug_is_synchronized_rather_than_translated():
    """Topic slugs stay locale-independent, so topics/<slug>/ resolves to the same topic
    in every language."""
    translatable_names = {field.field_name for field in get_translatable_fields(BlogTopic) if isinstance(field, TranslatableField)}

    assert translatable_names == {"name"}


def test_blog_index_featured_topics_skip_the_article_count_query(index_page_and_topics, django_assert_num_queries):
    """With featured topics set, the header costs only the chooser lookup and the
    localized topic query — the article count aggregation never runs."""
    index_page, topics = index_page_and_topics
    index_page.featured_topics = featured_topics_stream([topics["tips"], topics["security"]])
    index_page.save_revision().publish()

    page = BlogIndexPage.objects.get(pk=index_page.pk)
    with django_assert_num_queries(2):
        page.get_header_topics()


def test_blog_index_edit_handler_has_a_blog_options_tab():
    edit_handler = BlogIndexPage.get_edit_handler()

    assert [str(child.heading) for child in edit_handler.children] == ["Content", "Blog Options", "Promote", "Settings"]
    assert "featured_topics" in edit_handler.get_form_class().base_fields


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
        cards = cards_list.find_all("article", class_="fl-card")
        assert cards
        for card in cards:
            assert "fl-card-expand-link" in card.get("class", [])

            media = card.find("div", class_="fl-card-top-media")
            assert media and media.find("img")

            assert card.find("p", class_="fl-superheading")

            expand_link = card.find("a", class_="fl-link-expand")
            assert expand_link and expand_link["href"]

            body = card.find("div", class_="fl-body")
            assert body and body.get_text(strip=True)


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

    num_pages = (NUM_LIST_ARTICLES + 9) // 10
    indicator = pagination.find("span", class_="fl-pagination-indicator")
    assert indicator.get_text(strip=True) == f"1/{num_pages}"


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
    topic = BlogTopic.objects.get(slug="privacy")
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


def test_blog_all_tag_filter_pagination_urls_include_tag_param(blog_setup, rf):
    index_page, _ = blog_setup
    tag = get_blog_tags()["privacy"]
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url, {"tag": tag.slug})
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    pagination = soup.find("nav", class_="fl-pagination")
    assert pagination, "The privacy tag has enough articles to paginate"
    next_button = pagination.find("div", class_="fl-pagination-next").find("a")
    assert f"tag={tag.slug}" in next_button["href"]


def test_blog_topic_tag_filter_pagination_urls_include_tag_param(paginated_tagged_topic, rf):
    index_page, topic, tag = paginated_tagged_topic
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=[topic.slug])
    response = index_page.topic_route(rf.get(url, {"tag": tag.slug}), topic.slug)
    soup = BeautifulSoup(response.content, "html.parser")

    next_button = soup.find("nav", class_="fl-pagination").find("div", class_="fl-pagination-next").find("a")
    assert f"tag={tag.slug}" in next_button["href"]


def test_blog_all_renders_view_all_topics_link(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topics_route_url = index_page.url + index_page.reverse_subpage("topics_route")
    topics_all_div = soup.find("div", class_="fl-blog-topics-all")
    assert topics_all_div
    link = topics_all_div.find("a", class_="fl-link")
    assert link and link["href"] == topics_route_url


def test_blog_all_topic_links_are_tag_elements(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    response = index_page.all_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_links = soup.find_all("a", class_="fl-blog-topic-link")
    assert len(topic_links) == len(topics)
    for link in topic_links:
        assert "fl-tag" in link.get("class", [])


# ---------------------------------------------------------------------------
# Blog topics page (/topics/)
# ---------------------------------------------------------------------------


def test_blog_topics_renders_200(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    assert response.status_code == 200


def test_blog_topics_renders_back_link(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    back_link = soup.find("a", class_="fl-blog-back-link")
    assert back_link
    assert back_link["href"] == index_page.url


def test_blog_topics_renders_heading(blog_setup, rf):
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    h1 = soup.find("h1", class_="fl-heading")
    assert h1 and "All Topics" in h1.get_text()


def test_blog_topics_renders_topic_links(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    topic_links = [a for a in soup.find_all("a", class_="fl-tag") if "is-large" in a.get("class", [])]
    assert len(topic_links) == len(topics)
    for link in topic_links:
        assert link["href"].startswith(index_page.url + "topics/")
        assert link["href"].endswith("/")


def test_blog_topics_shows_article_count_badge(blog_setup, rf):
    index_page, _ = blog_setup
    topics = get_blog_topics()
    url = index_page.full_url + index_page.reverse_subpage("topics_route")
    request = rf.get(url)
    response = index_page.topics_route(request)
    soup = BeautifulSoup(response.content, "html.parser")

    badges = soup.find_all("span", class_="fl-tag-light-purple")
    assert len(badges) == len(topics), "Each topic link should show an article count badge, visible on hover."
    for badge in badges:
        assert badge.get_text(strip=True).isdigit()


# ---------------------------------------------------------------------------
# Blog topic page (/topics/<slug>/)
# ---------------------------------------------------------------------------


@pytest.fixture
def topic_blog(minimal_site):
    """Index page with 11 Privacy articles — enough to paginate — and 2 Security ones."""
    index_page = get_blog_index_page()
    topics = get_blog_topics()

    articles = {"privacy": [], "security": []}
    for topic_slug, count in (("privacy", 11), ("security", 2)):
        for number in range(1, count + 1):
            articles[topic_slug].append(
                create_blog_article(
                    index_page=index_page,
                    title=f"{topics[topic_slug].name} article {number}",
                    slug=f"test-{topic_slug}-{number}",
                    topic=topics[topic_slug],
                    tags=[],
                    image=None,
                    description=REGULAR_DESCRIPTIONS[number % len(REGULAR_DESCRIPTIONS)],
                    content=[],
                )
            )
    return index_page, articles


def test_blog_topic_renders(topic_blog, rf):
    """The plain variant renders the topic name, the back link, and the article list."""
    index_page, _ = topic_blog
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["security"])
    response = index_page.topic_route(rf.get(url), "security")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    heading = soup.find("h1")
    assert heading and "Security" in heading.get_text()

    back_link = soup.find("a", class_="fl-blog-back-link")
    assert back_link and back_link["href"] == index_page.url

    items = soup.find("div", class_="fl-blog-article-list").find_all("article", class_="fl-blog-article-list-item")
    assert len(items) == 2


def test_blog_topic_unknown_slug_404s(topic_blog, rf):
    index_page, _ = topic_blog
    with pytest.raises(Http404):
        index_page.topic_route(rf.get(index_page.url + "topics/nonexistent/"), "nonexistent")


def test_blog_topic_context_holds_only_that_topics_articles(topic_blog, rf):
    index_page, articles = topic_blog
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["security"])
    topic = BlogTopic.objects.get(slug="security", locale=index_page.locale)

    context = index_page.get_topic_context(rf.get(url), topic)

    assert {article.pk for article in context["list_articles"]} == {article.pk for article in articles["security"]}


def test_blog_topic_context_orders_articles_most_recent_first(topic_blog, rf):
    index_page, _ = topic_blog
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["privacy"])
    topic = BlogTopic.objects.get(slug="privacy", locale=index_page.locale)

    context = index_page.get_topic_context(rf.get(url), topic)

    dates = [article.first_published_at for article in context["list_articles"]]
    assert dates == sorted(dates, reverse=True)


def test_blog_topic_context_paginates(topic_blog, rf):
    index_page, _ = topic_blog
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["privacy"])
    topic = BlogTopic.objects.get(slug="privacy", locale=index_page.locale)

    first_page = index_page.get_topic_context(rf.get(url), topic)["list_articles"]
    assert first_page.paginator.count == 11
    assert first_page.paginator.num_pages == 2
    assert len(first_page.object_list) == 10

    second_page = index_page.get_topic_context(rf.get(url, {"page": "2"}), topic)["list_articles"]
    assert len(second_page.object_list) == 1


def test_blog_topic_with_no_articles_renders_empty(index_page, rf):
    BlogTopic.objects.create(name="Lonely", slug="lonely", locale=index_page.locale)
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["lonely"])

    response = index_page.topic_route(rf.get(url), "lonely")

    assert response.status_code == 200
    assert not BeautifulSoup(response.content, "html.parser").find("article", class_="fl-blog-article-list-item")


@pytest.fixture
def privacy_topic_page(index_page):
    """A BlogTopicPage for Privacy under an index page that has no articles."""
    topic = get_blog_topics()["privacy"]
    topic_page = get_or_create_page(
        BlogTopicPage,
        slug="test-privacy-topic-page",
        parent=index_page,
        defaults={"title": "Privacy", "topic": topic},
    )
    topic_page.save_revision().publish()
    return index_page, topic_page, topic


def test_blog_topic_page_url_uses_topic_route(privacy_topic_page):
    index_page, topic_page, _ = privacy_topic_page
    assert topic_page.url == index_page.url + index_page.reverse_subpage("topic_route", args=["privacy"])


def test_blog_topic_page_not_servable_at_its_own_path(privacy_topic_page, rf):
    _, topic_page, _ = privacy_topic_page
    with pytest.raises(Http404):
        topic_page.route(rf.get("/"), [])


def test_blog_topic_page_rejects_a_second_page_for_the_same_topic(privacy_topic_page):
    index_page, topic_page, topic = privacy_topic_page

    duplicate = BlogTopicPage(title="Another Privacy", slug="another-privacy", topic=topic, locale=index_page.locale)

    with pytest.raises(ValidationError) as exc_info:
        duplicate.clean()
    assert "topic" in exc_info.value.message_dict
    assert topic_page.title in str(exc_info.value)


@pytest.fixture
def curated_topic_page(topic_blog):
    """A BlogTopicPage for Privacy featuring that topic's 4 most recent articles."""
    index_page, _ = topic_blog
    featured = list(BlogArticlePage.objects.child_of(index_page).filter(topic__slug="privacy").order_by("-first_published_at")[:4])
    topic_page = get_or_create_page(
        BlogTopicPage,
        slug="test-privacy-curated",
        parent=index_page,
        defaults={"title": "Privacy", "topic": get_blog_topics()["privacy"]},
    )
    topic_page.page_heading = [
        {
            "type": "heading",
            "value": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="tph00001">Curated Privacy</p>',
                "subheading_text": "",
            },
            "id": "tph00001-0000-0000-0000-000000000001",
        }
    ]
    topic_page.featured_articles = [
        blog_article_block(article, f"tpf00000-0000-0000-0000-{number:012d}") for number, article in enumerate(featured, start=1)
    ]
    topic_page.save_revision().publish()
    return index_page, topic_page, featured


def test_blog_topic_renders_curated_header(curated_topic_page, rf):
    """With a BlogTopicPage the route renders its heading and featured articles in place
    of the plain topic name, and still renders the automatic list below."""
    index_page, _, featured = curated_topic_page
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["privacy"])

    response = index_page.topic_route(rf.get(url), "privacy")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    heading = soup.find("h1")
    assert heading and "Curated Privacy" in heading.get_text()

    featured_block = soup.find("div", class_="fl-blog-featured")
    assert featured_block
    assert featured[0].title in featured_block.get_text()

    assert soup.select_one(".fl-section-container > .fl-blog-article-list")


def test_blog_topic_context_excludes_featured_articles(curated_topic_page, rf):
    index_page, topic_page, featured = curated_topic_page
    url = index_page.full_url + index_page.reverse_subpage("topic_route", args=["privacy"])

    context = topic_page.get_context(rf.get(url))

    listed = context["list_articles"]
    assert {article.pk for article in listed}.isdisjoint({article.pk for article in featured})
    assert listed.paginator.count == 7, "11 privacy articles minus the 4 featured"
    assert listed.paginator.num_pages == 1


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


def test_blog_article_renders_a_single_author_byline(single_article, rf):
    _, article = single_article
    authors = get_blog_authors()
    article.article_authors.set([BlogArticleAuthor(author=authors["ada-lovelace"])])
    article.save_revision().publish()

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    byline = soup.select_one(".fl-blog-byline")
    assert byline
    assert byline.get_text(strip=True) == "By Ada Lovelace"


def test_blog_article_renders_a_multiple_author_byline(single_article, rf):
    _, article = single_article
    authors = get_blog_authors()
    article.article_authors.set(
        [
            BlogArticleAuthor(author=authors["ada-lovelace"]),
            BlogArticleAuthor(author=authors["grace-hopper"]),
            BlogArticleAuthor(author=authors["alan-turing"]),
        ]
    )
    article.save_revision().publish()

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    byline = soup.select_one(".fl-blog-byline")
    assert byline
    assert byline.get_text(strip=True) == "By Ada Lovelace, Grace Hopper, and Alan Turing"


def test_blog_article_without_authors_renders_no_byline(single_article, rf):
    _, article = single_article

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    assert soup.select_one(".fl-blog-byline") is None


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


def test_blog_article_related_articles_render_their_image(privacy_articles, rf):
    _, articles = privacy_articles
    article = articles[0]
    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    items = soup.find("section", class_="fl-blog-related-articles").find_all("article", class_="fl-blog-article-list-item")
    assert items

    for item in items:
        assert "fl-blog-article-list-item-with-image" in item.get("class", [])
        assert item.find("div", class_="fl-blog-article-list-item-image").find("img")


# ---------------------------------------------------------------------------
# N+1 query tests
# ---------------------------------------------------------------------------


def test_blog_index_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog index page should fetch all related data in bulk, not per article.

    The ceiling includes one query from AbstractSpringfieldCMSPage.get_breadcrumb_ancestors
    calling `.public()`, which does a PageViewRestriction lookup per render — required to
    keep view-restricted ancestors out of the BreadcrumbList JSON-LD.

    It also includes ~5 constant (not per-article) queries from custom-navigation
    resolution that runs on every page render. The count is pinned as flat (not
    per-article) by test_blog_all_query_count_does_not_grow_with_articles.
    # TODO (WT-1468): revisit whether to cache the resolved page nav / default snippet
    # to drop the ceiling back down.
    """
    index_page, _ = blog_setup
    request = rf.get(index_page.get_full_url())
    with django_assert_max_num_queries(27):
        index_page.serve(request)


def test_blog_all_no_n_plus_one_queries(blog_setup, rf, django_assert_max_num_queries):
    """Blog all-articles page should fetch all related data in bulk, not per article.

    As with the index page, the ceiling includes ~5 constant (not per-article)
    queries from custom-navigation resolution on every render: get_navigation()'s
    ancestor walk plus the get_default_navigation() tag's default-snippet lookup.
    # TODO (WT-1468): revisit caching the resolved page nav / default snippet
    # to drop the ceiling back down.
    """
    index_page, _ = blog_setup
    url = index_page.full_url + index_page.reverse_subpage("all_route")
    request = rf.get(url)
    with django_assert_max_num_queries(32):
        index_page.all_route(request)


def test_get_tags_skips_tags_with_no_live_localization(single_article):
    _, article = single_article
    tag = article.tags.first()
    tag.live = False
    tag.save()

    article = BlogArticlePage.objects.get(pk=article.pk)

    assert article.get_tags() == []


def test_all_page_renders_localized_tag_names(privacy_articles, rf):
    index_page, _ = privacy_articles
    fr_locale, _ = Locale.objects.get_or_create(language_code="fr")
    en_tag = BlogTag.objects.get(slug="privacy", locale=Locale.get_default())
    BlogTag.objects.create(
        name="Confidentialité",
        slug="privacy",
        locale=fr_locale,
        translation_key=en_tag.translation_key,
    )

    url = index_page.full_url + index_page.reverse_subpage("all_route")
    with override("fr"):
        response = index_page.all_route(rf.get(url))

    soup = BeautifulSoup(response.content, "html.parser")
    tag_labels = {element.get_text(strip=True) for element in soup.select(".fl-blog-article-list-item .fl-tag")}
    assert "Confidentialité" in tag_labels
    assert "Privacy" not in tag_labels


# ---------------------------------------------------------------------------
# Hero style, dates and listing image
# ---------------------------------------------------------------------------


def test_blog_article_listing_image_falls_back_to_the_featured_image(bare_article, stub_images):
    featured_image, _ = stub_images
    bare_article.image = featured_image

    assert bare_article.listing_image is None
    assert bare_article.get_listing_image() == featured_image


def test_blog_article_listing_image_replaces_the_featured_image(bare_article, stub_images):
    featured_image, listing_image = stub_images
    bare_article.image = featured_image
    bare_article.listing_image = listing_image

    assert bare_article.get_listing_image() == listing_image


def test_blog_article_listing_image_variants_come_from_the_featured_image(bare_article, stub_images):
    featured_image, dark_image = stub_images
    bare_article.image = featured_image
    bare_article.image_dark_mode = dark_image

    variants = bare_article.get_listing_image_variants()

    assert variants.dark_mode == dark_image
    assert variants.mobile is None
    assert variants.dark_mode_mobile is None


def test_blog_article_listing_image_suppresses_the_featured_image_variants(bare_article, stub_images):
    featured_image, listing_image = stub_images
    bare_article.image = featured_image
    bare_article.image_dark_mode = listing_image
    bare_article.listing_image = listing_image

    variants = bare_article.get_listing_image_variants()

    assert variants.dark_mode is None
    assert variants.mobile is None
    assert variants.dark_mode_mobile is None


@pytest.mark.parametrize("hero_style", [HeroStyle.STANDARD_IMAGE, HeroStyle.LARGE_IMAGE])
def test_blog_article_image_hero_styles_require_featured_image(hero_style, bare_article):
    bare_article.hero_style = hero_style
    with pytest.raises(ValidationError) as exc_info:
        bare_article.clean()
    assert "image" in exc_info.value.error_dict


def test_blog_article_video_hero_style_requires_a_video(bare_article, stub_images):
    featured_image, _ = stub_images
    bare_article.image = featured_image
    bare_article.hero_style = HeroStyle.VIDEO

    with pytest.raises(ValidationError) as exc_info:
        bare_article.clean()

    assert "hero_video" in exc_info.value.error_dict


def test_blog_article_text_only_hero_style_needs_no_assets(bare_article):
    bare_article.hero_style = HeroStyle.TEXT_ONLY

    bare_article.clean()  # does not raise


def test_blog_article_hero_renders_in_the_split_page_upper(make_article, real_images, rf):
    featured_image, _ = real_images
    article = make_article(
        image=featured_image,
        content=[("text", RichText("<p>Article body copy.</p>"))],
    )

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    assert upper
    assert upper.find("a", class_="fl-blog-back-link")
    header = upper.find("header", class_="fl-article-header")
    assert header and article.title in header.get_text()

    lower = soup.find("div", class_="fl-split-page-lower")
    assert lower
    assert "Article body copy." in lower.find("section", class_="fl-rich-text").get_text()


def test_blog_article_standard_hero_renders_image_before_title(make_article, real_images, rf):
    featured_image, _ = real_images
    article = make_article(image=featured_image, hero_style=HeroStyle.STANDARD_IMAGE)

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    assert "fl-article-header-standard-image" in header.get("class", [])
    children = header.find_all(recursive=False)
    children_classes = [child.get("class", []) for child in header.find_all(recursive=False)]

    assert len(children) >= 2, "Header should have at least two children: image and title"
    assert "image-variants-display" in children_classes[0], "First child should be the image"
    assert "fl-article-title" in children_classes[1], "Second child should be the title"
    assert article.title in children[1].get_text(), "Title should be rendered"


def test_blog_article_large_hero_renders_image_after_title(make_article, real_images, rf):
    featured_image, _ = real_images
    article = make_article(image=featured_image, hero_style=HeroStyle.LARGE_IMAGE)

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    assert "fl-article-header-large-image" in header.get("class", [])
    children = header.find_all(recursive=False)
    children_classes = [child.get("class", []) for child in children]

    assert len(children) >= 2, "Header should have at least two children: image and title"
    assert "fl-article-title" in children_classes[0], "First child should be the title"
    assert article.title in children[0].get_text(), "Title should be rendered"
    assert "image-variants-display" in children_classes[-1], "Second child should be the image"


def test_blog_article_text_only_hero_renders_no_media(make_article, real_images, rf):
    featured_image, _ = real_images
    article = make_article(image=featured_image, hero_style=HeroStyle.TEXT_ONLY)

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    assert "fl-article-header-text-only" in header.get("class", [])
    assert header.find("img") is None
    assert header.find("div", class_="fl-video") is None
    assert header.find("h1", class_="fl-heading")
    assert article.title in header.get_text()


def test_blog_article_video_hero_renders_video_before_title(make_article, real_images, rf):
    poster_image, _ = real_images
    article = make_article(
        hero_style=HeroStyle.VIDEO,
        hero_video=[
            {
                "type": "video",
                "value": {
                    "video_url": "https://www.youtube.com/watch?v=firefox123",
                    "alt": "A Firefox demo",
                    "poster": poster_image.pk,
                },
            }
        ],
    )

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    assert "fl-article-header-video" in header.get("class", [])
    assert header.find("div", class_="image-variants-display") is None

    video = header.find("div", class_="fl-video")
    assert video
    assert video.find("button")["data-video-id"] == "firefox123"

    children = [child.get("class", []) for child in header.find_all(recursive=False)]
    assert len(children) >= 2, "Header should have at least two children: video and title"
    assert "fl-video" in children[0]
    assert "fl-article-title" in children[1]


def test_blog_article_edit_handler_tabs():
    headings = [tab.heading for tab in BlogArticlePage.get_edit_handler().children]

    assert headings == ["Content", "Promote & SEO", "Settings"]


def test_blog_article_content_tab_panel_order():
    content_tab = BlogArticlePage.get_edit_handler().children[0]
    labels = [getattr(panel, "field_name", None) or getattr(panel, "relation_name", None) or panel.heading for panel in content_tab.children]

    assert labels == [
        "title",
        "internal_title",
        "description",
        "Topic & Tags",
        "article_authors",
        "Dates",
        "Featured Image",
        "Hero Options",
        "content",
    ]


def test_blog_article_form_exposes_publish_date_and_drops_show_in_menus():
    form_fields = BlogArticlePage.get_edit_handler().get_form_class().base_fields

    assert "first_published_at" in form_fields
    assert "updated_date" in form_fields
    assert "hide_dates" in form_fields
    assert "listing_image" in form_fields
    assert "show_in_menus" not in form_fields


def test_blog_article_hero_renders_description(make_article, rf):
    article = make_article(description=RichText("<p>What this article is about.</p>"))

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    header = soup.find("header", class_="fl-article-header")
    description = header.find("div", class_="fl-article-description")

    assert description
    assert "What this article is about." in description.get_text()


def test_blog_article_hero_renders_published_date(make_article, rf):
    article = make_article(first_published_at=datetime(2026, 6, 12, 9, 0, tzinfo=UTC))

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    meta = soup.find("header", class_="fl-article-header").find("div", class_="fl-article-meta")

    assert meta
    assert meta.find("time")["datetime"].startswith("2026-06-12")
    assert "Last updated on" not in meta.get_text()


def test_blog_article_hero_renders_updated_date(make_article, rf):
    article = make_article(updated_date=date(2026, 6, 12))

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    meta = soup.find("header", class_="fl-article-header").find("div", class_="fl-article-meta")

    assert "Last updated on" in meta.get_text()
    assert "June 12, 2026" in meta.get_text()


def test_blog_article_hide_dates_removes_hero_dates(make_article, rf):
    article = make_article(
        first_published_at=datetime(2026, 6, 12, 9, 0, tzinfo=UTC),
        updated_date=date(2026, 6, 12),
        hide_dates=True,
    )

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    assert soup.find("header", class_="fl-article-header").find("div", class_="fl-article-dates") is None


def test_blog_article_hero_puts_dates_under_byline(make_article, rf):
    authors = get_blog_authors()
    article = make_article(updated_date=date(2026, 6, 12))
    article.article_authors.set([BlogArticleAuthor(author=authors["ada-lovelace"])])
    article.save_revision().publish()

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    meta = soup.find("header", class_="fl-article-header").find("div", class_="fl-article-meta")
    children = meta.find_all(recursive=False)

    assert "fl-blog-byline" in children[0].get("class", [])
    assert "fl-article-dates" in children[1].get("class", [])


def test_blog_article_hide_dates_keeps_byline(make_article, rf):
    authors = get_blog_authors()
    article = make_article(hide_dates=True)
    article.article_authors.set([BlogArticleAuthor(author=authors["ada-lovelace"])])
    article.save_revision().publish()

    response = article.serve(rf.get(article.get_full_url()))
    soup = BeautifulSoup(response.content, "html.parser")

    meta = soup.find("header", class_="fl-article-header").find("div", class_="fl-article-meta")

    assert meta.find("p", class_="fl-blog-byline")
    assert meta.find("div", class_="fl-article-dates") is None


def test_blog_article_block_prefers_listing_image(make_article, stub_images):
    featured_image, listing_image = stub_images
    article = make_article(
        image=featured_image,
        image_dark_mode=featured_image,
        listing_image=listing_image,
        hero_style=HeroStyle.STANDARD_IMAGE,
    )

    value = BlogArticleBlock().to_python({"article": article.pk})

    assert value.get_image() == listing_image
    assert value.get_dark_image() is None
    assert value.get_mobile_image() is None
    assert value.get_mobile_dark_image() is None


def test_blog_article_block_falls_back_to_featured_image(make_article, stub_images):
    featured_image, dark_image = stub_images
    article = make_article(
        image=featured_image,
        image_dark_mode=dark_image,
        hero_style=HeroStyle.STANDARD_IMAGE,
    )

    value = BlogArticleBlock().to_python({"article": article.pk})

    assert value.get_image() == featured_image
    assert value.get_dark_image() == dark_image


def test_blog_article_block_override_beats_listing_image(make_article, stub_images):
    featured_image, listing_image = stub_images
    article = make_article(
        image=featured_image,
        listing_image=listing_image,
        hero_style=HeroStyle.STANDARD_IMAGE,
    )

    value = BlogArticleBlock().to_python(
        {
            "article": article.pk,
            "overrides": {"image": {"image": featured_image.pk}},
        }
    )

    assert value.get_image() == featured_image


def test_blog_list_item_renders_article_image(blog_index, make_article, real_images, rf):
    featured_image, _ = real_images
    article = make_article(title="Article with an image", image=featured_image)
    article.save_revision().publish()

    url = blog_index.full_url + blog_index.reverse_subpage("all_route")
    response = blog_index.all_route(rf.get(url))
    soup = BeautifulSoup(response.content, "html.parser")

    item = soup.find("div", class_="fl-blog-article-list").find("article", class_="fl-blog-article-list-item")
    assert "fl-blog-article-list-item-with-image" in item.get("class", [])
    assert item.find("div", class_="fl-blog-article-list-item-image").find("img")


def test_blog_list_item_renders_no_image_when_article_has_none(blog_index, make_article, rf):
    article = make_article(title="Article with no image", hero_style=HeroStyle.TEXT_ONLY)
    article.save_revision().publish()

    url = blog_index.full_url + blog_index.reverse_subpage("all_route")
    response = blog_index.all_route(rf.get(url))
    soup = BeautifulSoup(response.content, "html.parser")

    item = soup.find("div", class_="fl-blog-article-list").find("article", class_="fl-blog-article-list-item")
    assert "fl-blog-article-list-item-with-image" not in item.get("class", [])
    assert item.find("div", class_="fl-blog-article-list-item-image") is None


def test_blog_list_item_uses_listing_image_without_variants(blog_index, make_article, real_images, rf):
    featured_image, listing_image = real_images
    article = make_article(
        title="Article with a listing image",
        image=featured_image,
        image_dark_mode=featured_image,
        listing_image=listing_image,
    )
    article.save_revision().publish()

    url = blog_index.full_url + blog_index.reverse_subpage("all_route")
    response = blog_index.all_route(rf.get(url))
    soup = BeautifulSoup(response.content, "html.parser")

    item = soup.find("div", class_="fl-blog-article-list").find("article", class_="fl-blog-article-list-item")
    images = item.find("div", class_="fl-blog-article-list-item-image").find_all("img")

    assert len(images) == 1, "A dedicated listing image renders alone, with no variant siblings"


def test_blog_list_item_falls_back_to_featured_image_with_variants(blog_index, make_article, real_images, rf):
    featured_image, dark_image = real_images
    article = make_article(
        title="Article with a dark variant",
        image=featured_image,
        image_dark_mode=dark_image,
    )
    article.save_revision().publish()

    url = blog_index.full_url + blog_index.reverse_subpage("all_route")
    response = blog_index.all_route(rf.get(url))
    soup = BeautifulSoup(response.content, "html.parser")

    item = soup.find("div", class_="fl-blog-article-list").find("article", class_="fl-blog-article-list-item")
    images = item.find("div", class_="fl-blog-article-list-item-image").find_all("img")

    assert len(images) == 2, "The featured image renders alongside its dark-mode variant"
