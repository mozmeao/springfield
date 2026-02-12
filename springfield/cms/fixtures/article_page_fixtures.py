# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_article_index_test_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_download_firefox_cta_snippet, get_tags
from springfield.cms.models import ArticleDetailPage, ArticleThemePage, SpringfieldImage, Tag

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
    icon: str,
    sticker: SpringfieldImage,
    tag: Tag,
    link_text: str,
    featured_image: SpringfieldImage,
    cta_field: list,
) -> ArticleDetailPage:
    index_page = get_article_index_test_page()

    article = ArticleDetailPage.objects.filter(slug=slug).first()
    if not article:
        article = ArticleDetailPage(title=title, slug=slug, image=image)
        index_page.add_child(instance=article)

    article.featured = featured
    article.image = image
    article.featured_image = featured_image
    article.icon = icon
    article.sticker = sticker
    article.tag = tag
    article.link_text = link_text
    article.description = description
    article.content = [{"type": "text", "value": "".join(content_blocks)}]
    article.call_to_action = cta_field
    article.save_revision().publish()

    return article


def get_article_pages():
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
    cta_snippet = get_download_firefox_cta_snippet()
    tags = get_tags()
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
        icon="globe",
        sticker=dark_image,
        tag=tags["security"],
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
        icon="arrow-clockwise",
        sticker=image,
        tag=tags["privacy"],
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
        icon="apple",
        sticker=dark_image,
        tag=tags["performance"],
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
        icon="android",
        sticker=image,
        tag=tags["tips"],
        link_text="See Regular 2",
        cta_field=cta_field,
    )

    return [
        featured_article_1,
        featured_article_2,
        regular_article_1,
        regular_article_2,
    ]


def get_theme_page_intro():
    return {
        "type": "intro",
        "value": {
            "media": [
                {
                    "type": "image",
                    "value": {
                        "image": settings.PLACEHOLDER_IMAGE_ID,
                        "settings": {
                            "dark_mode_image": None,
                            "mobile_image": None,
                            "dark_mode_mobile_image": None,
                        },
                    },
                    "id": "bcc9cdcb-c5e7-4d28-9aba-79fded228fe4",
                }
            ],
            "heading": {
                "superheading_text": '<p data-block-key="aafi8">Protection</p>',
                "heading_text": '<p data-block-key="u6bj0">Your online life belongs</p><p data-block-key="5ji63">to you</p>',
                "subheading_text": '<p data-block-key="l00s0">Protection shouldn’t be a premium feature. With Firefox, it’s built in. '
                "We block trackers automatically, protect your privacy by default, and give you clear visibility into what’s "
                "happening behind the scenes.</p>",
            },
            "buttons": [],
        },
        "id": "3af11135-d051-4819-951e-16d534362260",
    }


def get_theme_page_illustration_cards_section():
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="qf39f">Peace of mind? Piece of cake.</p>',
                "subheading_text": "",
            },
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "illustration_card"},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[0].id,
                                    "overrides": {
                                        "image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                                        "superheading": "Tag override",
                                        "title": '<p data-block-key="njwu5">Title override</p>',
                                        "description": '<p data-block-key="mwjdk">Description override. The image is also different.</p>',
                                        "link_label": "Different label",
                                    },
                                },
                                "id": "422e4683-7693-424d-8022-df8066b97c6e",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[1].id,
                                    "overrides": {
                                        "image": None,
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "1a8ae2f1-56ea-47cd-b0e4-f7cb44c51ed6",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[2].id,
                                    "overrides": {
                                        "image": None,
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "5200d3b2-c955-46f0-9d42-b0adae0925e0",
                            },
                        ],
                    },
                    "id": "b702075e-de54-4ec9-a397-3e8b993cc2e1",
                }
            ],
            "cta": [],
        },
        "id": "2281b654-40f3-419a-8578-b6d7720f5528",
    }


def get_theme_page_icon_cards_section():
    articles = get_article_pages()
    buttons = get_button_variants()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sv9yi">Protection Features</p>',
                "subheading_text": "",
            },
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "icon_card"},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[3].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "book",
                                        "superheading": "",
                                        "title": '<p data-block-key="bcq0b">Different title</p>',
                                        "description": '<p data-block-key="ovybu">Something else about the article. Another sticker too.</p>',
                                        "link_label": "Different label",
                                    },
                                },
                                "id": "2923888c-0045-4c33-9e0f-5da63cc57628",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[2].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "3830dd7a-d08b-4813-b46b-cd08a0c557bd",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[1].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "cc5b422f-c69e-414b-906a-8aae4eef526c",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[0].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "c4c4115c-7564-418a-89e9-171a021c3521",
                            },
                        ],
                    },
                    "id": "20d28bc9-513a-4b66-b46b-c777ddb4637b",
                }
            ],
            "cta": [buttons["secondary"]],
        },
        "id": "30d1681d-a653-44f5-bd28-697317ce2df5",
    }


