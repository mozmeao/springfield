# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import get_article_index_test_page, get_placeholder_images
from springfield.cms.fixtures.snippet_fixtures import get_download_firefox_cta_snippet
from springfield.cms.models import ArticleDetailPage

LOREM_IPSUM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
)


def get_article_pages():
    index_page = get_article_index_test_page()
    image, dark_image, _, _ = get_placeholder_images()
    cta_snippet = get_download_firefox_cta_snippet()
    cta_field = [
        {
            "type": "download_firefox",
            "value": cta_snippet.id,
        }
    ]
    p_keys = ["c1bc4d7eadf0", "0b474f02", "d3fd4d86", "83cdc1bc", "4d7eadf0"]

    featured_article_1 = ArticleDetailPage.objects.filter(slug="test-featured-article-1").first()
    if not featured_article_1:
        featured_article_1 = ArticleDetailPage(
            title="Test Featured Article 1",
            slug="test-featured-article-1",
        )
        index_page.add_child(instance=featured_article_1)

    featured_article_1.featured = True
    featured_article_1.image = image
    featured_article_1.description = (
        '<p data-block-key="c1bc4d7eadf0">This is a description for Test Featured Article 1. It provides an overview of the article content.</p>'
    )
    featured_article_1.content = "".join(f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:3])
    featured_article_1.call_to_action = cta_field
    featured_article_1.save_revision().publish()

    featured_article_2 = ArticleDetailPage.objects.filter(slug="test-featured-article-2").first()
    if not featured_article_2:
        featured_article_2 = ArticleDetailPage(
            title="Test Featured Article 2",
            slug="test-featured-article-2",
        )
        index_page.add_child(instance=featured_article_2)

    featured_article_2.featured = True
    featured_article_2.image = dark_image
    featured_article_2.description = (
        '<p data-block-key="c1bc4d7eadf0">This is a description for Test Featured Article 2. It provides an overview of the article content.</p>'
    )
    featured_article_2.content = "".join(f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:4])
    featured_article_2.call_to_action = cta_field
    featured_article_2.save_revision().publish()

    regular_article_1 = ArticleDetailPage.objects.filter(slug="test-regular-article-1").first()
    if not regular_article_1:
        regular_article_1 = ArticleDetailPage(
            title="Test Regular Article 1",
            slug="test-regular-article-1",
        )
        index_page.add_child(instance=regular_article_1)

    regular_article_1.featured = False
    regular_article_1.image = image
    regular_article_1.description = (
        '<p data-block-key="c1bc4d7eadf0">This is a description for Test Regular Article 1. It provides an overview of the article content.</p>'
    )
    regular_article_1.content = "".join(f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:2])
    regular_article_1.call_to_action = cta_field
    regular_article_1.save_revision().publish()

    regular_article_2 = ArticleDetailPage.objects.filter(slug="test-regular-article-2").first()
    if not regular_article_2:
        regular_article_2 = ArticleDetailPage(
            title="Test Regular Article 2",
            slug="test-regular-article-2",
        )
        index_page.add_child(instance=regular_article_2)

    regular_article_2.featured = False
    regular_article_2.image = image
    regular_article_2.description = (
        '<p data-block-key="c1bc4d7eadf0">This is a description for Test Regular Article 2. It provides an overview of the article content.</p>'
    )
    regular_article_2.content = "".join(f"<p data-block-key='{key}'>{LOREM_IPSUM}</p>" for key in p_keys[:3])
    regular_article_2.call_to_action = cta_field
    regular_article_2.save_revision().publish()

    return [
        featured_article_1,
        featured_article_2,
        regular_article_1,
        regular_article_2,
    ]
