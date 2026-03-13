# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.text import slugify

from wagtail.models import Locale, Site

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import BlogArticlePage, BlogIndexPage, Tag

LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

# 5 featured + 12 non-featured = 17 total, triggering second page of pagination
NUM_FEATURED = 5
NUM_REGULAR = 12


def get_blog_topics() -> dict[str, Tag]:
    locale = Locale.get_default()
    topics = {}
    for name in BLOG_TOPIC_NAMES:
        slug = slugify(name)
        tag, _ = Tag.objects.update_or_create(
            slug=slug,
            locale=locale,
            defaults={"name": name},
        )
        topics[slug] = tag
    return topics


def get_blog_article_content(image) -> list:
    """Return article content using all available block types."""
    return [
        {
            "type": "text",
            "value": f'<p data-block-key="aaa11111">{LOREM_IPSUM}</p>',
            "id": "11111111-1111-1111-1111-111111111111",
        },
        {
            "type": "media",
            "value": [
                {
                    "type": "image",
                    "value": {
                        "image": image.id,
                        "settings": {
                            "dark_mode_image": None,
                            "mobile_image": None,
                            "dark_mode_mobile_image": None,
                        },
                    },
                    "id": "22222222-2222-2222-2222-222222222222",
                }
            ],
            "id": "33333333-3333-3333-3333-333333333333",
        },
        {
            "type": "code",
            "value": {
                "language": "python",
                "code": "print('Hello, Firefox!')",
            },
            "id": "44444444-4444-4444-4444-444444444444",
        },
        {
            "type": "quote",
            "value": {
                "quote": '<p data-block-key="bbb22222">The web is for everyone.</p>',
                "author": "Mozilla Foundation",
            },
            "id": "55555555-5555-5555-5555-555555555555",
        },
    ]


def _create_blog_article(
    *,
    index_page: BlogIndexPage,
    title: str,
    slug: str,
    featured: bool,
    topic: Tag,
    tags: list[Tag],
    image,
    featured_image,
    description: str,
    content: list,
) -> BlogArticlePage:
    article = BlogArticlePage.objects.filter(slug=slug).first()
    if not article:
        article = BlogArticlePage(title=title, slug=slug, featured_image=featured_image, topic=topic)
        index_page.add_child(instance=article)

    article.title = title
    article.featured = featured
    article.featured_image = featured_image
    article.topic = topic
    article.image = image
    article.description = description
    article.content = content
    article.save_revision().publish()
    article.tags.set(tags)

    return article


def get_blog_index_page() -> BlogIndexPage:
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = BlogIndexPage.objects.filter(slug="test-blog-index").first()
    if not index_page:
        index_page = BlogIndexPage(slug="test-blog-index", title="Blog Test Page")
        root_page.add_child(instance=index_page)
        index_page.save_revision().publish()
    return index_page


def get_blog_pages() -> list[BlogArticlePage]:
    """
    Create a blog index page with enough articles to cover all index page sections:
    - 5 featured articles: 1 hero (media+content) + 4 illustration cards
    - 12 non-featured articles: spans two pages of pagination (10 per page)

    All articles use all available content block types: text, media, code, quote.
    """
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
    topics = get_blog_topics()
    index_page = get_blog_index_page()
    content = get_blog_article_content(image)

    topic_list = list(topics.values())
    articles = []

    for i in range(1, NUM_FEATURED + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article_tags = topic_list[:2]
        article = _create_blog_article(
            index_page=index_page,
            title=f"Featured Blog Article {i}",
            slug=f"test-featured-blog-article-{i}",
            featured=True,
            topic=topic,
            tags=article_tags,
            image=image,
            featured_image=mobile_image,
            description=f'<p data-block-key="feat{i:05d}">Description for featured article {i}.</p>',
            content=content,
        )
        articles.append(article)

    for i in range(1, NUM_REGULAR + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article_tags = [topic_list[i % len(topic_list)]]
        article = _create_blog_article(
            index_page=index_page,
            title=f"Regular Blog Article {i}",
            slug=f"test-regular-blog-article-{i}",
            featured=False,
            topic=topic,
            tags=article_tags,
            image=dark_image,
            featured_image=dark_mobile_image,
            description=f'<p data-block-key="reg0{i:05d}">Description for regular article {i}.</p>',
            content=content,
        )
        articles.append(article)

    return articles
