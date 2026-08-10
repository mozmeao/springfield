# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.text import slugify

from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.models import BlogArticlePage, BlogIndexPage, BlogTag, BlogTopic, BlogTopicPage

LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

IMAGE_CAPTION = (
    '<p data-block-key="ccc33333">A caption below the image, using <b>bold</b>, <i>italic</i> and a <a href="https://www.mozilla.org/">link</a>.</p>'
)

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

LOREM_WORDS = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore".split()
LOREM_SENTENCES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
]


def get_title(n_words):
    return " ".join(LOREM_WORDS[:n_words]).capitalize()


def get_description(key, n_sentences):
    return f'<p data-block-key="{key}">{" ".join(LOREM_SENTENCES[:n_sentences])}</p>'


# Titles: varying word counts (1–13 words) to stress-test layout
FEATURED_TITLES = [get_title(n) for n in (3, 7, 1, 9, 5)]
REGULAR_TITLES = [get_title(n) for n in (5, 13, 1, 11, 3, 9, 7, 1, 13, 5, 11, 3)]
PRIVACY_EXTRA_FEATURED_TITLES = [get_title(n) for n in (7, 11, 3)]
PRIVACY_EXTRA_REGULAR_TITLES = [get_title(n) for n in (9, 1, 13, 5, 7, 3, 11, 9)]

# Descriptions: varying sentence counts (1–3) to stress-test layout
FEATURED_DESCRIPTIONS = [get_description(f"ft{i:04d}", n) for i, n in enumerate((1, 2, 3, 1, 2), start=1)]
REGULAR_DESCRIPTIONS = [get_description(f"rt{i:04d}", n) for i, n in enumerate((2, 1, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3), start=1)]
PRIVACY_EXTRA_FEATURED_DESCRIPTIONS = [get_description(f"pf{i:04d}", n) for i, n in enumerate((2, 3, 1), start=1)]
PRIVACY_EXTRA_REGULAR_DESCRIPTIONS = [get_description(f"pr{i:04d}", n) for i, n in enumerate((1, 3, 2, 1, 3, 2, 1, 3), start=1)]

# 5 across topics + 3 extra Privacy + 12 across topics + 8 extra Privacy = 28 total articles
NUM_LIST_ARTICLES = 28
NUM_FEATURED_INDEX_SHOWN = 8  # articles in index page featured_articles StreamField


def get_blog_topics() -> dict[str, BlogTopic]:
    locale = Locale.get_default()
    topics = {}
    for name in BLOG_TOPIC_NAMES:
        slug = slugify(name)
        topic, _ = BlogTopic.objects.update_or_create(
            slug=slug,
            locale=locale,
            defaults={"name": name},
        )
        topics[slug] = topic
    return topics


def featured_topics_stream(topics: list[BlogTopic]) -> list[dict]:
    """StreamField data for BlogIndexPage.featured_topics from an ordered list of topics."""
    return [{"type": "topic", "value": topic.pk, "id": f"ftopic00-0000-0000-0000-{i:012d}"} for i, topic in enumerate(topics, start=1)]


def get_blog_tags() -> dict[str, BlogTag]:
    locale = Locale.get_default()
    tags = {}
    for name in BLOG_TOPIC_NAMES:
        slug = slugify(name)
        tag, _ = BlogTag.objects.update_or_create(
            slug=slug,
            locale=locale,
            defaults={"name": name},
        )
        tags[slug] = tag
    return tags


