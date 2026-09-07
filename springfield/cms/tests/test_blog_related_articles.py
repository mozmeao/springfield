# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Tests for related articles on blog articles
#
# The "Related Articles" section displays up to 4 related published articles
# selected in this order:
# - From related_articles
# - Matching the article's topic and at least one tag
# - Matching the article's topic only
# - Matching the article's tag only
#
# Articles are not repeated, and an article does not appear in its own related
# articles section.

from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.text import slugify

import pytest
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.models import Locale, PageViewRestriction, Site

from springfield.cms.fixtures.blog_fixtures import blog_article_block
from springfield.cms.models import BlogArticlePage, BlogIndexPage, BlogTag, BlogTopic, HeroStyle, SpringfieldImage

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def topic():
    return BlogTopic.objects.create(name="Topic", slug="topic", locale=Locale.get_default())


@pytest.fixture
def other_topic():
    return BlogTopic.objects.create(name="Other topic", slug="other-topic", locale=Locale.get_default())


@pytest.fixture
def blog_tags():
    return [BlogTag.objects.create(name=name, slug=slugify(name), locale=Locale.get_default()) for name in ("Tag A", "Tag B")]


@pytest.fixture
def article(minimal_site, topic):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = root_page.add_child(instance=BlogIndexPage(title="Blog", slug="blog"))
    return index_page.add_child(instance=BlogArticlePage(title="Article", slug="article", topic=topic, hero_style=HeroStyle.TEXT_ONLY))


@pytest.fixture
def make_related_article(article):
    index_page = article.get_parent()

    def _make_related_article(title, *, topic=None, tags=(), description="", listing_image=None, first_published_at=None):
        related_article = BlogArticlePage(
            title=title,
            slug=slugify(title),
            topic=topic,
            description=description,
            listing_image=listing_image,
            hero_style=HeroStyle.TEXT_ONLY,
        )
        index_page.add_child(instance=related_article)
        related_article.tags.add(*tags)
        related_article.first_published_at = first_published_at
        related_article.save()
        return related_article

    return _make_related_article


def restrict_page(page):
    PageViewRestriction.objects.create(page=page, restriction_type=PageViewRestriction.PASSWORD, password="secret")


def set_related_articles(article, *related):
    article.related_articles = [
        blog_article_block(related_article, f"rec00000-0000-0000-0000-{position:012d}") for position, related_article in enumerate(related, start=1)
    ]
    article.save()


