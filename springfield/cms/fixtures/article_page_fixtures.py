# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.fixtures.base_fixtures import (
    SHOW_TO_ALL,
    get_article_theme_root_page,
    get_or_create_page,
    get_placeholder_images,
    with_fresh_ids,
)
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_pencil_banner_snippet, get_tags
from springfield.cms.models import ArticleDetailPage, ArticleThemePage, SpringfieldImage, Tag
from springfield.cms.models.pages import ArticleDetailPagePencilBannerPlacement, ArticleThemePagePencilBannerPlacement

ARTICLE_BODY_PARAGRAPHS = [
    "This is a sample Article Detail Page. Its title, description, tag and images are the fields that article cards pull from "
    "when they link to it, so filling them in well is what makes the cards on the theme and index pages look right.",
    "On a card any of those fields can be overridden, so the same article can be presented differently in different places "
    "without changing the article itself.",
    "The body you are reading is the article's own content, shown only here on the detail page — cards never display it.",
    "Turn on the Featured flag to pull an article into the index page's featured row instead of the plain listing below it.",
    "Give every article a clear tag; the theme and index pages group and style their cards by it.",
]


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
) -> ArticleDetailPage:
    # Articles live under the theme root, as siblings of the index page — the index
    # lists them through show_sibling_detail_pages, mirroring the real /features section.
    theme_root = get_article_theme_root_page()
    placeholder_alt = "A numbered grid, standing in for a real image"

    article = get_or_create_page(
        ArticleDetailPage,
        slug=slug,
        parent=theme_root,
        defaults={
            "title": title,
            "image": image,
            "image_alt": placeholder_alt,
        },
    )

    article.featured = featured
    article.image = image
    article.image_alt = placeholder_alt
    article.featured_image = featured_image
    article.featured_image_alt = placeholder_alt
    article.icon = icon
    article.sticker = sticker
    article.tag = tag
    article.link_text = link_text
    article.description = description
    article.content = [{"type": "text", "value": "".join(content_blocks)}]
    article.save_revision().publish()

    return article


def get_article_pages():
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
    tags = get_tags()
    p_keys = ["c1bc4d7eadf0", "0b474f02", "d3fd4d86", "83cdc1bc", "4d7eadf0"]

    featured_article_1 = create_article(
        title="Test Featured Article 1",
        slug="test-featured-article-1",
        featured=True,
        description=(
            '<p data-block-key="c1bc4d7eadf0">A featured article. This description, its tag and its image are what a card shows '
            "when it references the article — unless the card overrides them.</p>"
        ),
        content_blocks=[f"<p data-block-key='{key}'>{para}</p>" for key, para in zip(p_keys, ARTICLE_BODY_PARAGRAPHS[:3])],
        image=image,
        featured_image=dark_mobile_image,
        icon="globe",
        sticker=dark_image,
        tag=tags["security"],
        link_text="See Featured 1",
    )

    snippet = get_pencil_banner_snippet()
    ArticleDetailPagePencilBannerPlacement.objects.get_or_create(page=featured_article_1, snippet=snippet)

    featured_article_2 = create_article(
        title="Test Featured Article 2",
        slug="test-featured-article-2",
        featured=True,
        description=(
            '<p data-block-key="c1bc4d7eadf0">Another featured article. Featured articles appear in the index page\'s featured row; '
            "non-featured ones fall into the plain listing below it.</p>"
        ),
        content_blocks=[f"<p data-block-key='{key}'>{para}</p>" for key, para in zip(p_keys, ARTICLE_BODY_PARAGRAPHS[:4])],
        image=dark_image,
        featured_image=mobile_image,
        icon="arrow-clockwise",
        sticker=image,
        tag=tags["privacy"],
        link_text="See Featured 2",
    )

    regular_article_1 = create_article(
        title="Test Regular Article 1",
        slug="test-regular-article-1",
        featured=False,
        description=(
            '<p data-block-key="c1bc4d7eadf0">A regular (non-featured) article. It shows in the index page\'s main listing, '
            "and anywhere a card on a theme page links to it.</p>"
        ),
        content_blocks=[f"<p data-block-key='{key}'>{para}</p>" for key, para in zip(p_keys, ARTICLE_BODY_PARAGRAPHS[:2])],
        image=image,
        featured_image=dark_mobile_image,
        icon="apple",
        sticker=dark_image,
        tag=tags["performance"],
        link_text="See Regular 1",
    )

    regular_article_2 = create_article(
        title="Test Regular Article 2",
        slug="test-regular-article-2",
        featured=False,
        description=(
            '<p data-block-key="c1bc4d7eadf0">A regular article. Every article in this section feeds the cards on the theme page '
            "and the automatic listing on the index page.</p>"
        ),
        content_blocks=[f"<p data-block-key='{key}'>{para}</p>" for key, para in zip(p_keys, ARTICLE_BODY_PARAGRAPHS[:3])],
        image=image,
        featured_image=mobile_image,
        icon="android",
        sticker=image,
        tag=tags["tips"],
        link_text="See Regular 2",
    )

    return [
        featured_article_1,
        featured_article_2,
        regular_article_1,
        regular_article_2,
    ]