def get_blog_article_content(image, image_caption: str = "") -> list:
    """
    Return article content using all available block types.

    The image is rendered as an Image + Caption block when `image_caption` is
    given, and as a plain Media image block otherwise.
    """
    image_value = {
        "image": image.id,
        "settings": {
            "dark_mode_image": None,
            "mobile_image": None,
            "dark_mode_mobile_image": None,
        },
    }

    if image_caption:
        image_block = {
            "type": "image_caption",
            "value": {
                "image": image_value,
                "caption": image_caption,
            },
            "id": "66666666-6666-6666-6666-666666666666",
        }
    else:
        image_block = {
            "type": "media",
            "value": [
                {
                    "type": "image",
                    "value": image_value,
                    "id": "22222222-2222-2222-2222-222222222222",
                }
            ],
            "id": "33333333-3333-3333-3333-333333333333",
        }

    return [
        {
            "type": "text",
            "value": f'<p data-block-key="aaa11111">{LOREM_IPSUM}</p>',
            "id": "11111111-1111-1111-1111-111111111111",
        },
        image_block,
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


def blog_article_block(article: BlogArticlePage, block_id: str, block_type: str = "article") -> dict:
    """StreamField data for one BlogArticleBlock, with every override left empty."""
    return {
        "type": block_type,
        "value": {
            "article": article.pk,
            "overrides": {
                "image": {
                    "image": None,
                    "settings": {
                        "dark_mode_image": None,
                        "mobile_image": None,
                        "dark_mode_mobile_image": None,
                    },
                },
                "topic": "",
                "title": "",
                "description": "",
                "tags": [],
            },
        },
        "id": block_id,
    }


def create_blog_article(
    *,
    index_page: BlogIndexPage,
    title: str,
    slug: str,
    display_image: bool = False,
    topic: BlogTopic,
    tags: list[BlogTag],
    image,
    description: str,
    content: list,
) -> BlogArticlePage:
    article = get_or_create_page(
        BlogArticlePage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": title,
            "topic": topic,
        },
    )

    article.title = title
    article.display_image = display_image
    article.topic = topic
    article.image = image
    article.description = description
    article.content = content
    article.tags.set(tags)
    article.save_revision().publish()

    return article


def get_blog_index_page() -> BlogIndexPage:
    root_page = get_flare_pages_docs_page()
    index_page = get_or_create_page(
        BlogIndexPage,
        slug="test-blog-index",
        parent=root_page,
        defaults={"title": "Blog"},
    )
    index_page.save_revision().publish()
    return index_page


def get_blog_pages() -> list[BlogArticlePage]:
    """
    Create a blog index page with 28 articles:
    - 5 spread across topics + 3 extra for Privacy (Privacy gets 4 total)
    - 12 spread across topics + 8 extra for Privacy
      (Privacy gets 11 total: triggers pagination on its topic page)

    All articles use all available content block types: text, media or image + caption, code, quote.
    Featured articles carry a captioned image, regular ones a plain image.
    """
    image, dark_image, *_ = get_placeholder_images()
    topics = get_blog_topics()
    index_page = get_blog_index_page()
    captioned_content = get_blog_article_content(image, image_caption=IMAGE_CAPTION)
    plain_content = get_blog_article_content(image)

    topic_list = list(topics.values())
    privacy = topics["privacy"]
    tags = get_blog_tags()
    tag_list = list(tags.values())
    articles = []

    # 5 articles spread across all topics
    for i in range(1, len(topic_list) + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article = create_blog_article(
            index_page=index_page,
            title=FEATURED_TITLES[i - 1],
            slug=f"test-featured-blog-article-{i}",
            topic=topic,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[i - 1],
            content=captioned_content,
        )
        articles.append(article)

    # 3 extra articles for Privacy (Privacy total: 4)
    for i, (title, description) in enumerate(zip(PRIVACY_EXTRA_FEATURED_TITLES, PRIVACY_EXTRA_FEATURED_DESCRIPTIONS), start=1):
        article = create_blog_article(
            index_page=index_page,
            title=title,
            slug=f"test-privacy-extra-featured-{i}",
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=description,
            content=captioned_content,
        )
        articles.append(article)

    # 12 regular articles spread across all topics
    for i in range(1, len(REGULAR_TITLES) + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article = create_blog_article(
            index_page=index_page,
            title=REGULAR_TITLES[i - 1],
            slug=f"test-regular-blog-article-{i}",
            display_image=(i % 2 == 0),
            topic=topic,
            tags=[tag_list[i % len(tag_list)]],
            image=dark_image,
            description=REGULAR_DESCRIPTIONS[i - 1],
            content=plain_content,
        )
        articles.append(article)

    # 8 extra regular articles for Privacy (total Privacy regular: 11)
    for i, (title, description) in enumerate(zip(PRIVACY_EXTRA_REGULAR_TITLES, PRIVACY_EXTRA_REGULAR_DESCRIPTIONS), start=1):
        article = create_blog_article(
            index_page=index_page,
            title=title,
            slug=f"test-privacy-extra-regular-{i}",
            display_image=(i % 2 == 0),
            topic=privacy,
            tags=[tag_list[i % len(tag_list)]],
            image=dark_image,
            description=description,
            content=plain_content,
        )
        articles.append(article)

    index_page.page_heading = [
        {
            "type": "heading",
            "value": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="ph0001">The Firefox Blog</p>',
                "subheading_text": "",
            },
            "id": "ph000001-0000-0000-0000-000000000001",
        }
    ]
    index_page.more_articles_heading = '<p data-block-key="mah0001">Looking for more?</p>'
    index_page.featured_topics = featured_topics_stream([topics["tips"], topics["security"], topics["privacy"]])
    index_page.featured_articles = [blog_article_block(a, f"feat0000-0000-0000-0000-{i:012d}") for i, a in enumerate(articles[:8], start=1)]
    index_page.cards_lists = [
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00001">More Articles 1</p>',
                "link_label": "View all Privacy",
                "link_filter": "?topic=privacy",
                "articles": [
                    blog_article_block(a, f"cl010000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[8:11], start=1)
                ],
            },
            "id": "cl000001-0000-0000-0000-000000000001",
        },
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00002">More Articles 2</p>',
                "link_label": "View all Security",
                "link_filter": "?topic=security",
                "articles": [
                    blog_article_block(a, f"cl020000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[11:13], start=1)
                ],
            },
            "id": "cl000002-0000-0000-0000-000000000002",
        },
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00003">More Articles 3</p>',
                "link_label": "View all",
                "link_filter": "",
                "articles": [
                    blog_article_block(a, f"cl030000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[13:17], start=1)
                ],
            },
            "id": "cl000003-0000-0000-0000-000000000003",
        },
    ]
    index_page.save_revision().publish()

    return articles


