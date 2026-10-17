# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import itertools
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree

from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import override_settings

import pytest
from bs4 import BeautifulSoup
from wagtail.images.models import SourceImageIOError
from wagtail.models import Locale, PageViewRestriction, Site

from springfield.blog.feeds import BODY_BLOCK_RENDERERS
from springfield.blog.models import BlogArticleAuthor, BlogAuthor, BlogIndexPage
from springfield.blog.models.pages import FEED_ITEMS, BlogArticlePage, HeroStyle
from springfield.blog.models.snippets import BlogTag, BlogTopic
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models.images import SpringfieldImage

pytestmark = [pytest.mark.django_db]

DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"


@pytest.fixture
def blog_index(minimal_site):
    root_page = Site.objects.get(is_default_site=True).root_page
    index_page = BlogIndexPage(title="Blog", slug="test-unit-blog", locale=Locale.objects.get(language_code="en-US"))
    root_page.add_child(instance=index_page)
    return index_page


@pytest.fixture
def blog_topic(blog_index):
    return BlogTopic.objects.create(name="Privacy", slug="test-unit-privacy", locale=blog_index.locale)


@pytest.fixture
def other_topic(blog_index):
    return BlogTopic.objects.create(name="Security", slug="test-unit-security", locale=blog_index.locale)


@pytest.fixture
def blog_tag(blog_index):
    return BlogTag.objects.create(name="VPN", slug="test-unit-vpn", locale=blog_index.locale)


@pytest.fixture
def make_article(blog_index, blog_topic):
    """Each new article is published one day after the previous one."""
    numbers = itertools.count(1)

    def make_article(parent=None, **fields):
        number = next(numbers)
        fields.setdefault("topic", blog_topic)
        fields.setdefault("first_published_at", datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=number))
        if not fields.get("image"):
            fields.setdefault("hero_style", HeroStyle.TEXT_ONLY)
        parent = parent or blog_index
        article = BlogArticlePage(title=fields.pop("title", f"Article {number}"), slug=f"test-unit-article-{number}", locale=parent.locale, **fields)
        parent.add_child(instance=article)
        return article

    return make_article


def get_feed(index, rf, topic_slug=None):
    if topic_slug:
        return index.topic_feed_route(rf.get(index.url + f"topics/{topic_slug}/feed/"), topic_slug)
    return index.feed_route(rf.get(index.url + "feed/"))


def parse_feed(response):
    return ElementTree.fromstring(response.content).find("channel")


def item_titles(response):
    return [item.findtext("title") for item in parse_feed(response).iter("item")]


def test_feed_is_rss(blog_index, make_article, rf):
    response = get_feed(blog_index, rf)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/rss+xml; charset=utf-8"
    channel = parse_feed(response)
    assert channel.findtext("title") == "Firefox Blog"
    assert channel.findtext("link") == blog_index.full_url
    assert channel.findtext("language") == "en-US"


def test_feed_lists_newest_articles_first(blog_index, make_article, rf):
    make_article(title="Older")
    make_article(title="Newer")

    assert item_titles(get_feed(blog_index, rf)) == ["Newer", "Older"]


def test_feed_is_limited_to_the_newest_articles(blog_index, make_article, rf):
    for __ in range(FEED_ITEMS + 1):
        make_article()

    titles = item_titles(get_feed(blog_index, rf))

    assert len(titles) == FEED_ITEMS
    assert "Article 1" not in titles


def test_feed_item_fields(blog_index, blog_topic, blog_tag, make_article, rf):
    article = make_article(title="Item", description="<p>A short summary.</p>")
    article.tags.add(blog_tag)
    article.save()
    for position, name in enumerate(["Ada Lovelace", "Grace Hopper"]):
        author = BlogAuthor.objects.create(name=name, slug=f"author-{position}", locale=blog_index.locale)
        BlogArticleAuthor.objects.create(page=article, author=author, sort_order=position)

    item = parse_feed(get_feed(blog_index, rf)).find("item")

    assert item.findtext("link") == article.full_url
    assert item.findtext("guid") == article.full_url
    assert item.findtext("pubDate") == "Fri, 02 Jan 2026 00:00:00 +0000"
    assert item.findtext(DC_CREATOR) == "Ada Lovelace and Grace Hopper"
    assert [category.text for category in item.findall("category")] == ["Privacy", "VPN"]
    assert item.findtext("description") == "<p>A short summary.</p>"