def get_theme_page_intro():
    placeholder_images = get_placeholder_images()
    return {
        "type": "intro",
        "value": {
            "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
            "media": [
                {
                    "type": "image",
                    "value": {
                        "image": placeholder_images.image.id,
                        "image_alt": "A numbered grid, standing in for a real image",
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
                "superheading_text": '<p data-block-key="aafi8">Article Theme Page</p>',
                "heading_text": '<p data-block-key="u6bj0">The root of an article section</p>',
                "subheading_text": '<p data-block-key="l00s0">A theme page is the landing for a section like /features. It highlights a '
                "hand-picked set of articles with the article cards below — it does not list every article. The Article Index Page "
                "nested beneath it is the full table of contents.</p>",
            },
            "content": [],
        },
        "id": "3af11135-d051-4819-951e-16d534362260",
    }


def get_theme_page_illustration_cards_section():
    placeholder_images = get_placeholder_images()
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="qf39f">Article cards pull their content from the articles</p>',
                "subheading_text": '<p data-block-key="qf39g">Each card references an article and shows the article\'s own image, tag, title, '
                "description and link. The first card overrides those fields to show custom copy instead.</p>",
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
                                        "image": placeholder_images.mobile_image.id,
                                        "superheading": "Overridden tag",
                                        "title": '<p data-block-key="njwu5">Overridden title</p>',
                                        "description": '<p data-block-key="mwjdk">This card overrides the article\'s title, description, '
                                        "tag and image. The cards beside it leave the overrides empty, so they use the article's own fields.</p>",
                                        "link_label": "Overridden label",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sv9yi">The same cards, as icon cards</p>',
                "subheading_text": '<p data-block-key="sv9yj">The card_type setting switches the layout. Icon cards lead with an icon '
                "instead of the article image; this first card overrides the article's icon, title and description.</p>",
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
                                        "sticker": None,
                                        "icon": "book",
                                        "superheading": "",
                                        "title": '<p data-block-key="bcq0b">Overridden title</p>',
                                        "description": '<p data-block-key="ovybu">This icon card overrides the article\'s icon, '
                                        "title and description.</p>",
                                        "link_label": "Overridden label",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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


def get_theme_page_pictogram_row_section():
    placeholder_images = get_placeholder_images()
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sv9yi">The same cards, as a sticker row</p>',
                "subheading_text": '<p data-block-key="sv9yk">sticker_row is a third card_type — a compact row that leads with the article\'s '
                "sticker image. This first card overrides the sticker, tag, title and description.</p>",
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
                                        "sticker": placeholder_images.image.id,
                                        "icon": "",
                                        "superheading": "Overridden tag",
                                        "title": '<p data-block-key="bcq0b">Overridden title</p>',
                                        "description": '<p data-block-key="ovybu">This sticker-row card overrides the article\'s '
                                        "sticker, tag, title and description.</p>",
                                        "link_label": "Overridden label",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
                                    },
                                },
                                "id": "1e7108e1-27ac-4fac-b71d-69f5084e1642",
                            },
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[2].id,
                                    "overrides": {
                                        "image": None,
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
                                    },
                                },
                                "id": "ae4dabc0-357d-4361-a548-dd10e6ce36e7",
                            },
                        ],
                    },
                    "id": "641b7adb-7193-4087-a3d3-49742ea362ec",
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
                "settings": {"layout": "vertical", "slim": False, "anchor_id": ""},
                "media": [],
                "heading": {
                    "superheading_text": '<p data-block-key="arkm3">Article Theme Page (nested)</p>',
                    "heading_text": '<p data-block-key="arkm4">A theme page nested under another theme</p>',
                    "subheading_text": '<p data-block-key="ffk5g">Theme pages can nest under other theme pages, like /features/protection. Each '
                    "nested theme highlights its own subset of articles with the same article cards.</p>",
                },
                "content": [],
            },
            "id": "929f73bf-d056-42d5-8214-0f6f4a7390aa",
        }
    ]


