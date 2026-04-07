# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.text import slugify

from wagtail.models import Locale, Site

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import BlogArticlePage, BlogIndexPage, Tag

LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

_LOREM_WORDS = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore".split()
_LOREM_SENTENCES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
]


def _title(n_words):
    return " ".join(_LOREM_WORDS[:n_words]).capitalize()


def _desc(key, n_sentences):
    return f'<p data-block-key="{key}">{" ".join(_LOREM_SENTENCES[:n_sentences])}</p>'


# Titles: varying word counts (1–13 words) to stress-test layout
FEATURED_TITLES = [_title(n) for n in (3, 7, 1, 9, 5)]
REGULAR_TITLES = [_title(n) for n in (5, 13, 1, 11, 3, 9, 7, 1, 13, 5, 11, 3)]
PRIVACY_EXTRA_FEATURED_TITLES = [_title(n) for n in (7, 11, 3)]
PRIVACY_EXTRA_REGULAR_TITLES = [_title(n) for n in (9, 1, 13, 5, 7, 3, 11, 9)]

# Descriptions: varying sentence counts (1–3) to stress-test layout
FEATURED_DESCRIPTIONS = [_desc(f"ft{i:04d}", n) for i, n in enumerate((1, 2, 3, 1, 2), start=1)]
REGULAR_DESCRIPTIONS = [_desc(f"rt{i:04d}", n) for i, n in enumerate((2, 1, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3), start=1)]
PRIVACY_EXTRA_FEATURED_DESCRIPTIONS = [_desc(f"pf{i:04d}", n) for i, n in enumerate((2, 3, 1), start=1)]
PRIVACY_EXTRA_REGULAR_DESCRIPTIONS = [_desc(f"pr{i:04d}", n) for i, n in enumerate((1, 3, 2, 1, 3, 2, 1, 3), start=1)]

# 5 featured + 3 extra Privacy featured + 12 regular + 8 extra Privacy regular = 28 total articles
NUM_FEATURED = 5
NUM_LIST_ARTICLES = 23  # articles in the paginated list (20 regular + 3 overflow featured)
NUM_FEATURED_INDEX_SHOWN = 8  # articles in index page featured_articles StreamField


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
    description: str,
    content: list,
) -> BlogArticlePage:
    article = BlogArticlePage.objects.filter(slug=slug).first()
    if not article:
        article = BlogArticlePage(title=title, slug=slug, topic=topic)
        index_page.add_child(instance=article)

    article.title = title
    article.featured = featured
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
    Create a blog index page with articles covering all sections:
    - 8 featured: 5 spread across topics + 3 extra for Privacy
      (Privacy gets 4 total: 1 hero + 3 cards on its topic page)
    - 20 non-featured: 12 spread across topics + 8 extra for Privacy
      (Privacy gets 11 total: triggers pagination on its topic page)

    All articles use all available content block types: text, media, code, quote.
    """
    image, dark_image, *_ = get_placeholder_images()
    topics = get_blog_topics()
    index_page = get_blog_index_page()
    content = get_blog_article_content(image)

    topic_list = list(topics.values())
    privacy = topics["privacy"]
    articles = []

    # One featured article per topic (5 total)
    for i in range(1, len(topic_list) + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article = _create_blog_article(
            index_page=index_page,
            title=FEATURED_TITLES[i - 1],
            slug=f"test-featured-blog-article-{i}",
            featured=True,
            topic=topic,
            tags=topic_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[i - 1],
            content=content,
        )
        articles.append(article)

    # 3 extra featured articles for Privacy (total Privacy featured: 4)
    for i, (title, description) in enumerate(zip(PRIVACY_EXTRA_FEATURED_TITLES, PRIVACY_EXTRA_FEATURED_DESCRIPTIONS), start=1):
        article = _create_blog_article(
            index_page=index_page,
            title=title,
            slug=f"test-privacy-extra-featured-{i}",
            featured=True,
            topic=privacy,
            tags=topic_list[:2],
            image=image,
            description=description,
            content=content,
        )
        articles.append(article)

    # 12 regular articles spread across all topics
    for i in range(1, len(REGULAR_TITLES) + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article = _create_blog_article(
            index_page=index_page,
            title=REGULAR_TITLES[i - 1],
            slug=f"test-regular-blog-article-{i}",
            featured=False,
            topic=topic,
            tags=[topic_list[i % len(topic_list)]],
            image=dark_image,
            description=REGULAR_DESCRIPTIONS[i - 1],
            content=content,
        )
        articles.append(article)

    # 8 extra regular articles for Privacy (total Privacy regular: 11)
    for i, (title, description) in enumerate(zip(PRIVACY_EXTRA_REGULAR_TITLES, PRIVACY_EXTRA_REGULAR_DESCRIPTIONS), start=1):
        article = _create_blog_article(
            index_page=index_page,
            title=title,
            slug=f"test-privacy-extra-regular-{i}",
            featured=False,
            topic=privacy,
            tags=[topic_list[i % len(topic_list)]],
            image=dark_image,
            description=description,
            content=content,
        )
        articles.append(article)

    def _article_block(article, block_id, block_type="article"):
        return {
            "type": block_type,
            "value": {
                "article": article.pk,
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
            "id": block_id,
        }

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
    index_page.featured_articles = [_article_block(a, f"feat0000-0000-0000-0000-{i:012d}") for i, a in enumerate(articles[:8], start=1)]
    index_page.cards_lists = [
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00001">More Articles 1</p>',
                "articles": [
                    _article_block(a, f"cl010000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[8:11], start=1)
                ],
            },
            "id": "cl000001-0000-0000-0000-000000000001",
        },
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00002">More Articles 2</p>',
                "articles": [
                    _article_block(a, f"cl020000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[11:13], start=1)
                ],
            },
            "id": "cl000002-0000-0000-0000-000000000002",
        },
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00003">More Articles 3</p>',
                "articles": [
                    _article_block(a, f"cl030000-0000-0000-0000-{i:012d}", block_type="item") for i, a in enumerate(articles[13:17], start=1)
                ],
            },
            "id": "cl000003-0000-0000-0000-000000000003",
        },
    ]
    index_page.save_revision().publish()

    return articles