CONTENT_ENCODED = "{http://purl.org/rss/1.0/modules/content/}encoded"


def item_content(index, rf):
    return BeautifulSoup(parse_feed(get_feed(index, rf)).find("item").findtext(CONTENT_ENCODED), "html.parser")


def test_feed_item_content_is_the_full_article(blog_index, make_article, rf):
    image = get_placeholder_images()[0]
    make_article(
        image=image,
        hero_style=HeroStyle.STANDARD_IMAGE,
        description="<p>Summary.</p>",
        content=[
            {"type": "text", "value": '<p class="intro">Body <a href="/en-US/about/">text</a>.</p>'},
            {"type": "image_caption", "value": {"image": {"image": image.pk}, "caption": "<p>A caption</p>", "layout": "default"}},
            {"type": "code", "value": {"code": "<b>bold</b>"}},
            {"type": "quote", "value": {"quote": "<p>Quoted.</p>", "author": "Ada", "authors_title": "Countess"}},
        ],
    )

    content = item_content(blog_index, rf)

    hero, figure = content.find_all("figure")
    assert hero.img["src"].startswith("http://testserver/")
    assert hero.img["alt"] == image.default_alt_text
    paragraph = content.find("p")
    assert paragraph.get_text() == "Body text."
    assert not paragraph.has_attr("class")
    assert paragraph.a["href"] == "http://testserver/en-US/about/"
    assert figure.figcaption.get_text() == "A caption"
    assert content.find("pre").get_text() == "<b>bold</b>"
    assert content.blockquote.get_text() == "Quoted.— Ada, Countess"


def test_feed_item_content_without_a_hero_image(blog_index, make_article, rf):
    image = get_placeholder_images()[0]
    make_article(image=image, hero_style=HeroStyle.TEXT_ONLY, content=[{"type": "text", "value": "<p>Body.</p>"}])

    assert item_content(blog_index, rf).find("img") is None


def test_feed_item_content_videos(blog_index, make_article, rf):
    poster = get_placeholder_images()[0]
    make_article(
        content=[
            {
                "type": "media",
                "value": [
                    {"type": "video", "value": {"video_url": "https://www.youtube.com/watch?v=abc", "alt": "Demo", "poster": poster.pk}},
                    {"type": "video", "value": {"video_url": "https://assets.mozilla.net/demo.webm", "alt": "Demo", "poster": poster.pk}},
                ],
            }
        ]
    )

    content = item_content(blog_index, rf)

    youtube = content.find("a")
    assert youtube["href"] == "https://www.youtube.com/watch?v=abc"
    assert youtube.img["src"].startswith("http://testserver/")
    video = content.find("video")
    assert video["src"] == "https://assets.mozilla.net/demo.webm"
    assert video["poster"].startswith("http://testserver/")


def test_feed_item_content_cards_keep_headings_and_text_but_not_buttons(blog_index, make_article, rf):
    card_content = [
        {"type": "heading", "value": {"heading_text": "<p>Card heading</p>"}},
        {"type": "content", "value": "<p>Card text</p>"},
        {
            "type": "buttons",
            "value": [{"type": "button", "value": {"label": "Download", "link": {"link_to": "custom_url", "custom_url": "https://example.com"}}}],
        },
    ]
    make_article(content=[{"type": "cards_list", "value": {"cards": [{"type": "card", "value": {"media": [], "content": card_content}}]}}])

    content = item_content(blog_index, rf)

    assert content.find("h3").get_text() == "Card heading"
    assert content.find("p").get_text() == "Card text"
    assert "Download" not in content.get_text()


