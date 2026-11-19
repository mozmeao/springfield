# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import date

from django.utils.text import slugify

from wagtail.models import Locale

from springfield.blog.models import BlogArticleAuthor, BlogArticlePage, BlogAuthor, BlogIndexPage, BlogTag, BlogTopic, BlogTopicPage
from springfield.blog.models.pages import HeroStyle
from springfield.cms.fixtures.base_fixtures import SHOW_TO_ALL, get_flare_pages_docs_page, get_or_create_page, get_placeholder_images

ARTICLE_BODY = (
    "Firefox is built by a non-profit, so the browser answers to the people who use it, not to advertisers. "
    "That principle shapes every feature in this release, from the way tabs are organized to the trackers quietly "
    "blocked in the background. Read on for the details, and the handful of settings worth checking on your own device."
)

IMAGE_CAPTION = (
    '<p data-block-key="ccc33333">A caption below the image, using <b>bold</b>, <i>italic</i> and a <a href="https://www.mozilla.org/">link</a>.</p>'
)

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

BLOG_AUTHOR_NAMES = ["Ada Lovelace", "Grace Hopper", "Alan Turing"]

BLOG_SENTENCES = [
    "Here's what changed in the latest release, and why it's worth your attention.",
    "We walk through the feature step by step and show you exactly where to find it.",
    "A few small settings can make a real difference to your everyday browsing.",
]


def get_description(key, n_sentences):
    return f'<p data-block-key="{key}">{" ".join(BLOG_SENTENCES[:n_sentences])}</p>'


# Titles deliberately span one word to a full sentence, to stress-test how the
# listing and card layouts handle very short and very long headlines.
FEATURED_TITLES = [
    "Faster browsing, less memory",
    "How Firefox blocks trackers before they even load",
    "Containers",
    "Everything new in the latest Firefox release, from tabs to translations",
    "Your downloads, now clutter-free",
]
REGULAR_TITLES = [
    "Set Firefox as your default",
    "A practical guide to tightening your privacy settings without breaking the sites you love",
    "Sync",
    "What picture-in-picture can do that you probably haven't tried yet",
    "Meet Firefox View",
    "Five extensions our engineers actually keep installed",
    "Reader mode makes long articles easier",
    "Bookmarks",
    "Behind the scenes of the redesign that made Firefox feel noticeably quicker this year",
    "Tips for taming your tabs",
    "How we think about privacy when we build a new feature",
    "Protect your passwords",
]
PRIVACY_EXTRA_FEATURED_TITLES = [
    "Total Cookie Protection, explained in plain language",
    "Why we strip tracking parameters from the links you copy and share",
    "Private browsing, improved",
]
PRIVACY_EXTRA_REGULAR_TITLES = [
    "How to review and clear the data Firefox stores",
    "Telemetry",
    "A closer look at fingerprinting, the quiet tracking technique most people never notice",
    "Turn on DNS over HTTPS",
    "Your privacy report, now easier to read",
    "Block third-party cookies",
    "What Firefox sends to Mozilla, and the controls you have over it",
    "Stay private with the built-in private window shortcut",
]

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
QUOTES_ARTICLE_SLUG = "test-quotes-article"

NUM_LIST_ARTICLES = 33
NUM_FEATURED_INDEX_SHOWN = 4  # articles in index page featured_articles StreamField


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
        "image_alt": "A placeholder image used for testing purposes",
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
            "value": f'<p data-block-key="aaa11111">{ARTICLE_BODY}</p>',
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
                    "image_alt": "",
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
    related_articles: list | None = None,
) -> BlogArticlePage:
    if hero_style is None:
        hero_style = HeroStyle.STANDARD_IMAGE if image else HeroStyle.TEXT_ONLY
    placeholder_alt = "A numbered grid, standing in for a real image"

    article = get_or_create_page(
        BlogArticlePage,
        slug=slug,
        parent=index_page,
        defaults={
            "title": title,
            "topic": topic,
            "hero_style": hero_style,
            "image": image,
            "image_alt": placeholder_alt,
            "hero_video": hero_video or [],
        },
    )

    article.title = title
    article.topic = topic
    article.hero_style = hero_style
    article.image = image
    article.image_alt = placeholder_alt
    article.listing_image = listing_image
    article.listing_image_alt = placeholder_alt
    article.updated_date = updated_date
    article.hide_dates = hide_dates
    article.description = description
    article.content = content
    article.bottom_banner = bottom_banner or []
    article.related_articles = related_articles or []
    article.tags.set(tags)
    if hero_video is not None:
        article.hero_video = hero_video
    if authors:
        article.article_authors.set([BlogArticleAuthor(author=author) for author in authors])
    article.save_revision().publish()
    article.refresh_from_db()

    return article


