# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Tests for blog article recommendations
#
# The "Recommended Articles" section displays up to 4 recommended published articles
# selected in this order:
# - From recommended_articles
# - Matching the article's topic and at least one tag
# - Matching the article's topic only
# - Matching the article's tag only
#
# Articles are not repeated, and an article does not appear in its own recommendations.

from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.text import slugify

import pytest
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.models import Locale, Site

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
def make_recommended_article(article):
    index_page = article.get_parent()

    def _make_recommended_article(title, *, topic=None, tags=(), description="", listing_image=None, first_published_at=None):
        recommended_article = BlogArticlePage(
            title=title,
            slug=slugify(title),
            topic=topic,
            description=description,
            listing_image=listing_image,
            hero_style=HeroStyle.TEXT_ONLY,
        )
        index_page.add_child(instance=recommended_article)
        recommended_article.tags.add(*tags)
        recommended_article.first_published_at = first_published_at
        recommended_article.save()
        return recommended_article

    return _make_recommended_article


def set_recommended_articles(article, *recommended):
    article.recommended_articles = [
        blog_article_block(recommended_article, f"rec00000-0000-0000-0000-{position:012d}")
        for position, recommended_article in enumerate(recommended, start=1)
    ]
    article.save()


@pytest.fixture
def recommendation_pool(article, blog_tags, make_recommended_article, other_topic, topic):
    """An article for every recommendation group (topic + tag, topic, tag), plus one
    matching neither the topic nor tag."""
    tag_a, tag_b = blog_tags
    article.tags.add(tag_a)
    article.save()
    return SimpleNamespace(
        tag_only=make_recommended_article("Tag only", topic=other_topic, tags=[tag_a], first_published_at=datetime(2026, 1, 5, tzinfo=UTC)),
        topic_only=make_recommended_article("Topic only", topic=topic, first_published_at=datetime(2026, 1, 4, tzinfo=UTC)),
        topic_and_tag=make_recommended_article("Topic and tag", topic=topic, tags=[tag_a], first_published_at=datetime(2026, 1, 3, tzinfo=UTC)),
        older_topic_and_tag=make_recommended_article(
            "Older topic and tag", topic=topic, tags=[tag_b, tag_a], first_published_at=datetime(2026, 1, 2, tzinfo=UTC)
        ),
        unmatched=make_recommended_article("No match", topic=other_topic, first_published_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )


@pytest.fixture
def get_article_soup(article, client):

    def _get_article_soup():
        response = client.get(article.get_full_url())

        assert response.status_code == 200
        return BeautifulSoup(response.content, "html.parser")

    return _get_article_soup


def test_no_recommendations(get_article_soup):
    soup = get_article_soup()

    assert soup.select_one(".fl-blog-recommended-articles") is None


@pytest.fixture
def get_article_recommendations(get_article_soup):

    def _get_article_recommendations():
        soup = get_article_soup()

        recommended_article_links = soup.select(".fl-blog-article-list-item .fl-heading a")
        recommended_article_titles = []
        for link in recommended_article_links:
            title = link.get_text(strip=True) if link else None
            recommended_article_titles.append(title)

        return recommended_article_titles

    return _get_article_recommendations


def test_default_recommendations(get_article_recommendations, make_recommended_article, recommendation_pool, topic):
    """Matching topic and tag before matching topic only before matching tag only."""
    unpublished = make_recommended_article("Unpublished", topic=topic, first_published_at=datetime(2026, 1, 6, tzinfo=UTC))
    unpublished.unpublish()

    assert get_article_recommendations() == [
        "Topic and tag",
        "Older topic and tag",
        "Topic only",
        "Tag only",
    ]


def test_default_recommendations_with_no_topic(article, get_article_recommendations, recommendation_pool):
    """A null article topic means matching by tag only."""
    BlogArticlePage.objects.filter(pk=article.pk).update(topic=None)

    assert get_article_recommendations() == [
        "Tag only",
        "Topic and tag",
        "Older topic and tag",
    ]


def test_custom_recommendations(article, get_article_recommendations, make_recommended_article, other_topic):
    """Custom recommendations render in order, and need not match the topic or a tag."""
    first_pick = make_recommended_article("First pick", topic=other_topic)
    second_pick = make_recommended_article("Second pick", topic=other_topic)
    unpublished_pick = make_recommended_article("Unpublished pick", topic=other_topic)
    unpublished_pick.unpublish()
    # Article should not recommend itself nor unpublished articles
    set_recommended_articles(article, second_pick, unpublished_pick, article, first_pick)

    assert get_article_recommendations() == ["Second pick", "First pick"]


def test_default_recommendations_fill_extra_slots_after_custom_ones(article, get_article_recommendations, recommendation_pool):
    """`recommended_articles` come before default ones."""
    set_recommended_articles(article, recommendation_pool.unmatched)

    assert get_article_recommendations() == [
        "No match",
        "Topic and tag",
        "Older topic and tag",
        "Topic only",
    ]


def test_recommendations_do_not_repeat(article, get_article_recommendations, recommendation_pool):
    """Default recommendations should never repeat, and should never duplicate custom recommendations."""
    set_recommended_articles(article, recommendation_pool.older_topic_and_tag)

    assert get_article_recommendations() == [
        "Older topic and tag",
        "Topic and tag",
        "Topic only",
        "Tag only",
    ]


def test_recommendations_hidden(article, get_article_soup, recommendation_pool):
    """`hide_recommended` hides all recommendations: custom and default."""
    article.hide_recommended = True
    article.save()
    set_recommended_articles(article, recommendation_pool.unmatched)

    soup = get_article_soup()

    assert soup.select_one(".fl-blog-recommended-articles") is None


@pytest.fixture
def minimal_recommendation(make_recommended_article, topic):
    return make_recommended_article("Matches topic", topic=topic, description="<p>Matches topic description</p>")


def test_recommended_article_minimum_elements(get_article_soup, minimal_recommendation):
    soup = get_article_soup()

    section = soup.select_one(".fl-blog-recommended-articles")
    assert section is not None

    section_heading = section.select_one("h2.fl-heading")
    assert section_heading is not None
    assert section_heading.get_text(strip=True) == "Recommended Articles"

    recommended_article_elements = section.select(".fl-blog-article-list-item")
    assert len(recommended_article_elements) == 1
    article_element = recommended_article_elements[0]
    heading = article_element.select_one("p.fl-superheading")
    assert heading is not None
    assert heading.get_text(strip=True) == "Topic"
    link = article_element.select_one("h3.fl-heading a.fl-link")
    assert link is not None
    assert link.get_text(strip=True) == "Matches topic"
    assert link.get("href") == minimal_recommendation.url
    description = article_element.select_one("div.fl-body")
    assert description is not None
    assert description.get_text(strip=True) == "Matches topic description"
    date = article_element.select_one("p.fl-blog-article-date")
    assert date is None
    tags = [tag.get_text(strip=True) for tag in article_element.select("span.fl-tag")]
    assert tags == []
    image = article_element.select_one("img")
    assert image is None


@pytest.fixture
def recommendation_listing_image():
    image_buffer = BytesIO()
    Image.new("RGB", (800, 450), (117, 79, 224)).save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return SpringfieldImage.objects.create(
        title="Matches topic and tag",
        file=ContentFile(image_buffer.read(), "matches-topic-and-tag.png"),
        width=800,
        height=450,
    )


@pytest.fixture
def full_recommendation(blog_tags, make_recommended_article, recommendation_listing_image, topic):
    return make_recommended_article(
        "Matches topic and tag",
        topic=topic,
        tags=blog_tags,
        description="<p>Matches topic and tag description</p>",
        listing_image=recommendation_listing_image,
        first_published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_recommended_article_optional_elements(full_recommendation, get_article_soup):
    soup = get_article_soup()

    recommended_article_elements = soup.select(".fl-blog-recommended-articles .fl-blog-article-list-item")
    assert len(recommended_article_elements) == 1
    article_element = recommended_article_elements[0]
    date = article_element.select_one("p.fl-blog-article-date")
    assert date is not None
    assert date.get_text(strip=True) == "Jan. 1, 2026"
    tags = [tag.get_text(strip=True) for tag in article_element.select("span.fl-tag")]
    assert tags == ["Tag A", "Tag B"]
    image = article_element.select_one("img")
    assert image is not None
    assert "matches-topic-and-tag" in image.get("src", "")


# ---------------------------------------------------------------------------
# Editing blog article recommendations
# ---------------------------------------------------------------------------


def test_max_four_custom_recommendations_presented():
    recommended_articles_field = BlogArticlePage.get_edit_handler().get_form_class().base_fields["recommended_articles"]

    assert recommended_articles_field.block.meta.max_num == 4


def test_max_four_custom_recommendations_validated(article, make_recommended_article, other_topic):
    recommended_articles_field = BlogArticlePage.get_edit_handler().get_form_class().base_fields["recommended_articles"]
    article.recommended_articles = [
        blog_article_block(make_recommended_article(f"Pick {position}", topic=other_topic), f"rec00000-0000-0000-0000-{position:012d}")
        for position in range(1, 6)
    ]

    with pytest.raises(ValidationError):
        recommended_articles_field.clean(article.recommended_articles)