def test_feed_item_content_video_hero(blog_index, make_article, rf):
    poster = get_placeholder_images()[0]
    make_article(
        hero_style=HeroStyle.VIDEO,
        hero_video=[{"type": "video", "value": {"video_url": "https://www.youtube.com/watch?v=hero", "alt": "Hero", "poster": poster.pk}}],
    )

    hero_link = item_content(blog_index, rf).find("figure").a

    assert hero_link["href"] == "https://www.youtube.com/watch?v=hero"
    assert hero_link.img["src"].startswith("http://testserver/")


def test_feed_item_content_linked_image_caption(blog_index, make_article, rf):
    image = get_placeholder_images()[0]
    link = {"link_to": "custom_url", "custom_url": "https://example.com/more"}
    make_article(content=[{"type": "image_caption", "value": {"image": {"image": image.pk}, "caption": "", "link": link, "layout": "default"}}])

    figure = item_content(blog_index, rf).find("figure")

    assert figure.a["href"] == "https://example.com/more"
    assert figure.a.img
    assert figure.figcaption is None


def test_feed_item_content_animation_and_pictogram_show_their_images(blog_index, make_article, rf):
    image = get_placeholder_images()[0]
    animation = {"video_url": "https://assets.mozilla.net/loop.webm", "alt": "Loop", "poster": image.pk}
    card = {"media": [{"type": "pictogram", "value": {"image": image.pk}}], "content": []}
    make_article(
        content=[
            {"type": "media", "value": [{"type": "animation", "value": animation}]},
            {"type": "cards_list", "value": {"cards": [{"type": "card", "value": card}]}},
        ]
    )

    content = item_content(blog_index, rf)

    assert len(content.find_all("img")) == 2
    assert content.find("video") is None


def test_feed_item_content_youtube_without_a_poster_is_a_link(blog_index, make_article, rf):
    make_article(
        content=[{"type": "media", "value": [{"type": "video", "value": {"video_url": "https://youtu.be/abc", "alt": "Demo", "poster": None}}]}]
    )

    link = item_content(blog_index, rf).find("a")

    assert link["href"] == "https://youtu.be/abc"
    assert link.get_text() == "Demo"


def test_feed_item_content_skips_a_deleted_image(blog_index, make_article, rf):
    deleted_image_pk = 999999
    make_article(
        content=[
            {"type": "image_caption", "value": {"image": {"image": deleted_image_pk}, "caption": "<p>Gone</p>", "layout": "default"}},
            {"type": "text", "value": "<p>Still here.</p>"},
        ]
    )

    content = item_content(blog_index, rf)

    assert content.find("figure") is None
    assert content.get_text() == "Still here."


def test_feed_survives_an_image_whose_file_is_missing(blog_index, make_article, rf, monkeypatch):
    image = get_placeholder_images()[0]
    make_article(
        title="Broken image", content=[{"type": "image_caption", "value": {"image": {"image": image.pk}, "caption": "", "layout": "default"}}]
    )
    make_article(title="Fine")

    def missing_file(*args, **kwargs):
        raise SourceImageIOError("missing")

    monkeypatch.setattr(SpringfieldImage, "get_rendition", missing_file)

    assert item_titles(get_feed(blog_index, rf)) == ["Fine", "Broken image"]


@override_settings(ALLOWED_HOSTS=["*"])
def test_feed_item_urls_use_the_site_host_not_the_request_host(blog_index, make_article, rf):
    article = make_article(content=[{"type": "text", "value": '<p><a href="#details">Jump</a></p>'}])

    response = blog_index.feed_route(rf.get(blog_index.url + "feed/", HTTP_HOST="origin.internal"))
    content = BeautifulSoup(parse_feed(response).find("item").findtext(CONTENT_ENCODED), "html.parser")

    assert content.a["href"] == f"{article.full_url}#details"


