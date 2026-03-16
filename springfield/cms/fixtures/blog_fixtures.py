# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.text import slugify

from wagtail.models import Locale, Site

from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.models import BlogArticlePage, BlogIndexPage, Tag

LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

BLOG_TOPIC_NAMES = ["Privacy", "Security", "Performance", "Tips", "Open Source"]

FEATURED_TITLES = [
    "How Firefox Protects Your Privacy Online",
    "The Future of Web Security",
    "Faster Browsing: What's New in Firefox",
    "Essential Tips for a Better Web Experience",
    "Why Open Source Matters More Than Ever",
]

REGULAR_TITLES = [
    "Understanding Tracking Protection",
    "A Deep Dive into Browser Fingerprinting and What You Can Do About It",
    "Speed",
    "Ten Simple Tips to Stay Safe While Browsing the Web Every Day",
    "Contributing to Open Source for the First Time",
    "Firefox's Private Browsing Mode Explained in Detail",
    "Phishing Attacks: How to Spot and Avoid Them",
    "Memory",
    "Customizing Firefox: Extensions, Themes, and Hidden Settings Worth Knowing",
    "The History and Philosophy of Open Source Software",
    "Do Not Track and Global Privacy Control: What They Mean for You",
    "Zero-Day Vulnerabilities and How Browsers Respond",
]

FEATURED_DESCRIPTIONS = [
    '<p data-block-key="fd00001">Firefox includes built-in tracking protection that blocks thousands of trackers by default, '
    "keeping your browsing private.</p>",
    '<p data-block-key="fd00002">As threats evolve, so does Firefox. Here\'s a look at the latest security features designed to keep '
    "you safe on the modern web.</p>",
    "<p data-block-key=\"fd00003\">We've shipped significant performance improvements in the latest release. Here's what changed and "
    "why it matters.</p>",
    '<p data-block-key="fd00004">Small changes to how you browse can make a big difference. These tips will help you get more out of '
    "Firefox every day.</p>",
    '<p data-block-key="fd00005">Open source software powers much of the internet. We explore why transparency and community matter '
    "more than ever in today's digital landscape, and how Firefox embodies those values in everything it ships.</p>",
]

REGULAR_DESCRIPTIONS = [
    '<p data-block-key="rd00001">Firefox\'s Enhanced Tracking Protection stops social media trackers, cross-site cookies, fingerprinters, '
    "and cryptominers automatically.</p>",
    '<p data-block-key="rd00002">Browser fingerprinting is a subtle but powerful way advertisers track you without cookies. '
    "Learn how it works, what data gets collected, and the steps you can take to reduce your digital footprint across the web.</p>",
    '<p data-block-key="rd00003">Firefox is fast.</p>',
    '<p data-block-key="rd00004">From using a password manager and enabling two-factor authentication to keeping your browser updated and '
    "being cautious with extensions, these ten practices will meaningfully reduce your exposure to common online threats.</p>",
    '<p data-block-key="rd00005">Opening your first pull request can feel daunting. This guide walks you through finding a project, '
    "understanding the contribution workflow, and making a change you can be proud of.</p>",
    "<p data-block-key=\"rd00006\">Private Browsing in Firefox doesn't save your history, cookies, or form data locally — but it's not a "
    "full anonymity tool. Here's what it does and doesn't protect against, and when you should use it.</p>",
    '<p data-block-key="rd00007">Phishing emails and websites are getting harder to spot. Learn the tell-tale signs of a phishing attempt '
    "and the browser features that can help warn you before it's too late.</p>",
    "<p data-block-key=\"rd00008\">We've reduced Firefox's memory usage.</p>",
    '<p data-block-key="rd00009">Firefox is endlessly customizable. From productivity-boosting extensions to one-click theme changes and '
    "about:config tweaks that power users swear by, here's a tour of the best personalization options available to you right now.</p>",
    '<p data-block-key="rd00010">From the GNU Manifesto to Linux, Git, and Firefox itself, we trace the ideological roots of free and '
    "open source software and explain why the movement's founding principles remain as relevant today as they were decades ago.</p>",
    '<p data-block-key="rd00011">Do Not Track was the first attempt to let users opt out of tracking. Global Privacy Control is its '
    "more enforceable successor. We explain what each signal does, which sites respect it, and how to enable both in Firefox.</p>",
    '<p data-block-key="rd00012">When a zero-day is discovered, browser vendors race to patch it before attackers exploit it at scale. '
    "Here's how the vulnerability disclosure process works and what Firefox does to ship fixes fast.</p>",
]

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
            title=FEATURED_TITLES[i - 1],
            slug=f"test-featured-blog-article-{i}",
            featured=True,
            topic=topic,
            tags=article_tags,
            image=image,
            featured_image=mobile_image,
            description=FEATURED_DESCRIPTIONS[i - 1],
            content=content,
        )
        articles.append(article)

    for i in range(1, NUM_REGULAR + 1):
        topic = topic_list[(i - 1) % len(topic_list)]
        article_tags = [topic_list[i % len(topic_list)]]
        article = _create_blog_article(
            index_page=index_page,
            title=REGULAR_TITLES[i - 1],
            slug=f"test-regular-blog-article-{i}",
            featured=False,
            topic=topic,
            tags=article_tags,
            image=dark_image,
            featured_image=dark_mobile_image,
            description=REGULAR_DESCRIPTIONS[i - 1],
            content=content,
        )
        articles.append(article)

    return articles
