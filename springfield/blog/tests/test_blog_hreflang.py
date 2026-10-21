# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale, PageViewRestriction, Site

from springfield.blog.models import BlogArticlePage, BlogIndexPage, BlogTopic, BlogTopicPage
from springfield.blog.models.pages import HeroStyle
from springfield.cms.tests.factories import LocaleFactory

pytestmark = pytest.mark.django_db


def hreflangs(client, url):
    response = client.get(url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    return {link["hreflang"]: link["href"].removeprefix("https://www.firefox.com") for link in soup.find_all("link", rel="alternate", hreflang=True)}


@pytest.fixture
def blog():
    """An English blog with a German copy of one post: published, linked to the English
    post by translation_key only, and never synced."""
    english = Locale.objects.get(language_code="en-US")
    german = LocaleFactory(language_code="de")
    site = Site.objects.get(is_default_site=True)
    site.root_page.copy_for_translation(german).save_revision().publish()

    index = BlogIndexPage(title="Blog", slug="blog", locale=english)
    site.root_page.add_child(instance=index)
    index.save_revision().publish()
    topics = {slug: BlogTopic.objects.create(name=slug.title(), slug=slug, locale=english) for slug in ("privacy", "features")}

    posts = {}
    for slug, topic in (("english-only", "features"), ("translated", "privacy")):
        post = BlogArticlePage(title=slug, slug=slug, topic=topics[topic], locale=english, hero_style=HeroStyle.TEXT_ONLY)
        index.add_child(instance=post)
        post.save_revision().publish()
        posts[slug] = post

    de_index = index.copy_for_translation(german)
    de_index.save_revision().publish()
    de_topic = topics["privacy"].copy_for_translation(german)
    de_topic.save()
    de_post = posts["translated"].copy_for_translation(german)
    de_post.topic = de_topic
    de_post.save_revision().publish()
    for page in (de_index, de_post):
        page.refresh_from_db()

    return {"index": index, "de_index": de_index, "topics": topics, "de_topic": de_topic, "posts": posts, "de_post": de_post}


def test_english_only_post_lists_english_only(client, blog):
    assert hreflangs(client, "/en-US/blog/english-only/") == {"x-default": "/blog/english-only/", "en-US": "/en-US/blog/english-only/"}


def test_translated_post_lists_both_languages_reciprocally(client, blog):
    expected = {"x-default": "/blog/translated/", "en-US": "/en-US/blog/translated/", "de": "/de/blog/translated/"}

    assert hreflangs(client, "/en-US/blog/translated/") == expected
    assert hreflangs(client, "/de/blog/translated/") == expected


def test_draft_translation_is_not_listed(client, blog):
    blog["de_post"].unpublish()

    assert "de" not in hreflangs(client, "/en-US/blog/translated/")


def test_translation_under_a_private_index_is_not_listed(client, blog):
    PageViewRestriction.objects.create(page=blog["de_index"], restriction_type=PageViewRestriction.LOGIN)

    assert "de" not in hreflangs(client, "/en-US/blog/translated/")


def test_topic_route_lists_only_languages_with_articles_in_the_topic(client, blog):
    assert "de" not in hreflangs(client, "/en-US/blog/topics/features/")
    assert hreflangs(client, "/en-US/blog/topics/privacy/")["de"] == "/de/blog/topics/privacy/"
    assert hreflangs(client, "/de/blog/topics/privacy/")["en-US"] == "/en-US/blog/topics/privacy/"


def test_topic_route_drops_a_language_whose_topic_is_a_draft(client, blog):
    blog["de_topic"].unpublish()

    assert "de" not in hreflangs(client, "/en-US/blog/topics/privacy/")


def test_topic_route_drops_a_language_whose_articles_in_the_topic_are_drafts(client, blog):
    blog["de_post"].unpublish()

    assert "de" not in hreflangs(client, "/en-US/blog/topics/privacy/")


def test_curated_topic_page_lists_the_topics_languages(client, blog):
    """A curated English topic page with no German copy still lists German, matching the
    plain German topic listing that links back to it."""
    topic_page = BlogTopicPage(title="Privacy", slug="privacy", topic=blog["topics"]["privacy"], locale=blog["index"].locale)
    blog["index"].add_child(instance=topic_page)
    topic_page.save_revision().publish()

    assert hreflangs(client, "/en-US/blog/topics/privacy/")["de"] == "/de/blog/topics/privacy/"


@pytest.mark.parametrize("route", ["all/", "topics/"])
def test_listing_routes_drop_a_language_with_no_live_articles(client, blog, route):
    assert hreflangs(client, f"/en-US/blog/{route}")["de"] == f"/de/blog/{route}"

    blog["de_post"].unpublish()

    assert "de" not in hreflangs(client, f"/en-US/blog/{route}")


def test_alias_locale_is_not_listed(client, blog):
    assert hreflangs(client, "/en-GB/blog/english-only/") == {"x-default": "/blog/english-only/", "en-US": "/en-US/blog/english-only/"}


def test_index_lists_its_live_translation(client, blog):
    assert hreflangs(client, "/en-US/blog/")["de"] == "/de/blog/"

    blog["de_index"].unpublish()

    assert "de" not in hreflangs(client, "/en-US/blog/")
