# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from urllib.parse import urljoin

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.text import Truncator

from babel.lists import format_list
from bs4 import BeautifulSoup
from wagtail.images.models import SourceImageIOError
from wagtail.rich_text import expand_db_html

from lib.l10n_utils.fluent import ftl
from lib.l10n_utils.templatetags.helpers import get_locale
from springfield.cms.templatetags.cms_tags import alt_text, remove_p_tag

FTL_FILES = ["blog/blog"]
FEED_IMAGE_FILTER = "width-1200"
EXCERPT_WORDS = 55
YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com")


class ContentEncodedFeed(Rss201rev2Feed):
    """RSS 2.0 with the full article body in <content:encoded>, as WordPress feeds have."""

    def rss_attributes(self):
        return {**super().rss_attributes(), "xmlns:content": "http://purl.org/rss/1.0/modules/content/"}

    def add_item_elements(self, handler, item):
        super().add_item_elements(handler, item)
        if item.get("content_encoded"):
            handler.addQuickElement("content:encoded", item["content_encoded"])


def rich_text(value):
    return mark_safe(expand_db_html(value.source))


def feed_rendition(image):
    """The image's feed rendition, or None when the image was deleted or its file is
    missing, so one broken image doesn't break the whole feed."""
    if image is None:
        return None
    try:
        return image.get_rendition(FEED_IMAGE_FILTER)
    except SourceImageIOError:
        return None


def image_html(image, caption="", link_url="", alt=None):
    rendition = feed_rendition(image)
    if rendition is None:
        return ""
    image_tag = format_html(
        '<img src="{}" alt="{}" width="{}" height="{}">', rendition.url, rendition.alt if alt is None else alt, rendition.width, rendition.height
    )
    if link_url:
        image_tag = format_html('<a href="{}">{}</a>', link_url, image_tag)
    if caption:
        return format_html("<figure>{}<figcaption>{}</figcaption></figure>", image_tag, caption)
    return format_html("<figure>{}</figure>", image_tag)


def video_html(value):
    """A self-hosted video plays in the reader; a YouTube video is its poster, linked to YouTube."""
    url = value["video_url"]
    poster = value.get("poster")
    poster_rendition = feed_rendition(poster)
    if any(host in url for host in YOUTUBE_HOSTS):
        if poster_rendition is None:
            return format_html('<p><a href="{}">{}</a></p>', url, value["alt"] or url)
        return image_html(poster, link_url=url, alt=value["alt"])
    if poster_rendition is None:
        return format_html('<figure><video src="{}" aria-label="{}" controls></video></figure>', url, value["alt"])
    return format_html('<figure><video src="{}" poster="{}" aria-label="{}" controls></video></figure>', url, poster_rendition.url, value["alt"])


def media_html(stream):
    parts = []
    for child in stream:
        if child.block_type == "image" and child.value.get("image"):
            parts.append(image_html(child.value["image"], alt=alt_text(child.value["image_alt"], child.value["image"])))
        elif child.block_type == "video":
            parts.append(video_html(child.value))
        elif child.block_type == "animation" and child.value.get("poster"):
            parts.append(image_html(child.value["poster"], alt=child.value["alt"]))
    return mark_safe("".join(parts))


def heading_html(value):
    """The heading as an h3, with its superheading and subheading as paragraphs around it."""
    parts = []
    if value.get("superheading_text"):
        parts.append(format_html("<p>{}</p>", remove_p_tag(rich_text(value["superheading_text"]))))
    if value.get("heading_text"):
        parts.append(format_html("<h3>{}</h3>", remove_p_tag(rich_text(value["heading_text"]))))
    if value.get("subheading_text"):
        parts.append(format_html("<p>{}</p>", remove_p_tag(rich_text(value["subheading_text"]))))
    return mark_safe("".join(parts))


def testimonial_html(value):
    attribution = format_html_join(
        ", ", "{}", ((remove_p_tag(rich_text(value[field])),) for field in ("attribution", "attribution_role") if value.get(field))
    )
    if attribution:
        return format_html("<blockquote>{}<p>— {}</p></blockquote>", rich_text(value["content"]), attribution)
    return format_html("<blockquote>{}</blockquote>", rich_text(value["content"]))


def cards_list_html(value):
    """Each card's media, headings, text, pictograms and testimonials. Buttons are left out
    because some only work on firefox.com, tags because they're decorative labels, and cards
    shown only to some visitors because a feed reader can't tell who's reading."""
    parts = []
    for card in value["cards"]:
        if card.value["settings"]["show_to"].has_conditions:
            continue
        for media in card.value["media"] or []:
            if media.block_type == "media":
                parts.append(media_html(media.value))
            elif media.block_type == "pictogram" and media.value.get("image"):
                parts.append(image_html(media.value["image"]))
        for child in card.value["content"]:
            if child.block_type == "heading":
                parts.append(heading_html(child.value))
            elif child.block_type == "content" and child.value:
                parts.append(rich_text(child.value))
            elif child.block_type == "pictogram" and child.value.get("image"):
                parts.append(image_html(child.value["image"]))
            elif child.block_type == "testimonial":
                parts.append(testimonial_html(child.value))
    return mark_safe("".join(parts))