def test_every_body_block_type_has_a_feed_renderer():
    body_block_types = set(BlogArticlePage._meta.get_field("content").stream_block.child_blocks)

    assert body_block_types == set(BODY_BLOCK_RENDERERS)


def test_feed_item_description_falls_back_to_the_search_description(blog_index, make_article, rf):
    make_article(search_description="Search summary.", content=[{"type": "text", "value": "<p>Body.</p>"}])

    assert parse_feed(get_feed(blog_index, rf)).find("item").findtext("description") == "<p>Search summary.</p>"


def test_feed_item_description_falls_back_to_a_body_excerpt(blog_index, make_article, rf):
    words = [f"word{number}" for number in range(60)]
    make_article(content=[{"type": "text", "value": f"<p>{' '.join(words[:30])}</p>"}, {"type": "text", "value": f"<p>{' '.join(words[30:])}</p>"}])

    description = parse_feed(get_feed(blog_index, rf)).find("item").findtext("description")

    assert description == f"<p>{' '.join(words[:55])} […]</p>"


def test_feed_item_content_resolves_anchors_against_the_article(blog_index, make_article, rf):
    article = make_article(content=[{"type": "text", "value": '<p><a href="#details">Jump</a></p>'}])

    assert item_content(blog_index, rf).a["href"] == f"{article.full_url}#details"


def test_feed_item_description_is_the_summary(blog_index, make_article, rf):
    make_article(image=get_placeholder_images()[0], description="<p>Summary.</p>")

    assert parse_feed(get_feed(blog_index, rf)).find("item").findtext("description") == "<p>Summary.</p>"


def test_feed_leaves_out_unpublished_and_private_articles(blog_index, make_article, rf):
    make_article(title="Public")
    make_article(title="Draft", live=False)
    private = make_article(title="Private")
    PageViewRestriction.objects.create(page=private, restriction_type=PageViewRestriction.LOGIN)

    assert item_titles(get_feed(blog_index, rf)) == ["Public"]


def test_feed_under_a_private_index_is_empty(blog_index, make_article, rf):
    """Unlike the HTML listings, a feed never lists drafts or private articles for editors."""
    PageViewRestriction.objects.create(page=blog_index, restriction_type=PageViewRestriction.LOGIN)
    make_article(title="Live")
    make_article(title="Draft", live=False)

    assert item_titles(get_feed(blog_index, rf)) == []


def test_feed_leaves_out_articles_excluded_from_rss(blog_index, blog_topic, make_article, rf):
    make_article(title="Included")
    make_article(title="Excluded", exclude_from_rss=True)

    assert item_titles(get_feed(blog_index, rf)) == ["Included"]
    assert item_titles(get_feed(blog_index, rf, blog_topic.slug)) == ["Included"]


def test_feed_honours_feed_exclusions(blog_index, blog_topic, other_topic, blog_tag, make_article, rf):
    blog_index.feed_exclusions = [
        {"type": "topic", "value": blog_topic.pk, "id": "fx000001-0000-0000-0000-000000000001"},
        {"type": "tag", "value": blog_tag.pk, "id": "fx000002-0000-0000-0000-000000000002"},
    ]
    blog_index.save()
    make_article(title="Excluded topic")
    with_tag = make_article(title="Excluded tag", topic=other_topic)
    with_tag.tags.add(blog_tag)
    with_tag.save()
    make_article(title="Clear", topic=other_topic)

    assert item_titles(get_feed(blog_index, rf)) == ["Clear"]


def test_topic_feed_lists_only_its_topic(blog_index, blog_topic, other_topic, make_article, rf):
    make_article(title="Privacy article")
    make_article(title="Security article", topic=other_topic)

    response = get_feed(blog_index, rf, blog_topic.slug)

    assert item_titles(response) == ["Privacy article"]
    channel = parse_feed(response)
    assert channel.findtext("title") == "Privacy – Firefox Blog"
    assert channel.findtext("link") == blog_index.full_url + "topics/test-unit-privacy/"