def get_theme_page_sticker_row_section():
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all"},
            "heading": {"superheading_text": "", "heading_text": '<p data-block-key="sv9yi">More Firefox Features</p>', "subheading_text": ""},
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "sticker_row"},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[2].id,
                                    "overrides": {
                                        "image": settings.PLACEHOLDER_IMAGE_ID,
                                        "superheading": "",
                                        "title": '<p data-block-key="eqmnm">Another title</p>',
                                        "description": '<p data-block-key="5h96k">Different description. Different sticker too.</p>',
                                        "link_label": "New label",
                                    },
                                },
                                "id": "7e9b8e25-e66d-47c7-824d-e501c55db54f",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[3].id,
                                    "overrides": {
                                        "image": None,
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "86e173f7-3a35-4c7d-8078-eb6149a006d6",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[1].id,
                                    "overrides": {
                                        "image": None,
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "baa80b6c-ab78-4fed-98bb-efe32313231b",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[0].id,
                                    "overrides": {
                                        "image": None,
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "b57f37cd-5a41-411b-982f-eea274522b47",
                            },
                        ],
                    },
                    "id": "1f057a70-cabe-4197-8e4e-163b3f898d59",
                }
            ],
            "cta": [],
        },
        "id": "71f8168c-0ee7-4bf4-b12c-755b2670093f",
    }


def get_theme_hub_page_upper_content():
    return [
        {
            "type": "intro",
            "value": {
                "media": [],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="arkm4">Browse with features that put you first</p>',
                    "subheading_text": '<p data-block-key="ffk5g">Most browsers were built to capture your attention and monetize your data. '
                    "Firefox was built to give you control.</p>",
                },
                "buttons": [],
            },
            "id": "929f73bf-d056-42d5-8214-0f6f4a7390aa",
        }
    ]


def get_theme_hub_illustration_cards_section():
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all", "anchor_id": ""},
            "heading": {"superheading_text": "", "heading_text": "", "subheading_text": ""},
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "illustration_card"},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[0].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "1e7108e1-27ac-4fac-b71d-69f5084e1642",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[1].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "b711777c-cf36-42ed-8c6e-b42641ac0680",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[2].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "8f880527-300b-4e77-b20c-d043a84a35f8",
                            },
                        ],
                    },
                    "id": "d3fba51d-1585-4b03-b107-be0fe5e4e61d",
                }
            ],
            "cta": [],
        },
        "id": "df30f806-68a2-4da2-9b84-0fc868f56940",
    }


def get_theme_hub_page_sticker_row_section():
    buttons = get_button_variants()
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": "all", "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sx44k">Made by people on the internet, for people on the internet</p>',
                "subheading_text": '<p data-block-key="mrour">We\'re here to give you the internet on your terms: '
                "fast, private and actually useful.</p>",
            },
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "sticker_row"},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[3].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "1e7108e1-27ac-4fac-b71d-69f5084e1642",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[0].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "fbf9cb06-303b-42a8-8ae9-d34e0dcde400",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[1].id,
                                    "overrides": {
                                        "image": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                    },
                                },
                                "id": "ae4dabc0-357d-4361-a548-dd10e6ce36e7",
                            },
                        ],
                    },
                    "id": "641b7adb-7193-4087-a3d3-49742ea362ec",
                }
            ],
            "cta": [buttons["secondary"]],
        },
        "id": "23a1a6b7-2f1a-47cf-8e2c-b2977fc2d8e7",
    }


def get_article_theme_page():
    index_page = get_article_index_test_page()
    theme_page = ArticleThemePage.objects.filter(slug="test-article-theme-page").first()
    if not theme_page:
        theme_page = ArticleThemePage(
            title="Test Article Theme Page",
            slug="test-article-theme-page",
        )
        index_page.add_child(instance=theme_page)
    theme_page.content = [
        get_theme_page_intro(),
        get_theme_page_illustration_cards_section(),
        get_theme_page_icon_cards_section(),
        get_theme_page_sticker_row_section(),
    ]
    theme_page.save_revision().publish()
    return theme_page


def get_article_theme_hub_page():
    index_page = get_article_index_test_page()
    theme_page = ArticleThemePage.objects.filter(slug="test-article-theme-hub-page").first()
    if not theme_page:
        theme_page = ArticleThemePage(
            title="Test Article Theme Hub Page",
            slug="test-article-theme-hub-page",
        )
        index_page.add_child(instance=theme_page)
    theme_page.upper_content = get_theme_hub_page_upper_content()
    theme_page.content = [
        get_theme_hub_illustration_cards_section(),
        get_theme_hub_page_sticker_row_section(),
    ]
    theme_page.save_revision().publish()
    return theme_page