def get_blog_topic_page() -> BlogTopicPage:
    """A curated header for the Privacy topic, featuring its first four articles."""
    articles = get_blog_pages()
    privacy = get_blog_topics()["privacy"]
    privacy_articles = [article for article in articles if article.topic_id == privacy.pk][:4]

    topic_page = get_or_create_page(
        BlogTopicPage,
        slug="privacy",
        parent=get_blog_index_page(),
        defaults={"title": "Privacy", "topic": privacy},
    )
    topic_page.topic = privacy
    topic_page.page_heading = [
        {
            "type": "heading",
            "value": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="tph00001">All things Privacy</p>',
                "subheading_text": "",
            },
            "id": "tph00001-0000-0000-0000-000000000001",
        }
    ]
    topic_page.featured_articles = [
        blog_article_block(article, f"tpf00000-0000-0000-0000-{i:012d}") for i, article in enumerate(privacy_articles, start=1)
    ]
    topic_page.save_revision().publish()

    return articles


def get_blog_topic_page() -> BlogTopicPage:
    """A curated header for the Privacy topic, featuring its first four articles."""
    articles = get_blog_pages()
    privacy = get_blog_topics()["privacy"]
    privacy_articles = [article for article in articles if article.topic_id == privacy.pk][:4]

    topic_page = get_or_create_page(
        BlogTopicPage,
        slug="privacy",
        parent=get_blog_index_page(),
        defaults={"title": "Privacy", "topic": privacy},
    )
    topic_page.topic = privacy
    topic_page.page_heading = [
        {
            "type": "heading",
            "value": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="tph00001">All things Privacy</p>',
                "subheading_text": "",
            },
            "id": "tph00001-0000-0000-0000-000000000001",
        }
    ]
    topic_page.featured_articles = [
        blog_article_block(article, f"tpf00000-0000-0000-0000-{i:012d}") for i, article in enumerate(privacy_articles, start=1)
    ]
    topic_page.save_revision().publish()

    return topic_page
