# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Tests for ArticleDetailPage with an optional hero, landing content and closing CTA."""

from django.core.exceptions import ValidationError

import pytest
from bs4 import BeautifulSoup
from wagtail_localize.fields import SynchronizedField
from wagtail_localize.segments.extract import extract_segments

from springfield.cms.fixtures.base_fixtures import get_article_index_test_page
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet, get_pre_footer_cta_snippet
from springfield.cms.models import ArticleDetailPage, FreeFormPage2026
from springfield.cms.models.pages import PRE_FOOTER_IMAGE_GLOBE, PRE_FOOTER_IMAGE_KIT
from springfield.cms.tests.factories import ArticleDetailPageFactory

pytestmark = [pytest.mark.django_db]


def intro_block(heading_text, platforms=None):
    """Intro block carrying only a heading, shown to `platforms` if given and to everyone otherwise."""
    return {
        "type": "intro",
        "value": {
            "settings": {"anchor_id": "", "show_to": {"platforms": platforms or []}},
            "heading": {"heading_text": f"<p>{heading_text}</p>"},
        },
    }


def section_block(heading_text):
    return {"type": "section", "value": {"settings": {"anchor_id": ""}, "heading": {"heading_text": f"<p>{heading_text}</p>"}}}


def banner_block(heading_text):
    return {"type": "banner", "value": {"heading": {"heading_text": f"<p>{heading_text}</p>"}}}


def stream_block(page_model, field_name):
    return page_model._meta.get_field(field_name).stream_block


def showcase_media_blocks(page_model, field_name):
    showcase = stream_block(page_model, field_name).child_blocks["showcase"]
    return showcase.child_blocks["media"].child_blocks


@pytest.fixture
def article_index(minimal_site):
    return get_article_index_test_page()


@pytest.fixture
def article(article_index):
    """A published article with title and text only, as every article page is today."""
    page = ArticleDetailPageFactory(
        parent=article_index,
        title="Firefox VPN",
        slug="vpn",
        content=[{"type": "text", "value": "<h2>Why use a VPN</h2><p>Article text.</p>"}],
    )
    page.save_revision().publish()
    return page


def render(client, page):
    page.save_revision().publish()
    response = client.get(page.url)
    assert response.status_code == 200
    return BeautifulSoup(response.content, "html.parser")


def test_new_fields_default_to_todays_page():
    page = ArticleDetailPage(title="x", slug="x")

    assert page.show_pre_footer is True
    assert page.pre_footer_image == PRE_FOOTER_IMAGE_KIT
    assert not page.hero
    assert not page.landing_content
    assert not page.closing_cta


def test_hero_offers_intro_only():
    assert list(stream_block(ArticleDetailPage, "hero").child_blocks) == ["intro"]


def test_landing_content_offers_article_landing_blocks():
    assert list(stream_block(ArticleDetailPage, "landing_content").child_blocks) == [
        "intro",
        "section",
        "showcase",
        "carousel",
        "card_gallery",
        "media_content",
        "cards_list",
        "featured_image_section",
        "banner",
        "kit_banner",
        "line_cards",
        "topic_list",
        "button_row",
        "comparison_table",
        "browser_comparison_table",
        "image_caption",
        "rich_text",
    ]


def test_landing_content_showcase_offers_comparison_tabs():
    assert "tabs" in showcase_media_blocks(ArticleDetailPage, "landing_content")
    assert "tabs" not in showcase_media_blocks(FreeFormPage2026, "content")
    assert "tabs" not in showcase_media_blocks(FreeFormPage2026, "upper_content")


def test_closing_cta_offers_one_banner():
    closing_cta = stream_block(ArticleDetailPage, "closing_cta")
    assert list(closing_cta.child_blocks) == ["banner", "kit_banner"]

    two_banners = closing_cta.to_python([banner_block("One"), banner_block("Two")])
    with pytest.raises(ValidationError):
        closing_cta.clean(two_banners)


def test_hero_and_landing_content_sit_on_their_own_tab():
    tabs = {
        tab.heading: [panel.field_name for panel in tab.children if hasattr(panel, "field_name")]
        for tab in ArticleDetailPage.get_edit_handler().children
    }

    assert list(tabs) == ["Content", "Landing", "Promote", "Settings"]
    assert tabs["Landing"] == ["hero", "landing_content"]
    assert "closing_cta" in tabs["Content"]


def test_landing_content_needs_a_hero(article):
    article.landing_content = [section_block("What you get")]

    with pytest.raises(ValidationError) as error:
        article.full_clean()

    assert error.value.message_dict["hero"] == ["Add a hero to use landing content."]


@pytest.mark.parametrize(
    ("hero", "landing_content"),
    [([], []), ([intro_block("Firefox VPN")], []), ([intro_block("Firefox VPN")], [section_block("What you get")])],
    ids=["neither", "hero_only", "both"],
)
def test_hero_and_landing_content_pass_validation(article, hero, landing_content):
    article.hero = hero
    article.landing_content = landing_content

    article.full_clean()


def test_hero_and_landing_strings_are_translatable(article):
    article.hero = [intro_block("Firefox VPN")]
    article.landing_content = [section_block("What you get")]
    article.save()

    strings = {segment.string.data for segment in extract_segments(article) if hasattr(segment, "string")}

    assert "Firefox VPN" in strings
    assert "What you get" in strings


def test_pre_footer_image_is_synchronised():
    by_name = {field.field_name: field for field in ArticleDetailPage.override_translatable_fields}

    assert isinstance(by_name["pre_footer_image"], SynchronizedField)


# Rendering


@pytest.fixture
def pre_footer_snippets():
    get_pre_footer_cta_snippet()
    get_pre_footer_cta_form_snippet()


def test_article_without_new_fields_renders_as_today(client, article, pre_footer_snippets, placeholder_images):
    image, *_ = placeholder_images
    article.image = image
    soup = render(client, article)

    assert "fl-force-dark-theme" not in soup.select_one("header.fl-header")["class"]
    assert [h1.get_text(strip=True) for h1 in soup.find_all("h1")] == ["Firefox VPN"]
    assert soup.select_one(".fl-article-header .article-featured-image img") is not None
    assert soup.select_one(".fl-rich-text h2").get_text(strip=True) == "Why use a VPN"
    assert soup.select_one(".fl-pre-footer-cta") is not None
    assert "flare/kit-on-rock.png" in soup.select_one(".fl-newsletterform-illustration img")["src"]


def test_closing_cta_renders_last_as_h2(client, article):
    article.closing_cta = [banner_block("Get Firefox now")]
    soup = render(client, article)

    main = soup.select_one(".fl-main")
    closing_cta = main.select_one(".fl-banner-container")
    assert closing_cta.find(class_="fl-heading").name == "h2"
    assert closing_cta.find(class_="fl-heading").get_text(strip=True) == "Get Firefox now"
    assert closing_cta.find_previous(class_="fl-rich-text") is not None
    assert closing_cta.find_next(class_="fl-rich-text") is None
    assert main.find_all(recursive=False)[-1] is closing_cta


def test_pre_footer_can_be_turned_off(client, article, pre_footer_snippets):
    article.show_pre_footer = False
    soup = render(client, article)

    assert soup.select_one(".fl-pre-footer-cta") is None
    assert soup.select_one(".fl-newsletterform-cta") is None


def test_pre_footer_image_choice_is_shown(client, article, pre_footer_snippets):
    article.pre_footer_image = PRE_FOOTER_IMAGE_GLOBE
    soup = render(client, article)

    assert "flare/globe.png" in soup.select_one(".fl-newsletterform-illustration img")["src"]
