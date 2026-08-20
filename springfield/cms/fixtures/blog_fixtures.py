# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import date

from django.utils.text import slugify

from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import get_flare_pages_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTag, BlogTopic, BlogTopicPage
from springfield.cms.models.pages import HeroStyle

LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

IMAGE_CAPTION = (
    '<p data-block-key="ccc33333">A caption below the image, using <b>bold</b>, <i>italic</i> and a <a href="https://www.mozilla.org/">link</a>.</p>'
)

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

BLOG_AUTHOR_NAMES = ["Ada Lovelace", "Grace Hopper", "Alan Turing"]

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

# Slugs of the articles that demonstrate one hero style or the listing image each.
LARGE_IMAGE_ARTICLE_SLUG = "test-hero-large-image-article"
TEXT_ONLY_ARTICLE_SLUG = "test-hero-text-only-article"
VIDEO_ARTICLE_SLUG = "test-hero-video-article"
LISTING_IMAGE_ARTICLE_SLUG = "test-listing-image-article"
BOTTOM_BANNER_ARTICLE_SLUG = "test-bottom-banner-article"

# 5 across topics + 3 extra Privacy + 12 across topics + 8 extra Privacy = 28,
# plus the 5 hero style / listing image / bottom banner demonstrations = 33 total articles
NUM_LIST_ARTICLES = 33
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


def get_blog_authors() -> dict[str, BlogAuthor]:
    """Author snippets for article bylines, keyed by slug."""
    locale = Locale.get_default()
    authors = {}
    for name in BLOG_AUTHOR_NAMES:
        slug = slugify(name)
        author, _created = BlogAuthor.objects.update_or_create(
            slug=slug,
            locale=locale,
            defaults={"name": name},
        )
        authors[slug] = author
    return authors


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


def get_bottom_banner_stream() -> list[dict]:
    """StreamField data for BlogArticlePage.bottom_banner: a single default banner."""
    return [
        {
            "type": "banner",
            "value": {
                "settings": {
                    "theme": "default",
                    "media_after": False,
                    "show_to": SHOW_TO_ALL,
                    "anchor_id": "",
                    "slim": False,
                    "remove_border_radius": False,
                    "centralize_content": False,
                },
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="bban0001">Enjoying this article?</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "rich_text",
                        "id": "bban0001-0000-0000-0000-000000000002",
                        "value": '<p data-block-key="bban0002">Subscribe to get more like this in your inbox.</p>',
                    },
                ],
            },
            "id": "bban0000-0000-0000-0000-000000000001",
        }
    ]


def create_blog_article(
    *,
    index_page: BlogIndexPage,
    title: str,
    slug: str,
    topic: BlogTopic,
    tags: list[BlogTag],
    image,
    description: str,
    content: list,
    authors: list[BlogAuthor] | None = None,
    hero_style: str | None = None,
    hero_video: list | None = None,
    listing_image=None,
    updated_date=None,
    hide_dates: bool = False,
    bottom_banner: list | None = None,
) -> BlogArticlePage:
    if hero_style is None:
        hero_style = HeroStyle.STANDARD_IMAGE if image else HeroStyle.TEXT_ONLY

    article = get_or_create_page(
        BlogArticlePage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": title,
            "topic": topic,
            "hero_style": hero_style,
            "image": image,
            "hero_video": hero_video or [],
        },
    )

    article.title = title
    article.topic = topic
    article.hero_style = hero_style
    article.image = image
    article.listing_image = listing_image
    article.updated_date = updated_date
    article.hide_dates = hide_dates
    article.description = description
    article.content = content
    article.bottom_banner = bottom_banner or []
    article.tags.set(tags)
    if hero_video is not None:
        article.hero_video = hero_video
    if authors:
        article.article_authors.set([BlogArticleAuthor(author=author) for author in authors])
    article.save_revision().publish()
    article.refresh_from_db()

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
    Create a blog index page with 32 articles:
    - 5 spread across topics + 3 extra for Privacy (Privacy gets 4 total)
    - 12 spread across topics + 8 extra for Privacy
      (Privacy gets 11 total: triggers pagination on its topic page)
    - 5 demonstrating the large image, text only and video hero styles, a
      listing image that differs from the featured image, and a bottom banner

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
    author_list = list(get_blog_authors().values())
    # Featured articles 1 and 2 are the multi-author cases and 3 has a single
    # author, so the fixture site shows every byline state. The rest stay
    # uncredited.
    featured_authors = {
        1: author_list[:2],
        2: author_list,
        3: author_list[:1],
    }
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
            authors=featured_authors.get(i),
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
            topic=privacy,
            tags=[tag_list[i % len(tag_list)]],
            image=dark_image,
            description=description,
            content=plain_content,
        )
        articles.append(article)

    articles.append(
        create_blog_article(
            index_page=index_page,
            title="Hero style: large featured image",
            slug=LARGE_IMAGE_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[0],
            content=captioned_content,
            hero_style=HeroStyle.LARGE_IMAGE,
            authors=author_list[:1],
            updated_date=date(2026, 6, 12),
        )
    )
    articles.append(
        create_blog_article(
            index_page=index_page,
            title="Hero style: no image, text only",
            slug=TEXT_ONLY_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=None,
            description=FEATURED_DESCRIPTIONS[1],
            content=plain_content,
            hero_style=HeroStyle.TEXT_ONLY,
            hide_dates=True,
        )
    )
    articles.append(
        create_blog_article(
            index_page=index_page,
            title="Hero style: featured video",
            slug=VIDEO_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[2],
            content=plain_content,
            hero_style=HeroStyle.VIDEO,
            hero_video=[
                {
                    "type": "video",
                    "value": {
                        "video_url": "https://www.youtube.com/watch?v=firefoxdemo",
                        "alt": "A Firefox demo",
                        "poster": image.pk,
                    },
                    "id": "herovid0-0000-0000-0000-000000000001",
                }
            ],
        )
    )
    articles.append(
        create_blog_article(
            index_page=index_page,
            title="Listing image override",
            slug=LISTING_IMAGE_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[3],
            content=plain_content,
            listing_image=dark_image,
        )
    )
    articles.append(
        create_blog_article(
            index_page=index_page,
            title="Bottom banner",
            slug=BOTTOM_BANNER_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[4],
            content=plain_content,
            bottom_banner=get_bottom_banner_stream(),
        )
    )

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
