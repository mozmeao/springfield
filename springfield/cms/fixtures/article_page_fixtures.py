# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_article_index_test_page, get_placeholder_images
from springfield.cms.fixtures.snippet_fixtures import get_download_firefox_cta_snippet
from springfield.cms.models import ArticleDetailPage, SpringfieldImage

LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
)


def create_article(
    title: str,
    slug: str,
    featured: bool,
    description: str,
    content_blocks: list,
    image: SpringfieldImage,
    icon: SpringfieldImage,
    tag: str,
    link_text: str,
    featured_image: SpringfieldImage,
    cta_field: list,
) -> ArticleDetailPage:
    index_page = get_article_index_test_page()

    article = ArticleDetailPage.objects.filter(slug=slug).first()
    if not article:
        article = ArticleDetailPage(
            title=title,
            slug=slug,
        )
        index_page.add_child(instance=article)

    article.featured = featured
    article.image = image
    article.featured_image = featured_image
    article.icon = icon
    article.featured_tag = tag
    article.link_text = link_text
    article.description = description
    article.content = [{"type": "text", "value": "".join(content_blocks)}]
    article.call_to_action = cta_field
    article.save_revision().publish()

    return article


def get_article_pages():
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
    cta_snippet = get_download_firefox_cta_snippet()
    cta_field = [
        {
            "type": "download_firefox",
            "value": cta_snippet.id,
        }
    ]
    p_keys = ["c1bc4d7eadf0", "0b474f02", "d3fd4d86", "83cdc1bc", "4d7eadf0"]

    featured_article_1 = create_article(
        title="Test Featured Article 1",
        slug="test-featured-article-1",
        featured=True,
        description=(
            '<p data-block-key="c1bc4d7eadf0">This is a description for Test Featured Article 1. It provides an overview of the article content.</p>'
        ),
        content_blocks=[f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:3]],
        image=image,
        featured_image=dark_mobile_image,
        icon=mobile_image,
        tag="Tag 1",
        link_text="See Featured 1",
        cta_field=cta_field,
    )

    featured_article_2 = create_article(
        title="Test Featured Article 2",
        slug="test-featured-article-2",
        featured=True,
        description=(
            '<p data-block-key="c1bc4d7eadf0">This is a description for Test Featured Article 2. It provides an overview of the article content.</p>'
        ),
        content_blocks=[f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:4]],
        image=dark_image,
        featured_image=mobile_image,
        icon=dark_mobile_image,
        tag="Tag 2",
        link_text="See Featured 2",
        cta_field=cta_field,
    )
    regular_article_1 = create_article(
        title="Test Regular Article 1",
        slug="test-regular-article-1",
        featured=False,
        description=(
            '<p data-block-key="c1bc4d7eadf0">This is a description for Test Regular Article 1. It provides an overview of the article content.</p>'
        ),
        content_blocks=[f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:2]],
        image=image,
        featured_image=dark_mobile_image,
        icon=mobile_image,
        tag="Tag 1",
        link_text="See Regular 1",
        cta_field=cta_field,
    )

    regular_article_2 = create_article(
        title="Test Regular Article 2",
        slug="test-regular-article-2",
        featured=False,
        description=(
            '<p data-block-key="c1bc4d7eadf0">This is a description for Test Regular Article 2. It provides an overview of the article content.</p>'
        ),
        content_blocks=[f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:3]],
        image=image,
        featured_image=mobile_image,
        icon=image,
        tag="Tag 2",
        link_text="See Regular 2",
        cta_field=cta_field,
    )

    return [
        featured_article_1,
        featured_article_2,
        regular_article_1,
        regular_article_2,
    ]