@pytest.fixture
def related_articles_pool(article, blog_tags, make_related_article, other_topic, topic):
    """An article for every relation group (topic + tag, topic, tag), plus one matching
    neither the topic nor tag."""
    tag_a, tag_b = blog_tags
    article.tags.add(tag_a)
    article.save()
    return SimpleNamespace(
        tag_only=make_related_article("Tag only", topic=other_topic, tags=[tag_a], first_published_at=datetime(2026, 1, 5, tzinfo=UTC)),
        topic_only=make_related_article("Topic only", topic=topic, first_published_at=datetime(2026, 1, 4, tzinfo=UTC)),
        topic_and_tag=make_related_article("Topic and tag", topic=topic, tags=[tag_a], first_published_at=datetime(2026, 1, 3, tzinfo=UTC)),
        older_topic_and_tag=make_related_article(
            "Older topic and tag", topic=topic, tags=[tag_b, tag_a], first_published_at=datetime(2026, 1, 2, tzinfo=UTC)
        ),
        unmatched=make_related_article("No match", topic=other_topic, first_published_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )


@pytest.fixture
def get_article_soup(article, client):

    def _get_article_soup():
        response = client.get(article.get_full_url())

        assert response.status_code == 200
        return BeautifulSoup(response.content, "html.parser")

    return _get_article_soup


def test_no_related_articles(get_article_soup):
    soup = get_article_soup()

    assert soup.select_one(".fl-blog-related-articles") is None


@pytest.fixture
def get_related_articles(get_article_soup):

    def _get_related_articles():
        soup = get_article_soup()

        related_article_links = soup.select(".fl-blog-article-list-item .fl-heading a")
        related_article_titles = []
        for link in related_article_links:
            title = link.get_text(strip=True) if link else None
            related_article_titles.append(title)

        return related_article_titles

    return _get_related_articles


def test_default_related_articles(get_related_articles, make_related_article, related_articles_pool, topic):
    """Matching topic and tag before matching topic only before matching tag only."""
    unpublished = make_related_article("Unpublished", topic=topic, first_published_at=datetime(2026, 1, 6, tzinfo=UTC))
    unpublished.unpublish()
    # Articles behind a view restriction are not shown
    restricted = make_related_article("Restricted", topic=topic, first_published_at=datetime(2026, 1, 7, tzinfo=UTC))
    restrict_page(restricted)

    assert get_related_articles() == [
        "Topic and tag",
        "Older topic and tag",
        "Topic only",
        "Tag only",
    ]


def test_default_related_articles_for_article_with_null_topic_matches_by_tag_only(article, get_related_articles, related_articles_pool):
    BlogArticlePage.objects.filter(pk=article.pk).update(topic=None)

    # No "Topic only" article
    assert get_related_articles() == [
        "Tag only",
        "Topic and tag",
        "Older topic and tag",
    ]


def test_custom_related_articles(article, get_related_articles, make_related_article, other_topic):
    """Custom related articles render in order, and need not match the topic or a tag."""
    first_pick = make_related_article("First pick", topic=other_topic)
    second_pick = make_related_article("Second pick", topic=other_topic)
    unpublished_pick = make_related_article("Unpublished pick", topic=other_topic)
    unpublished_pick.unpublish()
    restricted_pick = make_related_article("Restricted pick", topic=other_topic)
    restrict_page(restricted_pick)
    # Article should not show itself, unpublished articles, nor restricted ones
    set_related_articles(article, second_pick, unpublished_pick, article, restricted_pick, first_pick)

    assert get_related_articles() == ["Second pick", "First pick"]


def test_ignore_deleted_custom_related_article(article, get_related_articles, make_related_article, other_topic):
    deleted_article = make_related_article("Deleted article", topic=other_topic)
    remaining_article = make_related_article("Remaining article", topic=other_topic)
    set_related_articles(article, deleted_article, remaining_article)
    deleted_article.delete()

    assert get_related_articles() == ["Remaining article"]


def test_default_related_articles_fill_extra_slots_after_custom_ones(article, get_related_articles, related_articles_pool):
    """`related_articles` come before default ones."""
    set_related_articles(article, related_articles_pool.unmatched)

    assert get_related_articles() == [
        "No match",
        "Topic and tag",
        "Older topic and tag",
        "Topic only",
    ]


def test_related_articles_do_not_repeat(article, get_related_articles, related_articles_pool):
    """Default related articles should never repeat, and should never duplicate custom ones."""
    set_related_articles(article, related_articles_pool.older_topic_and_tag)

    assert get_related_articles() == [
        "Older topic and tag",
        "Topic and tag",
        "Topic only",
        "Tag only",
    ]


def test_related_articles_hidden(article, get_article_soup, related_articles_pool):
    """`hide_related` hides all related articles: custom and default."""
    article.hide_related = True
    article.save()
    set_related_articles(article, related_articles_pool.unmatched)

    soup = get_article_soup()

    assert soup.select_one(".fl-blog-related-articles") is None


@pytest.fixture
def minimal_related_article(make_related_article, topic):
    related_article = make_related_article("Related", topic=topic, description="<p>Related description</p>")
    BlogArticlePage.objects.filter(pk=related_article.pk).update(topic=None)
    return related_article


def test_related_article_minimum_elements(article, get_article_soup, minimal_related_article):
    set_related_articles(article, minimal_related_article)

    soup = get_article_soup()

    section = soup.select_one(".fl-blog-related-articles")
    assert section is not None

    section_heading = section.select_one("h2.fl-heading")
    assert section_heading is not None
    assert section_heading.get_text(strip=True) == "Related Articles"

    related_article_elements = section.select(".fl-blog-article-list-item")
    assert len(related_article_elements) == 1
    article_element = related_article_elements[0]
    topic_heading = article_element.select_one("p.fl-superheading")
    assert topic_heading is None
    link = article_element.select_one("h3.fl-heading a.fl-link")
    assert link is not None
    assert link.get_text(strip=True) == "Related"
    assert link.get("href") == minimal_related_article.url
    description = article_element.select_one("div.fl-body")
    assert description is not None
    assert description.get_text(strip=True) == "Related description"
    image = article_element.select_one("img")
    assert image is None


@pytest.fixture
def related_listing_image():
    image_buffer = BytesIO()
    Image.new("RGB", (800, 450), (117, 79, 224)).save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return SpringfieldImage.objects.create(
        title="Related",
        file=ContentFile(image_buffer.read(), "related-image.png"),
        width=800,
        height=450,
    )


@pytest.fixture
def full_related_article(minimal_related_article, related_listing_image, topic):
    minimal_related_article.topic = topic
    minimal_related_article.listing_image = related_listing_image
    minimal_related_article.save()
    return minimal_related_article


def test_related_article_optional_elements(full_related_article, get_article_soup):
    soup = get_article_soup()

    related_article_elements = soup.select(".fl-blog-related-articles .fl-blog-article-list-item")
    assert len(related_article_elements) == 1
    article_element = related_article_elements[0]
    topic_heading = article_element.select_one("p.fl-superheading")
    assert topic_heading is not None
    assert topic_heading.get_text(strip=True) == "Topic"
    image = article_element.select_one("img")
    assert image is not None
    assert "related-image" in image.get("src", "")


# ---------------------------------------------------------------------------
# Editing related articles on blog articles
# ---------------------------------------------------------------------------


def test_max_four_custom_related_articles_validated(article, make_related_article, other_topic):
    related_articles_field = BlogArticlePage.get_edit_handler().get_form_class().base_fields["related_articles"]
    article.related_articles = [
        blog_article_block(make_related_article(f"Pick {position}", topic=other_topic), f"rec00000-0000-0000-0000-{position:012d}")
        for position in range(1, 6)
    ]

    with pytest.raises(ValidationError):
        related_articles_field.clean(article.related_articles)