def quote_html(value):
    attribution = ", ".join(part for part in (value.get("author"), value.get("authors_title")) if part)
    if attribution:
        return format_html("<blockquote>{}<p>— {}</p></blockquote>", rich_text(value["quote"]), attribution)
    return format_html("<blockquote>{}</blockquote>", rich_text(value["quote"]))


def image_caption_html(value):
    caption = rich_text(value["caption"]) if value.get("caption") else ""
    link = value.get("link")
    image = value["image"]["image"]
    return image_html(image, caption, link.get_url() if link else "", alt=alt_text(value["image"]["image_alt"], image))


def code_html(value):
    return format_html("<pre><code>{}</code></pre>", value["code"])


# One renderer per BlogArticlePage.content block type.
BODY_BLOCK_RENDERERS = {
    "text": rich_text,
    "image_caption": image_caption_html,
    "media": media_html,
    "code": code_html,
    "quote": quote_html,
    "cards_list": cards_list_html,
}


def body_html(article):
    return format_html_join("", "{}", ((BODY_BLOCK_RENDERERS[block.block_type](block.value),) for block in article.content))


def opening_image(article):
    """The image the body opens with, if it opens with one."""
    first = article.content[0] if article.content else None
    if first and first.block_type == "image_caption":
        return first.value["image"]["image"]
    if first and first.block_type == "media" and first.value and first.value[0].block_type == "image":
        return first.value[0].value.get("image")
    return None


def body_excerpt(article):
    """The opening words of the body's text, the way WordPress builds an excerpt. With no
    text blocks, the excerpt comes from the rest of the body, leaving out code."""
    text = " ".join(
        BeautifulSoup(expand_db_html(block.value.source), "html.parser").get_text(" ") for block in article.content if block.block_type == "text"
    )
    if not text.strip():
        soup = BeautifulSoup(body_html(article), "html.parser")
        for code in soup.find_all("pre"):
            code.decompose()
        text = soup.get_text(" ")
    return Truncator(text).words(EXCERPT_WORDS, truncate=" […]")


def absolutize(markup, base_url):
    """Make every link and image URL absolute, and drop the site's classes and data
    attributes, which mean nothing in a feed reader."""
    soup = BeautifulSoup(markup, "html.parser")
    for tag in soup.find_all(True):
        for attr in ("href", "src", "poster"):
            if tag.get(attr):
                tag[attr] = urljoin(base_url, tag[attr])
        for attr in list(tag.attrs):
            if attr == "class" or attr.startswith("data-"):
                del tag[attr]
    return str(soup)


class BlogFeed(Feed):
    """RSS feed of a BlogIndexPage's newest articles, or of one of its topics."""

    feed_type = ContentEncodedFeed

    def __init__(self, index, topic=None):
        self.index = index
        self.topic = topic
        self.language = index.locale.language_code

    def ftl(self, message_id, **kwargs):
        return ftl(message_id, ftl_files=FTL_FILES, locale=self.language, **kwargs)

    def title(self):
        if self.topic:
            return self.ftl("blog-feed-topic-title", topic=self.topic.name)
        return self.ftl("blog-feed-title")

    def description(self):
        return self.ftl("blog-feed-description")

    def link(self):
        if self.topic:
            return self.index.full_url + self.index.reverse_subpage("topic_route", args=[self.topic.slug])
        return self.index.full_url

    def feed_url(self):
        if self.topic:
            return self.index.full_url + self.index.reverse_subpage("topic_feed_route", args=[self.topic.slug])
        return self.index.full_url + self.index.reverse_subpage("feed_route")

    def items(self):
        return self.index.get_feed_articles(self.topic)

    def item_title(self, item):
        return item.title

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, item):
        return item.first_published_at

    def item_author_name(self, item):
        names = [author.name for author in item.get_authors()]
        return format_list(names, locale=get_locale(self.language)) if names else None

    def item_categories(self, item):
        topic = item.get_topic()
        names = [topic.name] if topic else []
        return names + [tag.name for tag in item.get_tags()]

    def item_description(self, item):
        """The article's description, or failing that its search description or the
        opening of its body."""
        if item.description:
            return absolutize(expand_db_html(item.description), item.full_url)
        if summary := item.search_description or body_excerpt(item):
            return format_html("<p>{}</p>", summary)
        return None

    def item_extra_kwargs(self, item):
        return {"content_encoded": absolutize(self.item_content(item), item.full_url)}

    def item_content(self, item):
        """The article as its page shows it: the hero, then each body block."""
        # Inline import: pages.py imports this module.
        from springfield.blog.models.pages import HeroStyle

        hero = ""
        if item.hero_style == HeroStyle.VIDEO and item.hero_video:
            hero = video_html(item.hero_video[0].value)
        elif item.hero_style != HeroStyle.TEXT_ONLY and item.image and opening_image(item) != item.image:
            hero = image_html(item.image, alt=alt_text(item.image_alt, item.image))
        return format_html("{}{}", hero, body_html(item))