def get_theme_hub_illustration_cards_section():
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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


def get_theme_hub_page_pictogram_row_section():
    buttons = get_button_variants()
    articles = get_article_pages()
    return {
        "type": "section",
        "value": {
            "settings": {"show_to": SHOW_TO_ALL, "anchor_id": ""},
            "heading": {
                "superheading_text": "",
                "heading_text": '<p data-block-key="sx44k">This nested theme\'s hand-picked articles</p>',
                "subheading_text": '<p data-block-key="mrour">Like the root theme page, a nested theme curates a specific set of articles '
                "with cards rather than listing them all.</p>",
            },
            "content": [
                {
                    "type": "article_cards_list",
                    "value": {
                        "settings": {"card_type": "sticker_row", "show_to": SHOW_TO_ALL},
                        "cards": [
                            {
                                "type": "item",
                                "value": {
                                    "article": articles[3].id,
                                    "overrides": {
                                        "image": None,
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
                                        "sticker": None,
                                        "icon": "",
                                        "superheading": "",
                                        "title": "",
                                        "description": "",
                                        "link_label": "",
                                        "link": {
                                            "link_to": "",
                                            "page": None,
                                            "file": None,
                                            "custom_url": "",
                                            "anchor": "",
                                            "email": "",
                                            "phone": "",
                                            "new_window": False,
                                        },
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
    """Fill the section root (the theme page) with its curated content: an intro and
    three article-card sections that highlight specific articles. The page itself is
    created by get_article_theme_root_page, so its title stays the section-root title."""
    theme_root = get_article_theme_root_page()
    theme_root.content = with_fresh_ids(
        [
            get_theme_page_intro(),
            get_theme_page_illustration_cards_section(),
            get_theme_page_icon_cards_section(),
            get_theme_page_pictogram_row_section(),
        ]
    )
    snippet = get_pencil_banner_snippet()
    ArticleThemePagePencilBannerPlacement.objects.get_or_create(page=theme_root, snippet=snippet)
    # The article children were created (under this root) after it was fetched, so this
    # instance's tree bookkeeping is stale. Refresh it before publishing so we don't
    # write back a stale numchild and collide child paths on the next add_child.
    theme_root.refresh_from_db(fields=["numchild", "path", "depth"])
    theme_root.save_revision().publish()
    return theme_root


def get_article_theme_hub_page():
    """A theme page nested under the section root, mirroring /features/protection."""
    theme_root = get_article_theme_root_page()
    sub_theme = get_or_create_page(
        ArticleThemePage,
        slug="test-article-theme-hub-page",
        parent=theme_root,
        defaults={
            "title": "02. Article Theme Page (nested theme)",
        },
    )
    # Sequential prefix keeps the nested theme beside the index, above the article pages.
    sub_theme.title = "02. Article Theme Page (nested theme)"
    sub_theme.upper_content = get_theme_hub_page_upper_content()
    sub_theme.content = [
        get_theme_hub_illustration_cards_section(),
        get_theme_hub_page_pictogram_row_section(),
    ]
    sub_theme.save_revision().publish()
    return sub_theme