def get_blog_index_page(slug="test-blog-index") -> BlogIndexPage:
    root_page = get_flare_pages_docs_page()
    index_page = get_or_create_page(
        BlogIndexPage,
        slug=slug,
        parent=root_page,
        defaults={"title": "Blog"},
    )
    index_page.title = "Blog"
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
      alongside two hand-picked related articles

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

    # Feature-demo articles continue the numbering after the topic hubs so they
    # cluster with them at the top of the Blog listing.
    hero_start = len(BLOG_TOPIC_NAMES) + 1
    articles.append(
        create_blog_article(
            index_page=index_page,
            title=f"{hero_start:02d}. Hero style: large featured image",
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
            title=f"{hero_start + 1:02d}. Hero style: no image, text only",
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
            title=f"{hero_start + 2:02d}. Hero style: featured video",
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
            title=f"{hero_start + 3:02d}. Listing image override",
            slug=LISTING_IMAGE_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[3],
            content=plain_content,
            listing_image=dark_image,
        )
    )
    # Picks from another topic, tagged differently, so neither could have been
    # related automatically and the editor's choice is visible on the page.
    articles_by_slug = {article.slug: article for article in articles}
    hand_picked = [articles_by_slug[f"test-regular-blog-article-{number}"] for number in (3, 4)]
    articles.append(
        create_blog_article(
            index_page=index_page,
            title=f"{hero_start + 4:02d}. Bottom banner",
            slug=BOTTOM_BANNER_ARTICLE_SLUG,
            topic=privacy,
            tags=tag_list[:2],
            image=image,
            description=FEATURED_DESCRIPTIONS[4],
            content=plain_content,
            bottom_banner=get_bottom_banner_stream(),
            related_articles=[
                blog_article_block(article, f"rel00000-0000-0000-0000-{position:012d}") for position, article in enumerate(hand_picked, start=1)
            ],
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
    index_page.featured_topics = featured_topics_stream([topics["tips"], topics["security"], topics["privacy"]])
    index_page.featured_articles = [blog_article_block(a, f"feat0000-0000-0000-0000-{i:012d}") for i, a in enumerate(articles[:4], start=1)]
    index_page.article_sections = [
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00001">Privacy</p>',
                "source": [{"type": "topic", "value": topics["privacy"].pk, "id": "src00001-0000-0000-0000-000000000001"}],
                "count": 3,
                "link_label": "View all Privacy",
            },
            "id": "cl000001-0000-0000-0000-000000000001",
        },
        {
            "type": "cards_list",
            "value": {
                "heading_text": '<p data-block-key="clh00002">Security</p>',
                "source": [{"type": "tag", "value": tags["security"].pk, "id": "src00002-0000-0000-0000-000000000002"}],
                "count": 2,
                "link_label": "View all Security",
            },
            "id": "cl000002-0000-0000-0000-000000000002",
        },
        {
            "type": "latest",
            "value": {"heading_text": '<p data-block-key="clh00003">Recently published</p>', "count": 4, "link_label": "View all"},
            "id": "cl000003-0000-0000-0000-000000000003",
        },
    ]
    index_page.save_revision().publish()

    return articles


def _text(block_id: str, html: str) -> dict:
    return {"type": "text", "value": html, "id": block_id}


def _quote(block_id: str, quote: str, style: str = "", author: str = "", authors_title: str = "") -> dict:
    return {
        "type": "quote",
        "value": {"style": style, "quote": quote, "author": author, "authors_title": authors_title},
        "id": block_id,
    }