def test_topic_feed_keeps_its_own_excluded_topic(blog_index, blog_topic, make_article, rf):
    blog_index.feed_exclusions = [{"type": "topic", "value": blog_topic.pk, "id": "fx000001-0000-0000-0000-000000000001"}]
    blog_index.save()
    make_article(title="Privacy article")

    assert item_titles(get_feed(blog_index, rf)) == []
    assert item_titles(get_feed(blog_index, rf, blog_topic.slug)) == ["Privacy article"]


def test_topic_feed_for_an_empty_topic_is_empty(blog_index, blog_topic, rf):
    response = get_feed(blog_index, rf, blog_topic.slug)

    assert response.status_code == 200
    assert item_titles(response) == []


@pytest.mark.parametrize("slug", ["no-such-topic", "draft-topic"])
def test_topic_feed_404s_for_a_missing_topic(blog_index, rf, slug):
    BlogTopic.objects.create(name="Draft", slug="draft-topic", locale=blog_index.locale, live=False)

    with pytest.raises(Http404):
        get_feed(blog_index, rf, slug)


def test_feed_lists_only_its_own_locale(blog_index, make_article, rf):
    make_article(title="English article")
    french = Locale.objects.get_or_create(language_code="fr")[0]
    french_index = blog_index.copy_for_translation(french)
    french_index.save_revision().publish()
    french_topic = BlogTopic.objects.create(name="Vie privée", slug="test-unit-vie-privee", locale=french)
    make_article(parent=french_index, title="Article français", topic=french_topic)

    response = get_feed(french_index, rf)

    assert item_titles(response) == ["Article français"]
    assert parse_feed(response).findtext("language") == "fr"
    assert item_titles(get_feed(blog_index, rf)) == ["English article"]


def test_feed_routes_take_precedence_over_child_pages(blog_index):
    assert blog_index.resolve_subpage("/feed/")[0] == blog_index.feed_route
    assert blog_index.resolve_subpage("/topics/test-unit-privacy/feed/")[0] == blog_index.topic_feed_route


@pytest.mark.parametrize("slug", ["all", "topics", "feed"])
def test_article_rejects_a_reserved_slug(make_article, slug):
    article = make_article()
    article.slug = slug

    with pytest.raises(ValidationError) as error:
        article.full_clean()
    assert "slug" in error.value.message_dict


def feed_links(response):
    soup = BeautifulSoup(response.content, "html.parser")
    return [(link["title"], link["href"]) for link in soup.find_all("link", rel="alternate", type="application/rss+xml")]


@pytest.mark.parametrize("route", ["index_route", "all_route", "topics_route"])
def test_index_routes_link_to_the_feed(blog_index, rf, route):
    response = getattr(blog_index, route)(rf.get(blog_index.url))

    assert feed_links(response) == [("Firefox Blog", blog_index.url + "feed/")]


def test_topic_route_links_to_both_feeds(blog_index, blog_topic, rf):
    response = blog_index.topic_route(rf.get(blog_index.url + "topics/test-unit-privacy/"), blog_topic.slug)

    assert feed_links(response) == [
        ("Firefox Blog", blog_index.url + "feed/"),
        ("Privacy – Firefox Blog", blog_index.url + "topics/test-unit-privacy/feed/"),
    ]


def test_article_links_to_the_feed(blog_index, make_article, rf):
    article = make_article()

    response = article.serve(rf.get(article.url))

    assert feed_links(response) == [("Firefox Blog", blog_index.url + "feed/")]


def test_exclude_from_rss_is_on_the_settings_tab():
    settings_tab = next(tab for tab in BlogArticlePage.get_edit_handler().children if tab.heading == "Settings")

    assert "exclude_from_rss" in settings_tab.get_form_options()["fields"]


def test_feed_is_served_at_its_url_with_page_caching(blog_index, make_article, client):
    make_article(title="Served")

    response = client.get(blog_index.url + "feed/")

    assert response.status_code == 200
    assert response["Cache-Control"] == "max-age=600"
    assert item_titles(response) == ["Served"]