def get_blog_quotes_content() -> list:
    """Every quote style and attribution state, between body text, plus quotes typed into rich text."""
    body = f'<p data-block-key="qbody">{BLOG_SENTENCES[0]} {BLOG_SENTENCES[1]} {BLOG_SENTENCES[2]}</p>'
    return [
        _text("quot0001-0000-0000-0000-000000000001", f'<h2 data-block-key="qh001">Standard</h2>{body}'),
        _quote(
            "quot0001-0000-0000-0000-000000000002",
            '<p data-block-key="q0001">“We\'re seeing real conversations, not just complaints.”</p>',
            author="Jon Siddoway",
            authors_title="community manager for Mozilla Connect",
        ),
        _text("quot0001-0000-0000-0000-000000000003", body),
        _quote(
            "quot0001-0000-0000-0000-000000000004",
            '<p data-block-key="q0002">“I loved the idea of incorporating open community feedback earlier into our process.”</p>',
            author="Karen Kim",
        ),
        _text("quot0001-0000-0000-0000-000000000005", body),
        _quote(
            "quot0001-0000-0000-0000-000000000006",
            '<p data-block-key="q0003">“On Mozilla Connect, people share constructive feedback. They explain their problem, suggest a solution.”</p>'
            '<p data-block-key="q0004">“It helps me change my approach.”</p>',
        ),
        _text("quot0001-0000-0000-0000-000000000007", f'{body}<h2 data-block-key="qh002">Pull quote</h2>{body}'),
        _quote(
            "quot0001-0000-0000-0000-000000000008",
            '<p data-block-key="q0005">We wanted a space where people could share ideas and actually get updates on what happened next.</p>',
            style="pull",
            author="Jon Siddoway",
            authors_title="community manager for Mozilla Connect",
        ),
        _text("quot0001-0000-0000-0000-000000000009", body),
        _quote(
            "quot0001-0000-0000-0000-000000000010",
            '<p data-block-key="q0006">The adoption of certain themes increased by more than 200%.</p>',
            style="pull",
        ),
        _text("quot0001-0000-0000-0000-000000000011", f'{body}<h2 data-block-key="qh003">Passage</h2>{body}'),
        _quote(
            "quot0001-0000-0000-0000-000000000012",
            '<p data-block-key="q0007">"Containers is the killer feature."<br/>— @Kaegun</p>'
            '<p data-block-key="q0008">"PIP (picture-in-picture) in every video"<br/>— @JanakXD</p>'
            '<p data-block-key="q0009">"I moved from Opera to Firefox because it was open-source and obeyed most of the standards. '
            'It’s been my default since version 1.5. Why wouldn’t it be?"<br/>— @omarwilley</p>',
            style="passage",
        ),
        _text("quot0001-0000-0000-0000-000000000013", body),
        _quote(
            "quot0001-0000-0000-0000-000000000014",
            '<p data-block-key="q0010"><i>encrypt</i> (verb): to change information from one form to another, especially to hide its meaning</p>',
            style="passage",
            authors_title="Merriam-Webster",
        ),
        _text(
            "quot0001-0000-0000-0000-000000000015",
            f'{body}<h2 data-block-key="qh004">Quotes in rich text</h2>{body}'
            '<blockquote data-block-key="q0011">A quote typed into a text block with the editor’s quote button.</blockquote>'
            f"{body}"
            # The shape imported WordPress posts store: paragraphs and a cite inside the blockquote.
            '<blockquote class="wp-block-quote"><p>“It’s collaborative in the best way.”</p>'
            "<cite>Jon Siddoway, community manager for Mozilla Connect</cite></blockquote>"
            f"{body}",
        ),
    ]


def get_blog_quotes_test_page() -> BlogArticlePage:
    """A blog article showing every quote style, for checking quotes in light and dark."""
    # Continues the Blog numbering after the topic hubs and the five feature-demo articles.
    number = len(BLOG_TOPIC_NAMES) + 6
    return create_blog_article(
        index_page=get_blog_index_page(),
        title=f"{number:02d}. Quote styles",
        slug=QUOTES_ARTICLE_SLUG,
        topic=get_blog_topics()["tips"],
        tags=[],
        image=None,
        description="Standard, pull quote and passage quotes, and quotes typed into rich text.",
        content=get_blog_quotes_content(),
        hero_style=HeroStyle.TEXT_ONLY,
    )


def get_blog_topic_pages() -> list[BlogTopicPage]:
    """A curated hub for every blog topic, each featuring up to four of its articles.

    The titles carry a sequential number so the topic hubs sit above the article
    pages in the Flare Docs listing.
    """
    articles = get_blog_pages()
    index_page = get_blog_index_page()
    topics = get_blog_topics()

    topic_pages = []
    for number, name in enumerate(BLOG_TOPIC_NAMES, start=1):
        slug = slugify(name)
        topic = topics[slug]
        topic_articles = [article for article in articles if article.topic_id == topic.pk][:4]
        # Two digits so the Blog tier still sorts correctly once the numbers reach 10.
        title = f"{number:02d}. {name} (topic hub)"

        topic_page = get_or_create_page(
            BlogTopicPage,
            slug=slug,
            parent=index_page,
            defaults={"title": title, "topic": topic},
        )
        topic_page.title = title
        topic_page.topic = topic
        topic_page.page_heading = [
            {
                "type": "heading",
                "value": {
                    "superheading_text": "",
                    "heading_text": f'<p data-block-key="tph{number:05d}">All things {name}</p>',
                    "subheading_text": "",
                },
                "id": f"tph{number:05d}-0000-0000-0000-000000000001",
            }
        ]
        topic_page.featured_articles = [
            blog_article_block(article, f"tpf{number:05d}-0000-0000-0000-{i:012d}") for i, article in enumerate(topic_articles, start=1)
        ]
        topic_page.save_revision().publish()
        topic_pages.append(topic_page)

    return topic_pages
