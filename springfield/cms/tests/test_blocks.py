# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from unittest import mock
from urllib.parse import urlparse, urlunparse

from django.template.loader import render_to_string
from django.test import override_settings

import pytest
from bs4 import BeautifulSoup
from wagtail.blocks import StreamBlockValidationError
from wagtail.documents.models import Document
from wagtail.images.jinja2tags import image, srcset_image
from wagtail.models import Locale, Page, Site

from lib.l10n_utils import get_locale
from springfield.cms.blocks import ArticleBlock, BaseArticleValue, SpringfieldLinkBlock
from springfield.cms.fixtures.article_page_fixtures import (
    get_article_pages,
    get_article_theme_hub_page,
    get_article_theme_page,
    get_theme_hub_illustration_cards_section,
    get_theme_hub_page_sticker_row_section,
    get_theme_hub_page_upper_content,
    get_theme_page_icon_cards_section,
    get_theme_page_illustration_cards_section,
    get_theme_page_intro,
    get_theme_page_sticker_row_section,
)
from springfield.cms.fixtures.banner_fixtures import get_banner_2026_test_page, get_banner_2026_variants, get_banner_test_page, get_banner_variants
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_blocks, get_buttons_2026_test_page, get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import (
    get_cards_list_variants,
    get_filled_card_variants,
    get_filled_cards_test_page,
    get_icon_card_variants,
    get_icon_cards_test_page,
    get_illustration_card_variants,
    get_illustration_cards_test_page,
    get_step_card_variants,
    get_step_cards_list_variants,
    get_step_cards_test_page,
    get_sticker_card_variants,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.card_gallery_2026_fixtures import get_card_gallery_2026_test_page, get_card_gallery_2026_variants
from springfield.cms.fixtures.cards_2026_fixtures import (
    get_illustration_card_2026_variants,
    get_illustration_cards_2026_test_page,
    get_outlined_card_2026_variants,
    get_outlined_cards_2026_test_page,
    get_step_card_2026_variants,
    get_step_cards_2026_test_page,
    get_sticker_card_2026_variants,
    get_sticker_cards_2026_test_page,
)
from springfield.cms.fixtures.carousel_2026_fixtures import get_carousel_2026_test_page, get_carousel_2026_variants
from springfield.cms.fixtures.freeformpage_2026 import (
    get_freeform_page_2026_test_page,
    get_mobile_store_qr_code,
    get_mobile_store_qr_code_test_page,
)
from springfield.cms.fixtures.homepage_fixtures import (
    get_card_gallery,
    get_cards_list,
    get_home_carousel,
    get_home_intro,
    get_home_test_page,
    get_kit_banner,
    get_showcase_variants,
)
from springfield.cms.fixtures.icon_cards_2026_fixtures import (
    get_icon_card_2026_variants,
    get_icon_cards_2026_test_page,
)
from springfield.cms.fixtures.icon_list_with_image_2026_fixtures import (
    get_icon_list_with_image_test_page,
    get_icon_list_with_image_variants,
)
from springfield.cms.fixtures.inline_notification_fixtures import get_inline_notification_test_page, get_inline_notification_variants
from springfield.cms.fixtures.intro_2026_fixtures import get_intro_2026_test_page, get_intro_2026_variants
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page, get_intro_variants
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_2026_test_page, get_kit_banner_test_page, get_kit_banner_variants
from springfield.cms.fixtures.kit_intro_2026_fixtures import get_kit_intro_2026_test_page, get_kit_intro_2026_variants
from springfield.cms.fixtures.line_cards_fixtures import (
    get_line_card_variants,
    get_line_cards_test_page,
)
from springfield.cms.fixtures.media_content_2026_fixtures import (
    get_media_content_2026_narrow_variants,
    get_media_content_2026_sections,
    get_media_content_2026_test_page,
    get_media_content_2026_variants,
)
from springfield.cms.fixtures.media_content_fixtures import (
    get_media_content_test_page,
    get_section_with_media_content_variants,
)
from springfield.cms.fixtures.notification_fixtures import get_notification_test_page, get_notification_variants
from springfield.cms.fixtures.showcase_2026_fixtures import get_showcase_2026_test_page, get_showcase_2026_variants
from springfield.cms.fixtures.sliding_carousel_fixtures import (
    get_sliding_carousel_slides,
    get_sliding_carousel_test_page,
)
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import (
    get_smart_window_explainer_content,
    get_smart_window_explainer_intro,
    get_smart_window_explainer_test_page,
)
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_snippet
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page, get_subscription_variants
from springfield.cms.fixtures.testimonial_card_fixtures import (
    get_testimonial_card_2026_variants,
    get_testimonial_cards_2026_test_page,
)
from springfield.cms.fixtures.topic_list_fixtures import get_topic_list_2026_test_page, get_topic_list_lower_variants, get_topic_list_upper_variants
from springfield.cms.models import ArticleDetailPage, SpringfieldImage
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.templatetags.cms_tags import add_utm_parameters
from springfield.cms.tests.factories import ArticleDetailPageFactory, LocaleFactory
from springfield.firefox.firefox_details import firefox_desktop
from springfield.firefox.templatetags.misc import app_store_url, fxa_button, play_store_url

pytestmark = [
    pytest.mark.django_db,
]

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def strip_host(url):
    return urlunparse(urlparse(url)._replace(scheme="", netloc=""))


def assert_button_attributes(
    button_element: BeautifulSoup,
    button_data: dict,
    context: dict,
    cta_position: str | None = None,
    cta_text: str | None = None,
):
    """
    Compares the rendered button element with the expected button data.
    The request context is needed to verify the button link UTM parameters.
    The cta_position and cta_text are built by the parent component
    and passed down to the button.
    """
    label = button_data["value"]["label"]
    settings = button_data["value"]["settings"]
    theme = settings["theme"]
    icon = settings["icon"]
    icon_position = settings["icon_position"]
    analytics_id = settings["analytics_id"]

    external = False
    if button_data["value"]["link"]["link_to"] == "custom_url":
        link = button_data["value"]["link"]["custom_url"]
        external = button_data["value"]["link"]["new_window"]
    elif button_data["value"]["link"]["link_to"] == "page":
        page_id = button_data["value"]["link"]["page"]
        page = Page.objects.get(id=page_id).specific
        link = page.get_url(context["request"])
        external = button_data["value"]["link"]["new_window"]
    elif button_data["value"]["link"]["link_to"] == "file":
        document_id = button_data["value"]["link"]["file"]
        document = Document.objects.get(id=document_id)
        link = document.url
    elif button_data["value"]["link"]["link_to"] == "email":
        email = button_data["value"]["link"]["email"]
        link = f"mailto:{email}"
    elif button_data["value"]["link"]["link_to"] == "phone":
        phone = button_data["value"]["link"]["phone"]
        link = f"tel:{phone}"

    assert button_element["href"] == add_utm_parameters(context, link)

    if external:
        assert button_element["target"] == "_blank"
        assert set(button_element["rel"]) == {"external", "noopener"}

    assert label in button_element.get_text()
    if theme:
        assert f"button-{theme}" in button_element["class"]
    if icon:
        icon_span = button_element.find("span", class_="fl-icon")
        assert icon_span and f"fl-icon-{icon}" in icon_span["class"]
        if icon_position == "left":
            assert "fl-icon-left" in icon_span["class"]
        else:
            assert "fl-icon-right" in icon_span["class"]
    assert button_element["data-cta-uid"] == analytics_id
    if cta_position:
        assert button_element["data-cta-position"] == cta_position
    if cta_text:
        assert button_element["data-cta-text"] == cta_text


def assert_download_button_attributes(
    button_element: BeautifulSoup, button_data: dict, context: dict, cta_position: str | None = None, cta_text: str | None = None
):
    label = button_data["value"]["label"]
    settings = button_data["value"]["settings"]
    theme = settings["theme"]
    icon = settings["icon"]
    icon_position = settings["icon_position"]
    analytics_id = settings["analytics_id"]

    assert label in button_element.get_text()
    assert "download-link" in button_element["class"]
    assert button_element["href"] == "/thanks/"

    assert "c-button-download-thanks" in button_element.parent["class"]
    assert button_data["value"]["settings"]["analytics_id"] == button_element.parent["id"]

    channel = "release"
    version = firefox_desktop.latest_version(channel)
    locale = get_locale(context["request"])
    download_link_direct = firefox_desktop.get_download_url(
        channel=channel,
        version=version,
        platform="win",
        locale=locale,
        force_direct=True,
        force_full_installer=False,
    )
    assert button_element["data-direct-link"] == download_link_direct

    if theme:
        assert f"button-{theme}" in button_element["class"]
    if icon:
        icon_span = button_element.find("span", class_="fl-icon")
        assert icon_span and f"fl-icon-{icon}" in icon_span["class"]
        if icon_position == "left":
            assert "fl-icon-left" in icon_span["class"]
        else:
            assert "fl-icon-right" in icon_span["class"]
    assert button_element["data-cta-uid"] == analytics_id
    if cta_position:
        assert button_element["data-cta-position"] == cta_position
    if cta_text:
        assert button_element["data-cta-text"] == cta_text

    if settings.get("show_default_browser_checkbox"):
        checkbox_label = button_element.find_next_sibling("label", class_="default-browser-label hidden")
        assert checkbox_label and "Set Firefox as your default browser." in checkbox_label.get_text()
        id_ = f"{settings['analytics_id']}-default-browser"
        assert checkbox_label["for"] == id_
        checkbox = checkbox_label.find("input", {"type": "checkbox", "class": "default-browser-checkbox"})
        assert checkbox and checkbox["id"] == id_


def assert_tag_attributes(tag_element: BeautifulSoup, tag_data: dict):
    """
    Compares the rendered tag element with the expected tag data.
    """
    title = tag_data["value"]["title"]
    icon = tag_data["value"]["icon"]
    icon_position = tag_data["value"]["icon_position"]
    corners = tag_data["value"].get("corners")
    color = tag_data["value"]["color"]

    assert title in tag_element.get_text()
    if color:
        assert f"fl-tag-{color}" in tag_element["class"]
    if corners:
        assert f"fl-tag-{corners}" in tag_element["class"]
    icon_span = tag_element.find("span", class_="fl-icon")
    assert icon_span and f"fl-icon-{icon}" in icon_span["class"]
    if icon_position == "before":
        assert "icon-left" in icon_span["class"]
    else:
        assert "icon-right" in icon_span["class"]


def assert_section_heading_attributes(section_element: BeautifulSoup, heading_data: dict, index: int):
    """
    Compares the rendered section heading with the expected heading data.
    The index is used to determine if the heading should be an h1 or h2.
    """
    superheading_text = BeautifulSoup(heading_data["superheading_text"], "html.parser").get_text()
    heading_text = BeautifulSoup(heading_data["heading_text"], "html.parser").get_text()
    subheading_text = BeautifulSoup(heading_data["subheading_text"], "html.parser").get_text()

    heading = section_element.find("h1" if index == 0 else "h2", class_="fl-heading")
    assert heading and heading_text in heading.get_text()

    if superheading_text:
        superheading = section_element.find("p", class_="fl-superheading")
        assert superheading and superheading_text in superheading.get_text()

    if subheading_text:
        subheading = section_element.find("p", class_="fl-subheading")
        assert subheading and subheading_text in subheading.get_text()


def assert_image_variants_attributes(
    images_element: BeautifulSoup,
    images_value: dict,
    sizes: str = "(min-width: 1200px) 680px, (min-width: 600px) 50vw, 100vw",
    widths: str = "width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
    break_at: str = "sm",
):
    """
    Compares the rendered image element with the expected image data.
    The is_dark flag indicates if the image is a dark mode image.
    The is_mobile flag indicates if the image is a mobile image.
    """

    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()

    assert images_element

    settings = images_value.get("settings", {})

    default_display_classes = "display-light" if settings.get("dark_mode_image") else ""
    if settings.get("mobile_image") or settings.get("dark_mode_mobile_image"):
        default_display_classes += f" display-{break_at}-up"
    img_tag = images_element.find("img", class_=default_display_classes)
    assert img_tag

    def assert_attrs(img: SpringfieldImage, img_tag: BeautifulSoup, classes: str = ""):
        rendered_image = srcset_image(
            img,
            widths,
            **{
                "sizes": sizes,
                "width": img.width,
                "height": img.height,
                "loading": "lazy",
                "class": classes,
            },
        )
        image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
        assert img_tag["alt"] == image_soup["alt"]
        assert img_tag["class"] == image_soup["class"]
        assert img_tag["loading"] == image_soup["loading"]
        assert img_tag["width"] == image_soup["width"]
        assert img_tag["height"] == image_soup["height"]
        assert img_tag["src"] == image_soup["src"]

    assert_attrs(image, img_tag, default_display_classes)

    if settings.get("dark_mode_image"):
        dark_desktop_classes = "display-dark"
        if settings.get("mobile_image") or settings.get("dark_mode_mobile_image"):
            dark_desktop_classes += f" display-{break_at}-up"
        dark_img_tag = images_element.find("img", class_=dark_desktop_classes)
        assert dark_img_tag
        assert_attrs(dark_image, dark_img_tag, dark_desktop_classes)

    if settings.get("mobile_image"):
        mobile_classes = "display-light" if settings.get("dark_mode_mobile_image") else ""
        mobile_classes += " display-xs-and-sm" if break_at == "md" else " display-xs"
        mobile_img_tag = images_element.find("img", class_=mobile_classes)
        assert mobile_img_tag
        assert_attrs(mobile_image, mobile_img_tag, mobile_classes)

    if settings.get("dark_mode_mobile_image"):
        dark_mobile_classes = "display-dark"
        dark_mobile_classes += " display-xs-and-sm" if break_at == "md" else " display-xs"
        dark_mobile_img_tag = images_element.find("img", class_=dark_mobile_classes)
        assert dark_mobile_img_tag
        assert_attrs(dark_mobile_image, dark_mobile_img_tag, dark_mobile_classes)


def assert_section_cta_attributes(
    section_element: BeautifulSoup,
    cta_data: dict,
    context: dict,
    cta_position: str | None = None,
    cta_text: str | None = None,
):
    link = section_element.find("a", class_="fl-section-cta-link")
    assert link["href"] == add_utm_parameters(context, cta_data["value"]["link"]["custom_url"])
    assert link.get_text().strip() == cta_data["value"]["label"].strip()
    if cta_position:
        assert link["data-cta-position"] == cta_position
    if cta_text:
        assert link["data-cta-text"] == cta_text
        assert link["data-cta-uid"] == cta_data["value"]["settings"]["analytics_id"]


def assert_card_attributes(
    card_element: BeautifulSoup,
    card_data: dict,
    context: dict,
    cta_position: str | None = None,
    heading_tag: str = "h3",
):
    headline_text = BeautifulSoup(card_data["value"]["headline"], "html.parser").get_text()
    content_text = BeautifulSoup(card_data["value"]["content"], "html.parser").get_text()

    headline = card_element.find(heading_tag, class_="fl-heading")
    content = card_element.find(class_="fl-body")

    assert headline and headline_text in headline.get_text()
    assert content and content_text in content.get_text()

    if superheading := card_data["value"].get("superheading"):
        superheading_text = BeautifulSoup(superheading, "html.parser").get_text()
        superheading_element = card_element.find(class_="fl-superheading")
        assert superheading_element and superheading_text in superheading_element.get_text()

    # TODO: Fix icon card buttons
    buttons = card_data["value"].get("button") or card_data["value"].get("buttons")
    if buttons:
        cta_text = f"{headline_text.strip()} - {buttons[0]['value']['label'].strip()}"

        assert_button_attributes(
            button_element=card_element.find("a", class_="fl-button"),
            button_data=buttons[0],
            context=context,
            cta_position=cta_position,
            cta_text=cta_text,
        )


def assert_article_card_attributes(
    card_element: BeautifulSoup,
    card_data: dict,
    article: ArticleDetailPage,
    card_list_type: str,
):
    overrides = card_data["value"].get("overrides", {})

    if card_list_type in ["sticker_card", "illustration_card"]:
        superheading_text = overrides.get("superheading") or (article.tag.name if article.tag else "")
        if superheading_text:
            superheading_element = card_element.find("p", class_="fl-superheading")
            assert superheading_element and superheading_element.get_text().strip() == superheading_text.strip()

    title_override = overrides.get("title")
    title_text = BeautifulSoup(title_override, "html.parser").get_text() if title_override else article.title
    heading_element = card_element.find("h3", class_="fl-heading")
    assert heading_element and heading_element.get_text().strip() == title_text.strip()

    link = card_element.find("a")
    assert link and link["href"] == article.url
    link_text = overrides.get("link_label") or article.link_text
    assert link.get_text().strip() == link_text.strip()

    description_override = overrides.get("description")
    description_source = description_override if description_override else article.description
    description_text = BeautifulSoup(description_source, "html.parser").get_text().strip()
    description_class = "fl-article-item-description" if card_list_type == "sticker_row" else "fl-body"
    description_element = card_element.find("div", class_=description_class)
    if card_list_type == "sticker_row":
        description_element = description_element.find("p")
    assert description_element and description_element.get_text().strip() == description_text.strip()


def assert_video_attributes(video_element: BeautifulSoup, video_data: dict):
    """
    Compares the rendered video element with the expected video data.
    """
    video_url = video_data["value"]["video_url"]
    alt = video_data["value"]["alt"]
    poster = video_data["value"]["poster"]

    youtube_id = None
    if "youtube.com" in video_url or "youtu.be" in video_url:
        youtube_id = video_url.split("watch?v=")[-1].split("youtu.be/")[-1].split("&")[0].split("?")[0]

    button = video_element.find("button", class_="fl-video-play")
    assert button and button["aria-label"] == alt

    if youtube_id:
        assert button["data-video-id"] == youtube_id
    else:
        assert "assets.mozilla.net" in video_url
        assert button["data-video-url"] == video_url

    if poster:
        image = SpringfieldImage.objects.get(id=poster)
        image_url = image.get_rendition("width-800").url
        assert button["data-video-poster"] == image_url
        img = video_element.find("img", class_="fl-video-poster")
        assert img and img["src"] == image_url


def assert_animation_attributes(animation_element: BeautifulSoup, animation_data: dict):
    """
    Compares the rendered animation element with the expected animation data.
    """
    video_url = animation_data["value"]["video_url"]
    alt = animation_data["value"]["alt"]
    poster_id = animation_data["value"]["poster"]
    playback = animation_data["value"].get("playback", "autoplay_loop")

    image_obj = SpringfieldImage.objects.get(id=poster_id)
    image_url = image_obj.get_rendition("width-800").url

    if playback == "autoplay_loop":
        # Should render a simple <video autoplay muted loop>
        video = animation_element.find("video")
        assert video
        assert video.has_attr("autoplay")
        assert video.has_attr("muted")
        assert video.has_attr("loop")
        assert video.has_attr("playsinline")
        assert video["poster"] == image_url
        source = video.find("source")
        assert source and source["src"] == video_url
        img = video.find("img", class_="fl-video-poster")
        assert img and img["src"] == image_url
        assert img["alt"] == alt
    elif playback == "autoplay_once":
        # Should render .fl-animation container with play button and video
        assert "fl-animation" in animation_element.get("class", [])
        assert "fl-animation-playing" in animation_element.get("class", [])
        assert animation_element["data-playback"] == "autoplay_once"

        button = animation_element.find("button", class_="js-animation-play")
        assert button and button["aria-label"] == alt

        img = button.find("img", class_="fl-video-poster")
        assert img and img["src"] == image_url

        video = animation_element.find("video")
        assert video
        assert video.has_attr("muted")
        assert video.has_attr("playsinline")
        assert not video.has_attr("autoplay")
        assert not video.has_attr("loop")
        assert video["poster"] == image_url
        source = video.find("source")
        assert source and source["src"] == video_url


def test_inline_notifications(index_page, rf):
    notifications = get_inline_notification_variants()
    test_page = get_inline_notification_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    notification_divs = soup.find_all("div", class_="fl-notification")
    assert len(notification_divs) == len(notifications)

    for index, notification in enumerate(notifications):
        div = notification_divs[index]
        message = BeautifulSoup(notification["value"]["message"], "html.parser").get_text()
        settings = notification["value"].get("settings", {})
        color = settings.get("color")
        icon = settings.get("icon")
        closable = settings.get("closable")
        inverted = settings.get("inverted")

        assert message in div.get_text()
        if color:
            assert f"fl-notification-{color}" in div["class"]
        if icon:
            icon_span = div.find("span", class_="fl-icon")
            assert icon_span and f"fl-icon-{icon}" in icon_span["class"]
        if closable:
            close_button = div.find("button", class_="fl-notification-close")
            assert close_button
        if inverted:
            icon_section = div.find("div", class_="fl-notification-icon-section")
            assert icon_section and "fl-notification-icon-inverted" in icon_section["class"]


def test_intro_block(index_page, placeholder_images, rf):
    intros = get_intro_variants()
    test_page = get_intro_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    # Intro blocks
    intro_divs = soup.find_all("div", class_="fl-intro")
    assert len(intro_divs) == len(intros)

    for index, intro in enumerate(intros):
        intro_element = intro_divs[index]

        # Settings
        settings = intro["value"]["settings"]
        anchor_id = settings.get("anchor_id")
        if anchor_id:
            assert intro_element.get("id") == anchor_id

        # Heading
        heading_block = intro["value"]["heading"]
        assert_section_heading_attributes(section_element=intro_element, heading_data=heading_block, index=index)

        heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

        # Buttons
        button = intro["value"]["buttons"][0]
        button_element = intro_element.find("a", class_="fl-button")
        cta_position = f"block-{index + 1}-intro.button-1"
        cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
        assert_button_attributes(
            button_element=button_element,
            button_data=button,
            context=context,
            cta_position=cta_position,
            cta_text=cta_text,
        )

        # Media
        media_value = intro["value"]["media"] and intro["value"]["media"][0]
        if media_value:
            if media_value["type"] == "image":
                images_element = intro_element.find("div", class_="fl-intro-media")
                assert_image_variants_attributes(
                    images_element=images_element,
                    images_value=media_value["value"],
                    sizes="(min-width: 1200px) 934px, (min-width: 600px) 50vw, 100vw",
                    widths="width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
                )

            if media_value["type"] == "video":
                video_div = intro_element.find("div", class_="fl-video")
                assert_video_attributes(video_div, media_value)

            if media_value["type"] == "animation":
                animation_div = intro_element.find("div", class_="fl-video")
                assert_animation_attributes(animation_div, media_value)

        if video := intro["value"].get("video"):
            video = video[0]
            video_div = intro_element.find("div", class_="fl-video")
            assert_video_attributes(video_div, video)


def test_subscription_block(index_page, rf):
    subscriptions = get_subscription_variants()
    test_page = get_subscription_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    subscription_sections = soup.find_all("section", class_="fl-section-subscribe")
    assert len(subscription_sections) == len(subscriptions)

    for index, subscription in enumerate(subscriptions):
        section = subscription_sections[index]
        heading_block = subscription["value"]["heading"]
        superheading_text = BeautifulSoup(heading_block["superheading_text"], "html.parser").get_text()
        heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()
        subheading_text = BeautifulSoup(heading_block["subheading_text"], "html.parser").get_text()

        superheading = section.find("p", class_="fl-superheading")
        heading = section.find("h1" if index == 0 else "h2", class_="fl-heading")
        subheading = section.find("p", class_="fl-subheading")

        assert superheading and superheading_text in superheading.get_text()
        assert heading and heading_text in heading.get_text()
        assert subheading and subheading_text in subheading.get_text()

        form = section.find("form", class_="fl-newsletterform")
        assert form

        email_input = form.find("input", {"type": "email", "name": "email"})
        assert email_input
        country_select = form.find("select", {"name": "country"})
        assert country_select
        lang_select = form.find("select", {"name": "lang"})
        assert lang_select
        privacy_checkbox = form.find("input", {"type": "checkbox", "name": "privacy"})
        assert privacy_checkbox
        submit_button = form.find("button", {"type": "submit"})
        assert submit_button


def test_media_content_block(index_page, placeholder_images, rf):
    section = get_section_with_media_content_variants()
    test_page = get_media_content_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_element = soup.find("section", class_="fl-section")
    assert section_element

    # Settings
    settings = section["value"]["settings"]
    anchor_id = settings.get("anchor_id")
    if anchor_id:
        assert section_element.get("id") == anchor_id

    # Heading
    heading_data = section["value"]["heading"]
    assert_section_heading_attributes(section_element, heading_data, 0)

    # CTA
    heading_text = BeautifulSoup(heading_data["heading_text"], "html.parser").get_text()
    cta_label = section["value"]["cta"][0]["value"]["label"]
    assert_section_cta_attributes(
        section_element,
        section["value"]["cta"][0],
        context,
        cta_position="block-1-section.cta",
        cta_text=f"{heading_text.strip()} - {cta_label.strip()}",
    )

    # Media + Content blocks
    media_contents = section["value"]["content"]
    media_content_divs = section_element.find_all("div", class_="fl-mediacontent")
    assert len(media_content_divs) == len(media_contents)

    for index, media_content in enumerate(media_contents):
        div = media_content_divs[index]

        # Content
        eyebrow_text = BeautifulSoup(media_content["value"]["eyebrow"], "html.parser").get_text()
        headline_text = BeautifulSoup(media_content["value"]["headline"], "html.parser").get_text()
        content_html = media_content["value"]["content"][0]["value"]
        content_text = BeautifulSoup(content_html, "html.parser").get_text()

        eyebrow = div.find("p", class_="fl-superheading")
        headline = div.find("h2", class_="fl-heading")
        content = div.find("div", class_="fl-body")

        assert eyebrow and eyebrow_text in eyebrow.get_text()
        assert headline and headline_text in headline.get_text()
        assert content and content_text in content.get_text()

        # Buttons
        button = media_content["value"]["buttons"][0]
        button_element = div.find("a", class_="fl-button")
        cta_position = f"block-1-section.item-{index + 1}-media_content.button-1"
        cta_text = f"{headline_text.strip()} - {button['value']['label'].strip()}"
        assert_button_attributes(
            button_element=button_element,
            button_data=button,
            context=context,
            cta_position=cta_position,
            cta_text=cta_text,
        )

        # Media
        media_element = div.find("div", class_="fl-mediacontent-media")
        assert media_element

        media_value = media_content["value"]["media"][0]
        if media_value["type"] == "image":
            assert_image_variants_attributes(images_element=media_element, images_value=media_value["value"])

        elif media_value["type"] == "video":
            video_div = div.find("div", class_="fl-video")
            assert_video_attributes(video_div, media_value)

        elif media_value["type"] == "animation":
            animation_div = div.find("div", class_="fl-video")
            assert_animation_attributes(animation_div, media_value)

        # Tags
        tags = media_content["value"]["tags"]
        tag_elements = div.find("div", class_="fl-mediacontent-tags").find_all("span", class_="fl-tag")
        assert len(tag_elements) == len(tags)
        for index, tag in enumerate(tags):
            tag_element = tag_elements[index]
            assert_tag_attributes(tag_element, tag)


def _assert_media_content_2026_variants(region, variants, section_prefix, context, heading_tag="h3"):
    for index, variant in enumerate(variants):
        div = region.find_all("div", class_="fl-mediacontent")[index]
        value = variant["value"]

        # Headline
        headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
        headline = div.find(heading_tag, class_="fl-heading")
        assert headline and headline_text in headline.get_text()

        # Eyebrow (optional)
        if value.get("eyebrow"):
            eyebrow_text = BeautifulSoup(value["eyebrow"], "html.parser").get_text()
            eyebrow = div.find("p", class_="fl-superheading")
            assert eyebrow and eyebrow_text in eyebrow.get_text()

        # Content (StreamBlock — first rich_text block)
        content_html = value["content"][0]["value"]
        content_text = BeautifulSoup(content_html, "html.parser").get_text()
        body = div.find("div", class_="fl-body")
        assert body and content_text in body.get_text()

        # Every <a> in the raw content HTML must be rendered with all three
        # CTA tracking attributes (uid, text, position).
        content_soup = BeautifulSoup(content_html, "html.parser")
        expected_link_count = len(content_soup.find_all("a"))
        if expected_link_count:
            rich_text_links = body.find_all("a", attrs={"data-cta-uid": True})
            assert len(rich_text_links) == expected_link_count
            for link in rich_text_links:
                uid = link["data-cta-uid"]
                assert _UUID_RE.match(uid), f"Body link {link.get('href')!r} has invalid data-cta-uid: {uid!r}"
                assert link.get("data-cta-text"), f"Body link {link.get('href')!r} missing data-cta-text"
                assert link.get("data-cta-position"), f"Body link {link.get('href')!r} missing data-cta-position"

        # Buttons
        button = value["buttons"][0]
        button_element = div.find("a", class_="fl-button")
        cta_position = f"{section_prefix}.item-{index + 1}-media_content.button-1"
        cta_text = f"{headline_text.strip()} - {button['value']['label'].strip()}"
        assert_button_attributes(
            button_element=button_element,
            button_data=button,
            context=context,
            cta_position=cta_position,
            cta_text=cta_text,
        )

        # Media
        media_element = div.find("div", class_="fl-mediacontent-media")
        assert media_element

        media_value = value["media"][0]
        if media_value["type"] == "image":
            assert_image_variants_attributes(images_element=media_element, images_value=media_value["value"])
        elif media_value["type"] == "video":
            video_div = div.find("div", class_="fl-video")
            assert_video_attributes(video_div, media_value)

        # Tags
        tags = value["tags"]
        if tags:
            tag_elements = div.find("div", class_="fl-mediacontent-tags").find_all("span", class_="fl-tag")
            assert len(tag_elements) == len(tags)
            for i, tag in enumerate(tags):
                assert_tag_attributes(tag_elements[i], tag)

        # Settings: media_after → fl-mediacontent-reverse; narrow → is-narrow
        if value["settings"].get("media_after"):
            assert "fl-mediacontent-reverse" in div.get("class", [])
        else:
            assert "fl-mediacontent-reverse" not in div.get("class", [])

        if value["settings"].get("narrow"):
            assert "is-narrow" in div.get("class", [])
        else:
            assert "is-narrow" not in div.get("class", [])


def test_media_content_2026_block(index_page, placeholder_images, rf):
    sections = get_media_content_2026_sections()
    variants = get_media_content_2026_variants()
    narrow_variants = get_media_content_2026_narrow_variants()
    page = get_media_content_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    # Upper region: section 1 has block_level=1 (children get h2), section 2 has block_level=2 (children get h3)
    upper_section_elements = upper.find_all("section", class_="fl-section")
    assert len(upper_section_elements) == len(sections)
    assert len(upper_section_elements[0].find_all("div", class_="fl-mediacontent")) == len(variants)
    assert len(upper_section_elements[1].find_all("div", class_="fl-mediacontent")) == len(narrow_variants)
    _assert_media_content_2026_variants(upper_section_elements[0], variants, "upper-block-1-section", context, heading_tag="h2")
    _assert_media_content_2026_variants(upper_section_elements[1], narrow_variants, "upper-block-2-section", context, heading_tag="h3")

    # Lower region: all sections have block_level=2 (children get h3)
    lower_section_elements = lower.find_all("section", class_="fl-section")
    assert len(lower_section_elements) == len(sections)
    assert len(lower_section_elements[0].find_all("div", class_="fl-mediacontent")) == len(variants)
    assert len(lower_section_elements[1].find_all("div", class_="fl-mediacontent")) == len(narrow_variants)
    _assert_media_content_2026_variants(lower_section_elements[0], variants, "lower-block-1-section", context, heading_tag="h3")
    _assert_media_content_2026_variants(lower_section_elements[1], narrow_variants, "lower-block-2-section", context, heading_tag="h3")


def test_icon_card_block(index_page, rf):
    test_page = get_icon_cards_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_titles = ["Cards List with Icon Cards", "Cards List with Icon Cards - 4 columns"]

    card_variants = get_icon_card_variants()
    card_lists = get_cards_list_variants(
        card_variants,
        heading_1=section_titles[0],
        heading_2=section_titles[1],
    )

    # Card Lists
    section_elements = soup.find_all("section", class_="fl-section")
    assert len(section_elements) == len(card_lists)

    for list_index, card_list in enumerate(card_lists):
        section_element = section_elements[list_index]
        assert section_element

        # Section Heading
        assert_section_heading_attributes(section_element, card_list["value"]["heading"], list_index)

        # CTA
        cta_data = card_list["value"]["cta"][0]
        assert_section_cta_attributes(
            section_element,
            cta_data,
            context,
            cta_position=f"block-{list_index + 1}-section.cta",
            cta_text=f"{section_titles[list_index].strip()} - {cta_data['value']['label'].strip()}",
        )

        # Cards
        card_list_div = section_element.find("div", class_="fl-card-grid")
        assert card_list_div

        card_divs = card_list_div.find_all("article", class_="fl-card")
        cards = card_list["value"]["content"][0]["value"]["cards"]
        assert len(card_divs) == len(cards)

        for card_index, card in enumerate(cards):
            card_element = card_divs[card_index]
            # icon-card.html uses block_level directly; section 0 children are h2, section 1 are h3
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
                heading_tag="h2" if list_index == 0 else "h3",
            )
            icon_element = card_element.find("span", class_="fl-icon")
            assert icon_element and f"fl-icon-{card['value']['icon']}" in icon_element["class"]


def test_sticker_card_block(index_page, placeholder_images, rf):
    test_page = get_sticker_cards_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_titles = ["Cards List with Sticker Cards", "Cards List with Sticker Cards - 4 columns"]

    card_variants = get_sticker_card_variants()
    card_lists = get_cards_list_variants(
        card_variants,
        heading_1=section_titles[0],
        heading_2=section_titles[1],
    )

    # Card Lists
    section_elements = soup.find_all("section", class_="fl-section")
    assert len(section_elements) == len(card_lists)

    for list_index, card_list in enumerate(card_lists):
        section_element = section_elements[list_index]
        assert section_element

        # Section Heading
        assert_section_heading_attributes(section_element, card_list["value"]["heading"], list_index)

        # CTA
        cta_data = card_list["value"]["cta"][0]
        assert_section_cta_attributes(
            section_element,
            cta_data,
            context,
            cta_position=f"block-{list_index + 1}-section.cta",
            cta_text=f"{section_titles[list_index].strip()} - {cta_data['value']['label'].strip()}",
        )

        # Cards
        card_list_div = section_element.find("div", class_="fl-card-grid")
        assert card_list_div

        card_divs = card_list_div.find_all("article", class_="fl-card")
        cards = card_list["value"]["content"][0]["value"]["cards"]
        assert len(card_divs) == len(cards)

        for card_index, card in enumerate(cards):
            card_element = card_divs[card_index]
            # sticker-card.html uses block_level directly; section 0 children are h2, section 1 are h3
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
                heading_tag="h2" if list_index == 0 else "h3",
            )

            images_element = card_element.find("div", class_="fl-card-sticker")
            assert_image_variants_attributes(
                images_element=images_element,
                images_value=card["value"]["image"],
                widths="width-400",
            )


def test_filled_card_block(index_page, rf):
    test_page = get_filled_cards_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_titles = ["Cards List with Filled Cards", "Cards List with Filled Cards - 4 columns"]

    card_variants = get_filled_card_variants()
    card_lists = get_cards_list_variants(
        card_variants,
        heading_1=section_titles[0],
        heading_2=section_titles[1],
    )

    # Card Lists
    section_elements = soup.find_all("section", class_="fl-section")
    assert len(section_elements) == len(card_lists)

    for list_index, card_list in enumerate(card_lists):
        section_element = section_elements[list_index]
        assert section_element

        # Section Heading
        assert_section_heading_attributes(section_element, card_list["value"]["heading"], list_index)

        # CTA
        cta_data = card_list["value"]["cta"][0]
        assert_section_cta_attributes(
            section_element,
            cta_data,
            context,
            cta_position=f"block-{list_index + 1}-section.cta",
            cta_text=f"{section_titles[list_index].strip()} - {cta_data['value']['label'].strip()}",
        )

        # Cards
        card_list_div = section_element.find("div", class_="fl-card-grid")
        assert card_list_div

        card_divs = card_list_div.find_all("article", class_="fl-card")
        cards = card_list["value"]["content"][0]["value"]["cards"]
        assert len(card_divs) == len(cards)

        for card_index, card in enumerate(cards):
            card_element = card_divs[card_index]
            # filled-card.html uses block_level directly; section 0 children are h2, section 1 are h3
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
                heading_tag="h2" if list_index == 0 else "h3",
            )
            tags = card["value"]["tags"]
            tag_elements = card_element.find_all("span", class_="fl-tag")
            assert len(tag_elements) == len(tags)
            for tag_index, tag in enumerate(tags):
                tag_element = tag_elements[tag_index]
                assert_tag_attributes(tag_element, tag)


def test_illustration_card_block(index_page, placeholder_images, rf):
    test_page = get_illustration_cards_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_titles = ["Cards List with Illustration Cards", "Cards List with Illustration Cards - 4 columns"]

    card_variants = get_illustration_card_variants()
    card_lists = get_cards_list_variants(
        card_variants,
        heading_1=section_titles[0],
        heading_2=section_titles[1],
    )

    # Card Lists
    section_elements = soup.find_all("section", class_="fl-section")
    assert len(section_elements) == len(card_lists)

    for list_index, card_list in enumerate(card_lists):
        section_element = section_elements[list_index]
        assert section_element

        # Section Heading
        assert_section_heading_attributes(section_element, card_list["value"]["heading"], list_index)

        # CTA
        cta_data = card_list["value"]["cta"][0]
        assert_section_cta_attributes(
            section_element,
            cta_data,
            context,
            cta_position=f"block-{list_index + 1}-section.cta",
            cta_text=f"{section_titles[list_index].strip()} - {cta_data['value']['label'].strip()}",
        )

        # Cards
        card_list_div = section_element.find("div", class_="fl-card-grid")
        assert card_list_div

        card_divs = card_list_div.find_all("article", class_="fl-card")
        cards = card_list["value"]["content"][0]["value"]["cards"]
        assert len(card_divs) == len(cards)

        for card_index, card in enumerate(cards):
            card_element = card_divs[card_index]
            # illustration-card.html uses block_level directly; section 0 children are h2, section 1 are h3
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
                heading_tag="h2" if list_index == 0 else "h3",
            )
            images_element = card_element.find("div", class_="image-variants-display")
            images_value = card["value"]["image"]
            assert_image_variants_attributes(
                images_element=images_element,
                images_value=images_value,
            )


def test_step_card_block(index_page, placeholder_images, rf):
    test_page = get_step_cards_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    section_titles = ["Step Cards List with 3 columns layout", "Step Cards List with 4 columns layout"]

    card_variants = get_step_card_variants()
    card_lists = get_step_cards_list_variants(
        card_variants,
        heading_1=section_titles[0],
        heading_2=section_titles[1],
    )

    # Card Lists
    section_elements = soup.find_all("section", class_="fl-section")
    assert len(section_elements) == len(card_lists)

    image, dark_image, mobile_image, dark_mobile_image = placeholder_images

    for list_index, card_list in enumerate(card_lists):
        section_element = section_elements[list_index]
        assert section_element

        # Section Heading
        assert_section_heading_attributes(section_element, card_list["value"]["heading"], list_index)

        # CTA
        cta_data = card_list["value"]["cta"][0]
        assert_section_cta_attributes(
            section_element,
            cta_data,
            context,
            cta_position=f"block-{list_index + 1}-section.cta",
            cta_text=f"{section_titles[list_index].strip()} - {cta_data['value']['label'].strip()}",
        )

        # Cards
        card_list_div = section_element.find("div", class_="fl-card-grid")
        assert card_list_div

        card_divs = card_list_div.find_all("article", class_="fl-card")
        cards = card_list["value"]["content"][0]["value"]["cards"]
        assert len(card_divs) == len(cards)

        for card_index, card in enumerate(cards):
            card_element = card_divs[card_index]
            # step-card.html uses block_level directly; section 0 children are h2, section 1 are h3
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-step_cards.card-{card_index + 1}.button-1",
                heading_tag="h2" if list_index == 0 else "h3",
            )
            superheading = card_element.find("p", class_="fl-superheading")
            assert superheading and superheading.get_text().strip() == f"Step {(card_index + 1):>02}"
            images_element = card_element.find("div", class_="image-variants-display")
            assert images_element

            spec = "width-{200,400,600,800,1000,1200,1400,1600,1800,2000}"
            sizes = "(min-width: 768px) 50vw, (min-width: 1024px) 30vw, (min-width: 1440px) 500px, 100vw"

            img_tag = images_element.find("img", class_="display-light")
            assert img_tag
            rendered_image = srcset_image(
                image,
                spec,
                **{
                    "sizes": sizes,
                    "width": image.width,
                    "height": image.height,
                    "loading": "lazy",
                    "class": "display-light",
                },
            )
            image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
            assert img_tag["alt"] == image_soup["alt"]
            assert img_tag["class"] == image_soup["class"]
            assert img_tag["loading"] == image_soup["loading"]
            assert img_tag["width"] == image_soup["width"]
            assert img_tag["height"] == image_soup["height"]
            assert img_tag["src"] == image_soup["src"]

            if card["value"].get("dark_image"):
                img_tag = images_element.find("img", class_="display-dark")
                assert img_tag
                rendered_image = srcset_image(
                    dark_image,
                    spec,
                    **{
                        "sizes": sizes,
                        "width": dark_image.width,
                        "height": dark_image.height,
                        "loading": "lazy",
                        "class": "display-dark",
                    },
                )
                image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
                assert img_tag["alt"] == image_soup["alt"]
                assert img_tag["class"] == image_soup["class"]
                assert img_tag["loading"] == image_soup["loading"]
                assert img_tag["width"] == image_soup["width"]
                assert img_tag["height"] == image_soup["height"]
                assert img_tag["src"] == image_soup["src"]


def test_buttons(index_page, rf):
    test_page = get_buttons_test_page()
    blocks = get_button_blocks()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    main = soup.find("main", class_="fl-main")
    intros = main.find_all("div", class_="fl-intro")
    assert len(intros) == len(blocks)

    for block_index, (intro, block) in enumerate(zip(intros, blocks)):
        buttons_data = block["value"]["buttons"]
        # Store buttons render as fl-store-button; all others render as fl-button
        non_store_data = [b for b in buttons_data if b["type"] != "store_button"]
        store_data = [b for b in buttons_data if b["type"] == "store_button"]

        button_elements = [el for el in intro.find_all("a", class_="fl-button") if "Extended Support Release" not in el.get("data-cta-text", "")]
        assert len(button_elements) == len(non_store_data)

        heading_text = BeautifulSoup(block["value"]["heading"]["heading_text"], "html.parser").get_text()

        for btn_index, (button_data, button_element) in enumerate(zip(non_store_data, button_elements)):
            if button_data["type"] == "button":
                cta_position = f"block-{block_index + 1}-intro.button-{btn_index + 1}"
                cta_text = f"{heading_text.strip()} - {button_data['value']['label'].strip()}"
                assert_button_attributes(
                    button_element=button_element,
                    button_data=button_data,
                    context=context,
                    cta_position=cta_position,
                    cta_text=cta_text,
                )
            elif button_data["type"] == "fxa_button":
                utm_parameters = context["utm_parameters"]
                entrypoint = f"{utm_parameters['utm_source']}-{utm_parameters['utm_campaign']}"
                icon = button_data["value"]["settings"]["icon"]
                icon_position = button_data["value"]["settings"]["icon_position"]
                inner_html = None
                if icon:
                    icon_context = {
                        "extra_class": f"fl-icon-{icon_position}",
                        "icon_name": icon,
                        "hidden": True,
                    }
                    icon_html = render_to_string("components/icon.html", icon_context)
                    inner_html = f"{icon_html}{button_data['value']['label']}"
                rendered_fxa_button = fxa_button(
                    ctx=context,
                    entrypoint=entrypoint,
                    button_text=button_data["value"]["label"],
                    optional_parameters={
                        "utm_campaign": utm_parameters["utm_campaign"],
                    },
                    optional_attributes={
                        "data-cta-text": f"{heading_text.strip()} - {button_data['value']['label'].strip()}",
                        "data-cta-position": f"block-{block_index + 1}-intro.button-{btn_index + 1}",
                        "data-cta-uid": button_data["value"]["settings"]["analytics_id"],
                    },
                    class_name=f"fl-button button-{button_data['value']['settings']['theme']}",
                    inner_html=inner_html,
                )
                fxa_button_soup = BeautifulSoup(rendered_fxa_button, "html.parser").find("a")
                assert button_element.prettify() == fxa_button_soup.prettify()
            elif button_data["type"] == "download_button":
                assert_download_button_attributes(
                    button_element=button_element,
                    button_data=button_data,
                    context=context,
                )
            elif button_data["type"] == "focus_button":
                assert button_data["value"]["label"] in button_element.get_text()
                theme = button_data["value"]["settings"]["theme"]
                if theme:
                    assert f"button-{theme}" in button_element["class"]
                icon = button_data["value"]["settings"]["icon"]
                if icon:
                    assert button_element.find("span", class_=f"fl-icon-{icon}")
                campaign = context["utm_parameters"]["utm_campaign"]
                if button_data["value"]["store"] == "android":
                    assert button_element["href"] == play_store_url(context, "focus", campaign)
                else:
                    assert button_element["href"] == app_store_url(context, "focus", campaign)

        # Store buttons render as fl-store-button, exclude those inside download wrappers
        store_els = [el for el in intro.find_all("a", class_="fl-store-button") if not el.find_parent(class_="c-button-download-thanks")]
        assert len(store_els) == len(store_data)
        campaign = context["utm_parameters"]["utm_campaign"]
        for btn_data, btn_el in zip(store_data, store_els):
            assert f"fl-store-button-{btn_data['value']['store']}" in btn_el["class"]
            if btn_data["value"]["store"] == "android":
                assert btn_el["href"] == play_store_url(context, "firefox", campaign)
            else:
                assert btn_el["href"] == app_store_url(context, "firefox", campaign)


def test_buttons_2026(index_page, rf):
    test_page = get_buttons_2026_test_page()
    blocks = get_button_blocks()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region, block_prefix in [(upper, "upper-"), (lower, "lower-")]:
        intros = region.find_all("div", class_="fl-intro")
        assert len(intros) == len(blocks)

        for block_index, (intro, block) in enumerate(zip(intros, blocks)):
            buttons_data = block["value"]["buttons"]
            # Store buttons render as fl-store-button; all others render as fl-button
            non_store_data = [b for b in buttons_data if b["type"] != "store_button"]
            store_data = [b for b in buttons_data if b["type"] == "store_button"]

            button_elements = [el for el in intro.find_all("a", class_="fl-button") if "Extended Support Release" not in el.get("data-cta-text", "")]
            assert len(button_elements) == len(non_store_data)

            heading_text = BeautifulSoup(block["value"]["heading"]["heading_text"], "html.parser").get_text()

            for btn_index, (button_data, button_element) in enumerate(zip(non_store_data, button_elements)):
                if button_data["type"] == "button":
                    cta_position = f"{block_prefix}block-{block_index + 1}-intro.button-{btn_index + 1}"
                    cta_text = f"{heading_text.strip()} - {button_data['value']['label'].strip()}"
                    assert_button_attributes(
                        button_element=button_element,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )
                elif button_data["type"] == "fxa_button":
                    utm_parameters = context["utm_parameters"]
                    entrypoint = f"{utm_parameters['utm_source']}-{utm_parameters['utm_campaign']}"
                    icon = button_data["value"]["settings"]["icon"]
                    icon_position = button_data["value"]["settings"]["icon_position"]
                    inner_html = None
                    if icon:
                        icon_context = {
                            "extra_class": f"fl-icon-{icon_position}",
                            "icon_name": icon,
                            "hidden": True,
                        }
                        icon_html = render_to_string("components/icon.html", icon_context)
                        inner_html = f"{icon_html}{button_data['value']['label']}"
                    rendered_fxa_button = fxa_button(
                        ctx=context,
                        entrypoint=entrypoint,
                        button_text=button_data["value"]["label"],
                        optional_parameters={
                            "utm_campaign": utm_parameters["utm_campaign"],
                        },
                        optional_attributes={
                            "data-cta-text": f"{heading_text.strip()} - {button_data['value']['label'].strip()}",
                            "data-cta-position": f"{block_prefix}block-{block_index + 1}-intro.button-{btn_index + 1}",
                            "data-cta-uid": button_data["value"]["settings"]["analytics_id"],
                        },
                        class_name=f"fl-button button-{button_data['value']['settings']['theme']}",
                        inner_html=inner_html,
                    )
                    fxa_button_soup = BeautifulSoup(rendered_fxa_button, "html.parser").find("a")
                    assert " ".join(button_element.prettify().split()) == " ".join(fxa_button_soup.prettify().split())
                elif button_data["type"] == "download_button":
                    assert_download_button_attributes(
                        button_element=button_element,
                        button_data=button_data,
                        context=context,
                    )
                elif button_data["type"] == "focus_button":
                    assert button_data["value"]["label"] in button_element.get_text()
                    theme = button_data["value"]["settings"]["theme"]
                    if theme:
                        assert f"button-{theme}" in button_element["class"]
                    icon = button_data["value"]["settings"]["icon"]
                    if icon:
                        assert button_element.find("span", class_=f"fl-icon-{icon}")
                    campaign = context["utm_parameters"]["utm_campaign"]
                    if button_data["value"]["store"] == "android":
                        assert button_element["href"] == play_store_url(context, "focus", campaign)
                    else:
                        assert button_element["href"] == app_store_url(context, "focus", campaign)

            # Store buttons render as fl-store-button, exclude those inside download wrappers
            store_els = [el for el in intro.find_all("a", class_="fl-store-button") if not el.find_parent(class_="c-button-download-thanks")]
            assert len(store_els) == len(store_data)
            campaign = context["utm_parameters"]["utm_campaign"]
            for btn_data, btn_el in zip(store_data, store_els):
                assert f"fl-store-button-{btn_data['value']['store']}" in btn_el["class"]
                if btn_data["value"]["store"] == "android":
                    assert btn_el["href"] == play_store_url(context, "firefox", campaign)
                else:
                    assert btn_el["href"] == app_store_url(context, "firefox", campaign)


def test_banner_block(index_page, placeholder_images, rf):
    banners = get_banner_variants()
    test_page = get_banner_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    # Banner blocks
    banner_divs = soup.find_all("div", class_="fl-banner")
    assert len(banner_divs) == len(banners)

    for index, banner in enumerate(banners):
        banner_element = banner_divs[index]

        settings = banner["value"]["settings"]
        assert f"fl-banner-{settings['theme']}" in banner_element["class"]
        if settings.get("media_after"):
            assert "fl-banner-reverse" in banner_element["class"]
        anchor_id = settings.get("anchor_id")
        if anchor_id:
            assert banner_element.parent.get("id") == anchor_id

        # Heading
        heading_block = banner["value"]["heading"]
        assert_section_heading_attributes(section_element=banner_element, heading_data=heading_block, index=index)

        heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

        # Links with uid in subheading must render with all three CTA tracking attributes.
        subheading_html = banner["value"]["heading"]["subheading_text"]
        subheading_soup = BeautifulSoup(subheading_html, "html.parser")
        uid_link_count = len([a for a in subheading_soup.find_all("a") if a.get("uid")])
        if uid_link_count:
            subheading = banner_element.find("p", class_="fl-subheading")
            rendered_uid_links = subheading.find_all("a", attrs={"data-cta-uid": True}) if subheading else []
            assert len(rendered_uid_links) == uid_link_count, f"Expected {uid_link_count} links with data-cta-uid"
            for link in rendered_uid_links:
                uid = link["data-cta-uid"]
                assert _UUID_RE.match(uid), f"Subheading link {link.get('href')!r} has invalid data-cta-uid: {uid!r}"
                assert link.get("data-cta-text"), f"Subheading link {link.get('href')!r} missing data-cta-text"
                assert link.get("data-cta-position"), f"Subheading link {link.get('href')!r} missing data-cta-position"

        # Buttons
        buttons = banner["value"]["buttons"]
        button_elements = banner_element.find_all("a", class_="fl-button")
        for button_index, button in enumerate(buttons):
            button_element = button_elements[button_index]
            cta_position = f"block-{index + 1}-banner.button-{button_index + 1}"
            cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
            assert_button_attributes(
                button_element=button_element,
                button_data=button,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )

        # Media
        if media := banner["value"]["media"]:
            media = media[0]
            media_element = banner_element.find("div", class_="fl-banner-media")
            assert media_element

            media_value = media["value"]
            if media["type"] == "image":
                images_element = media_element.find("div", class_="image-variants-display")
                assert_image_variants_attributes(images_element=images_element, images_value=media_value)
            elif media["type"] == "video":
                video_div = banner_element.find("div", class_="fl-video")
                assert_video_attributes(video_div, media)
            elif media["type"] == "animation":
                animation_div = banner_element.find("div", class_="fl-video")
                assert_animation_attributes(animation_div, media)
            elif media["type"] == "qr_code":
                assert "has-qr-code" in media_element["class"]
                assert media_element.find("div", class_="fl-banner-qr").find("svg")
                if media_value.get("background"):
                    assert media_element.find("img")


def test_banner_2026_block(index_page, placeholder_images, rf):
    banners = get_banner_2026_variants()
    test_page = get_banner_2026_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, (region_name, region) in enumerate([("upper", upper), ("lower", lower)]):
        banner_divs = region.find_all("div", class_="fl-banner")
        assert len(banner_divs) == len(banners)

        # The page template shares a heading counter across upper and lower content,
        # so lower-region banners always render as h2 (counter > 0 after upper).
        heading_index_offset = region_index * len(banners)

        for index, banner in enumerate(banners):
            banner_element = banner_divs[index]

            settings = banner["value"]["settings"]
            assert f"fl-banner-{settings['theme']}" in banner_element["class"]
            if settings.get("media_after"):
                assert "fl-banner-reverse" in banner_element["class"]
            anchor_id = settings.get("anchor_id")
            if anchor_id:
                assert banner_element.parent.get("id") == anchor_id

            heading_block = banner["value"]["heading"]
            assert_section_heading_attributes(section_element=banner_element, heading_data=heading_block, index=heading_index_offset + index)

            heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

            # Links with uid in subheading must render with all three CTA tracking attributes.
            subheading_html = banner["value"]["heading"]["subheading_text"]
            subheading_soup = BeautifulSoup(subheading_html, "html.parser")
            uid_link_count = len([a for a in subheading_soup.find_all("a") if a.get("uid")])
            if uid_link_count:
                subheading = banner_element.find("p", class_="fl-subheading")
                rendered_uid_links = subheading.find_all("a", attrs={"data-cta-uid": True}) if subheading else []
                assert len(rendered_uid_links) == uid_link_count, f"Expected {uid_link_count} links with data-cta-uid"
                for link in rendered_uid_links:
                    uid = link["data-cta-uid"]
                    assert _UUID_RE.match(uid), f"Subheading link {link.get('href')!r} has invalid data-cta-uid: {uid!r}"
                    assert link.get("data-cta-text"), f"Subheading link {link.get('href')!r} missing data-cta-text"
                    assert link.get("data-cta-position"), f"Subheading link {link.get('href')!r} missing data-cta-position"

            buttons = banner["value"]["buttons"]
            button_elements = banner_element.find_all("a", class_="fl-button")
            for button_index, button in enumerate(buttons):
                button_element = button_elements[button_index]
                cta_position = f"{region_name}-block-{index + 1}-banner.button-{button_index + 1}"
                cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
                assert_button_attributes(
                    button_element=button_element,
                    button_data=button,
                    context=context,
                    cta_position=cta_position,
                    cta_text=cta_text,
                )

            if media := banner["value"]["media"]:
                media = media[0]
                media_element = banner_element.find("div", class_="fl-banner-media")
                assert media_element

                media_value = media["value"]
                if media["type"] == "image":
                    images_element = media_element.find("div", class_="image-variants-display")
                    assert_image_variants_attributes(images_element=images_element, images_value=media_value)
                elif media["type"] == "video":
                    video_div = banner_element.find("div", class_="fl-video")
                    assert_video_attributes(video_div, media)
                elif media["type"] == "animation":
                    animation_div = banner_element.find("div", class_="fl-video")
                    assert_animation_attributes(animation_div, media)
                elif media["type"] == "qr_code":
                    assert "has-qr-code" in media_element["class"]
                    assert media_element.find("div", class_="fl-banner-qr").find("svg")
                    if media_value.get("background"):
                        assert media_element.find("img")


def test_kit_banner_block(index_page, rf):
    banners = get_kit_banner_variants()
    test_page = get_kit_banner_test_page()

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    # Kit Banner blocks
    banner_elements = soup.find_all("div", class_="fl-banner-kit")
    assert len(banner_elements) == len(banners)

    for index, banner in enumerate(banners):
        banner_element = banner_elements[index]

        settings = banner["value"]["settings"]
        theme = settings["theme"].replace("filled-", "").replace("filled", "")
        if theme:
            assert f"fl-banner-kit-{theme}" in banner_element["class"]
        anchor_id = settings.get("anchor_id")
        if anchor_id:
            assert banner_element.parent.get("id") == anchor_id

        # Heading
        heading_block = banner["value"]["heading"]
        assert_section_heading_attributes(section_element=banner_element, heading_data=heading_block, index=index)

        heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

        # Buttons
        buttons = banner["value"]["buttons"]
        button_elements = banner_element.find_all("a", class_="fl-button")
        for button_index, button in enumerate(buttons):
            button_element = button_elements[button_index]
            cta_position = f"block-{index + 1}-kit_banner.button-{button_index + 1}"
            cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
            assert_button_attributes(
                button_element=button_element,
                button_data=button,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )


def test_kit_banner_curious_animation(index_page, rf):
    test_page = get_kit_banner_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Find the curious animation banner by anchor ID
    animation_container = soup.find(id="filled-banner-curious-animation")
    assert animation_container is not None

    banner = animation_container.find("div", class_="fl-banner-kit")
    assert banner is not None

    # The curious-animation theme applies fl-banner-kit-curious-animation class
    assert "fl-banner-kit-curious-animation" in banner["class"]

    # Animation wrapper is rendered
    animation_wrapper = banner.find("div", class_="fl-banner-animation")
    assert animation_wrapper is not None

    # Video element is present (autoplay_loop renders a plain <video>)
    video = animation_wrapper.find("video")
    assert video is not None

    # Pause button is present
    pause_button = animation_wrapper.find("button", class_="js-animation-pause")
    assert pause_button is not None

    # Pause button has accessible label attributes
    assert pause_button.get("data-label-pause") is not None
    assert pause_button.get("data-label-play") is not None

    # Pause icon is visible by default
    pause_icon = pause_button.find(class_="js-pause-icon")
    assert pause_icon is not None
    assert pause_icon.get("hidden") is None

    # Play icon is hidden by default
    play_icon = pause_button.find(class_="js-play-icon")
    assert play_icon is not None
    assert play_icon.get("hidden") is not None


def test_topic_list_2026_block(index_page, placeholder_images, rf):
    upper_variants = get_topic_list_upper_variants()
    lower_variants = get_topic_list_lower_variants()
    test_page = get_topic_list_2026_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_name, region, variants in [("upper", upper, upper_variants), ("lower", lower, lower_variants)]:
        topic_lists = region.find_all("div", class_="fl-topic-list")
        assert len(topic_lists) == len(variants)

        for block_index, (topic_list_element, variant) in enumerate(zip(topic_lists, variants)):
            topics = variant["value"]["topics"]

            # Sidebar links match anchor IDs
            sidebar_links = topic_list_element.find("div", class_="fl-topic-list-sidebar").find_all("a")
            assert len(sidebar_links) == len(topics)
            for topic, link in zip(topics, sidebar_links):
                assert link["href"] == f"#{topic['value']['anchor_id']}"
                assert topic["value"]["short_title"] in link.get_text()

            # Topic sections have correct anchor IDs, image, heading and content
            topic_sections = topic_list_element.find("div", class_="fl-topic-list-content").find_all("section", class_="fl-topic")
            assert len(topic_sections) == len(topics)
            for topic_index, (topic, section) in enumerate(zip(topics, topic_sections)):
                assert section["id"] == topic["value"]["anchor_id"]

                # Image — rendered with "width-400" spec
                img_tag = section.find("img")
                assert img_tag
                assert "width-400" in img_tag["src"]

                # Heading
                heading_text = BeautifulSoup(topic["value"]["heading"]["heading_text"], "html.parser").get_text()
                heading = section.find("h2", class_="fl-heading")
                assert heading and heading_text in heading.get_text()

                # Content
                content_text = BeautifulSoup(topic["value"]["content"], "html.parser").get_text()
                assert content_text in section.get_text()

                # Buttons
                buttons = topic["value"]["buttons"]
                button_elements = section.find_all("a", class_="fl-button")
                for button_index, button in enumerate(buttons):
                    button_element = button_elements[button_index]
                    cta_position = f"{region_name}-block-{block_index + 1}-topic_list.topic-{topic_index + 1}.button-{button_index + 1}"
                    cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
                    assert_button_attributes(
                        button_element=button_element,
                        button_data=button,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_kit_banner_2026_block(index_page, placeholder_images, rf):
    banners = get_kit_banner_variants()
    test_page = get_kit_banner_2026_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, (region_name, region) in enumerate([("upper", upper), ("lower", lower)]):
        banner_elements = region.find_all("div", class_="fl-banner-kit")
        assert len(banner_elements) == len(banners)

        heading_index_offset = region_index * len(banners)

        for index, banner in enumerate(banners):
            banner_element = banner_elements[index]

            settings = banner["value"]["settings"]
            theme = settings["theme"].replace("filled-", "").replace("filled", "")
            if theme:
                assert f"fl-banner-kit-{theme}" in banner_element["class"]
            anchor_id = settings.get("anchor_id")
            if anchor_id:
                assert banner_element.parent.get("id") == anchor_id

            heading_block = banner["value"]["heading"]
            assert_section_heading_attributes(
                section_element=banner_element,
                heading_data=heading_block,
                index=heading_index_offset + index,
            )

            heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

            buttons = banner["value"]["buttons"]
            button_elements = banner_element.find_all("a", class_="fl-button")
            for button_index, button in enumerate(buttons):
                button_element = button_elements[button_index]
                cta_position = f"{region_name}-block-{index + 1}-kit_banner.button-{button_index + 1}"
                cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
                assert_button_attributes(
                    button_element=button_element,
                    button_data=button,
                    context=context,
                    cta_position=cta_position,
                    cta_text=cta_text,
                )


# Homepage


def test_home_intro_block(index_page, rf):
    home_intro = get_home_intro()
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    intro_div = soup.find("div", class_="fl-home-intro")

    heading_block = home_intro["value"]["heading"]
    assert_section_heading_attributes(section_element=intro_div, heading_data=heading_block, index=0)

    superheading_element = intro_div.find("p", class_="fl-superheading")
    superheading_link = superheading_element.find("a")
    assert superheading_link["href"] == add_utm_parameters(context, "https://mozilla.org")

    heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()
    button = home_intro["value"]["buttons"][0]
    button_element = intro_div.find("a", class_="fl-button")
    cta_position = "upper-block-1-intro.button-1"
    cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
    assert_download_button_attributes(
        button_element=button_element,
        button_data=button,
        context=context,
        cta_position=cta_position,
        cta_text=cta_text,
    )


def test_home_sticker_cards_list_block(index_page, placeholder_images, rf):
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    cards_list = get_cards_list()

    cards_list_div = soup.find("div", class_="fl-card-grid")
    assert cards_list_div

    card_elements = cards_list_div.find_all("article", class_="fl-sticker-card")

    cards = cards_list["value"]["cards"]
    assert len(card_elements) == len(cards)

    for index, card in enumerate(cards):
        card_element = card_elements[index]
        assert_card_attributes(
            card_element=card_element,
            card_data=card,
            context=context,
            heading_tag="h2",
        )

        images_element = card_element.find("div", class_="fl-card-sticker")
        assert_image_variants_attributes(
            images_element=images_element,
            images_value=card["value"]["image"],
            widths="width-400",
        )


def test_home_carousel_block(index_page, placeholder_images, rf):
    carousel = get_home_carousel()
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    carousel_div = soup.find("div", class_="fl-carousel")
    assert carousel_div

    heading_block = carousel["value"]["heading"]
    assert_section_heading_attributes(section_element=carousel_div, heading_data=heading_block, index=2)

    slides = carousel["value"]["slides"]
    slides_element = carousel_div.find("div", class_="fl-carousel-slides")

    assert slides_element

    control_elements = slides_element.find_all("li", class_="fl-carousel-control-item")
    assert len(control_elements) == len(slides)

    slide_elements = slides_element.find_all("div", class_="fl-carousel-slide")
    assert len(slide_elements) == len(slides)

    for slide_index, slide in enumerate(slides):
        control_element = control_elements[slide_index]
        assert control_element
        assert control_element.get_text().strip() == BeautifulSoup(slide["value"]["headline"], "html.parser").get_text().strip()

        slide_element = slide_elements[slide_index]
        assert slide_element

        images_element = slide_element.find("div", class_="fl-carousel-image")

        image_value = slide["value"]["image"]

        assert_image_variants_attributes(
            images_element=images_element,
            images_value=image_value,
            widths="width-{400,600,800,1000}",
            sizes="(min-width: 900px) 800px, 100vw",
        )


def test_showcase_block(index_page, placeholder_images, rf):
    showcase_variants = get_showcase_variants()
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    showcase_sections = soup.find_all("section", class_="fl-showcase")
    assert len(showcase_sections) == 2

    image, dark_image, mobile_image, dark_mobile_image = placeholder_images

    showcase_with_title = showcase_variants["with_title"]
    showcase_no_title = showcase_variants["no_title"]

    for index, showcase in enumerate([showcase_with_title, showcase_no_title]):
        showcase_element = showcase_sections[index]

        assert f"fl-showcase-{showcase['value']['settings']['layout']}" in showcase_element["class"]

        headline_text = BeautifulSoup(showcase["value"]["headline"], "html.parser").get_text().strip()
        heading_element = showcase_element.find("h2", class_="fl-heading")
        assert heading_element and heading_element.get_text().strip() == headline_text

        figure = showcase_element.find("figure", class_="fl-showcase-image")
        assert figure

        image_value = showcase["value"]["media"][0]["value"]

        assert_image_variants_attributes(
            images_element=figure,
            images_value=image_value,
        )

        caption_element = figure.find("figcaption", class_="fl-showcase-caption")
        assert caption_element

        caption_text = BeautifulSoup(showcase["value"]["caption_description"], "html.parser").get_text().strip()
        description_element = caption_element.find("p")
        assert description_element and description_element.get_text().strip() == caption_text

        if showcase["value"]["caption_title"]:
            caption_title_text = BeautifulSoup(showcase["value"]["caption_title"], "html.parser").get_text().strip()
            title_element = caption_element.find("h3", class_="fl-subheading")
            assert title_element and title_element.get_text().strip() == caption_title_text


def test_card_gallery_block(index_page, placeholder_images, rf):
    image, _, _, _ = placeholder_images
    rendered_image = srcset_image(
        image,
        "width-{400,600,800,1000,1200}",
        **{
            "sizes": "(min-width: 900px) 70vw, 100vw",
            "width": image.width,
            "loading": "lazy",
        },
    )
    image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")

    card_gallery = get_card_gallery()
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    gallery_div = soup.find("div", class_="fl-card-gallery")
    assert gallery_div

    heading = card_gallery["value"]["heading"]
    assert_section_heading_attributes(section_element=gallery_div, heading_data=heading, index=5)

    main_card = card_gallery["value"]["main_card"]
    main_card_element = gallery_div.find("div", class_="fl-card-gallery-main-card")
    assert main_card_element

    icon = main_card["icon"]
    icon_element = main_card_element.find("span", class_="fl-icon")
    assert icon_element and f"fl-icon-{icon}" in icon_element["class"]

    headline_text = BeautifulSoup(main_card["headline"], "html.parser").get_text()
    heading_element = main_card_element.find("h3", class_="fl-card-gallery-heading")
    assert heading_element and heading_element.get_text().strip() == headline_text.strip()

    description = BeautifulSoup(main_card["description"], "html.parser").prettify()
    description_element = main_card_element.find("div", class_="fl-card-gallery-body")
    assert description_element and description_element.find_next().prettify().strip() == description.strip()

    button = main_card["buttons"][0]
    button_element = main_card_element.find("a", class_="fl-button")
    cta_position = "lower-block-3-card_gallery.main-card.button-1"
    cta_text = f"{headline_text.strip()} - {button['value']['label'].strip()}"
    assert_button_attributes(
        button_element=button_element,
        button_data=button,
        context=context,
        cta_position=cta_position,
        cta_text=cta_text,
    )

    image_element = main_card_element.find("img")
    assert image_element["alt"] == image_soup["alt"]
    assert image_element["loading"] == image_soup["loading"]
    assert image_element["width"] == image_soup["width"]
    assert image_element["src"] == image_soup["src"]

    secondary_card = card_gallery["value"]["secondary_card"]
    secondary_card_element = gallery_div.find("div", class_="fl-card-gallery-secondary-card")
    assert secondary_card_element

    icon = secondary_card["icon"]
    icon_element = secondary_card_element.find("span", class_="fl-icon")
    assert icon_element and f"fl-icon-{icon}" in icon_element["class"]

    headline_text = BeautifulSoup(secondary_card["headline"], "html.parser").get_text()
    heading_element = secondary_card_element.find("h3", class_="fl-card-gallery-heading")
    assert heading_element and heading_element.get_text().strip() == headline_text.strip()

    description = BeautifulSoup(secondary_card["description"], "html.parser").prettify()
    description_element = secondary_card_element.find("div", class_="fl-card-gallery-body")
    assert description_element and description_element.find_next().prettify().strip() == description.strip()

    button = secondary_card["buttons"][0]
    button_element = secondary_card_element.find("a", class_="fl-button")
    cta_position = "lower-block-3-card_gallery.secondary-card.button-1"
    cta_text = f"{headline_text.strip()} - {button['value']['label'].strip()}"
    assert_button_attributes(
        button_element=button_element,
        button_data=button,
        context=context,
        cta_position=cta_position,
        cta_text=cta_text,
    )

    image_element = secondary_card_element.find("img")
    assert image_element["alt"] == image_soup["alt"]
    assert image_element["loading"] == image_soup["loading"]
    assert image_element["width"] == image_soup["width"]
    assert image_element["src"] == image_soup["src"]

    callout_card = card_gallery["value"]["callout_card"]
    callout_card_element = gallery_div.find("div", class_="fl-card-gallery-callout-card")
    assert callout_card_element

    headline_text = BeautifulSoup(callout_card["headline"], "html.parser").get_text()
    heading_element = callout_card_element.find("h3", class_="fl-gallery-callout-card-heading")
    assert heading_element and heading_element.get_text().strip() == headline_text.strip()

    description = BeautifulSoup(callout_card["description"], "html.parser").prettify()
    description_element = callout_card_element.find("div", class_="fl-card-gallery-body")
    assert description_element and description_element.find_next().prettify().strip() == description.strip()


def test_home_kit_banner_block(index_page, rf):
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    kit_banner = get_kit_banner()

    banner_element = soup.find("div", class_="fl-banner-kit")
    assert banner_element
    assert "fl-banner-kit-diving-in" in banner_element["class"]

    # Settings
    settings = kit_banner["value"]["settings"]
    anchor_id = settings.get("anchor_id")
    if anchor_id:
        assert banner_element.parent.get("id") == anchor_id

    assert_section_heading_attributes(
        section_element=banner_element,
        heading_data=kit_banner["value"]["heading"],
        index=7,
    )

    heading_text = BeautifulSoup(kit_banner["value"]["heading"]["heading_text"], "html.parser").get_text()
    button = kit_banner["value"]["buttons"][0]
    assert_button_attributes(
        button_element=banner_element.find("a", class_="fl-button"),
        button_data=button,
        context=test_page.get_context(request),
        cta_position="lower-block-4-kit_banner.button-1",
        cta_text=f"{heading_text} - {button['value']['label'].strip()}",
    )


def test_home_pre_footer_cta(index_page, rf):
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    pre_footer_cta = get_pre_footer_cta_snippet()

    cta_element = soup.find("div", class_="fl-pre-footer-cta")
    assert cta_element

    link_element = cta_element.find("a", class_="fl-pre-footer-cta-button")
    assert link_element

    assert link_element.get_text().strip() == pre_footer_cta.label.strip()

    # data might be pointing the link to a different host,
    # so we only validate the remainder
    assert strip_host(link_element["href"]) == "/thanks/"
    assert link_element["data-cta-position"] == "pre-footer-cta"
    assert link_element["data-cta-text"] == pre_footer_cta.label.strip()
    assert link_element["data-cta-uid"] == pre_footer_cta.analytics_id


# Articles


def test_theme_page_blocks(index_page, rf):
    page = get_article_theme_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    intro_div = soup.find("div", class_="fl-intro")
    intro_data = get_theme_page_intro()
    assert_section_heading_attributes(
        section_element=intro_div,
        heading_data=intro_data["value"]["heading"],
        index=0,
    )

    sections = soup.find_all("section", class_="fl-section")
    assert len(sections) == 3

    images = get_placeholder_images()
    image_ids = {img.id: img for img in images}

    # Illustration Card Articles
    illustration_card_section_data = get_theme_page_illustration_cards_section()
    illustration_card_article_section = sections[0]

    assert illustration_card_article_section.find(class_="fl-card-grid")
    illustration_card_articles = illustration_card_article_section.find_all("article", class_="fl-illustration-card")
    illustration_card_articles_data = illustration_card_section_data["value"]["content"][0]["value"]["cards"]
    assert len(illustration_card_articles) == len(illustration_card_articles_data)

    for i, article_data in enumerate(illustration_card_articles_data):
        card_element = illustration_card_articles[i]
        article_id = article_data["value"]["article"]
        article = ArticleDetailPage.objects.get(id=article_id)
        overrides = article_data["value"].get("overrides", {})

        assert_article_card_attributes(
            card_element=card_element,
            article=article,
            card_data=article_data,
            card_list_type="illustration_card",
        )

        image_id = overrides.get("image") or article.featured_image.id
        img = image_ids[image_id]
        rendered_image = srcset_image(
            img,
            "width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
            **{
                "sizes": "(min-width: 768px) 50vw, (min-width: 1440px) 680px,100vw",
                "width": img.width,
                "height": img.height,
                "loading": "lazy",
            },
        )
        img_tag = card_element.find("img")
        image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
        assert img_tag["alt"] == image_soup["alt"]
        assert img_tag["loading"] == image_soup["loading"]
        assert img_tag["width"] == image_soup["width"]
        assert img_tag["height"] == image_soup["height"]
        assert img_tag["src"] == image_soup["src"]

    # Icon Cards Section
    icon_card_section_data = get_theme_page_icon_cards_section()
    icon_card_section = sections[1]
    assert icon_card_section and icon_card_section.find(class_="fl-card-grid")

    assert_section_heading_attributes(
        section_element=icon_card_section,
        heading_data=icon_card_section_data["value"]["heading"],
        index=1,
    )

    assert icon_card_section.find(class_="fl-card-grid")
    icon_card_articles = icon_card_section.find_all("article", class_="fl-illustration-card fl-illustration-icon-card")
    icon_card_articles_data = icon_card_section_data["value"]["content"][0]["value"]["cards"]
    assert len(icon_card_articles) == len(icon_card_articles_data)

    for i, article_data in enumerate(icon_card_articles_data):
        card_element = icon_card_articles[i]
        article_id = article_data["value"]["article"]
        article = ArticleDetailPage.objects.get(id=article_id)
        overrides = article_data["value"].get("overrides", {})

        assert_article_card_attributes(
            card_element=card_element,
            article=article,
            card_data=article_data,
            card_list_type="icon_card",
        )

        icon_name = overrides.get("icon") or article.icon or "globe"
        icon_element = card_element.find("span", class_="fl-icon")
        assert icon_element and f"fl-icon-{icon_name}" in icon_element["class"]

    # Sticker Row Articles
    sticker_row_section_data = get_theme_page_sticker_row_section()
    sticker_row_section = sections[2]

    assert_section_heading_attributes(
        section_element=sticker_row_section,
        heading_data=sticker_row_section_data["value"]["heading"],
        index=2,
    )

    assert sticker_row_section and sticker_row_section.find(class_="fl-stacked-article-list")
    sticker_row_articles = sticker_row_section.find_all("article", class_="fl-article-item")
    sticker_row_articles_data = sticker_row_section_data["value"]["content"][0]["value"]["cards"]
    assert len(sticker_row_articles) == len(sticker_row_articles_data)

    for i, article_data in enumerate(sticker_row_articles_data):
        card_element = sticker_row_articles[i]
        article_id = article_data["value"]["article"]
        article = ArticleDetailPage.objects.get(id=article_id)
        overrides = article_data["value"].get("overrides", {})

        assert_article_card_attributes(
            card_element=card_element,
            article=article,
            card_data=article_data,
            card_list_type="sticker_row",
        )

        image_id = overrides.get("image") or article.sticker.id
        img = image_ids[image_id]
        rendered_icon = image(img, "width-400").img_tag()
        sticker_element = card_element.find("img")
        assert sticker_element.prettify() == BeautifulSoup(rendered_icon, "html.parser").find("img").prettify()


def test_theme_hub_page_blocks(index_page, rf):
    page = get_article_theme_hub_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    # Verify the split-page layout exists
    upper_section = soup.find("div", class_="fl-split-page-upper")
    lower_section = soup.find("div", class_="fl-split-page-lower")
    assert upper_section, "Upper section should exist when upper_content has blocks"
    assert lower_section, "Lower section should exist when upper_content has blocks"

    # Test Upper Content - Intro Block
    upper_content_data = get_theme_hub_page_upper_content()
    assert len(upper_content_data) == 1, "Upper content should have 1 intro block"

    intro_div = upper_section.find("div", class_="fl-intro")
    assert intro_div, "Intro block should be in upper section"

    intro_data = upper_content_data[0]
    assert_section_heading_attributes(
        section_element=intro_div,
        heading_data=intro_data["value"]["heading"],
        index=0,
    )

    # Test Lower Content - Sections
    sections = lower_section.find_all("section", class_="fl-section")
    assert len(sections) == 2, "Lower content should have 2 sections"

    images = get_placeholder_images()
    image_ids = {img.id: img for img in images}

    # Illustration Cards Section (first section in lower content)
    illustration_section_data = get_theme_hub_illustration_cards_section()
    illustration_section = sections[0]

    assert illustration_section.find(class_="fl-card-grid")
    illustration_card_articles = illustration_section.find_all("article", class_="fl-illustration-card")
    illustration_card_articles_data = illustration_section_data["value"]["content"][0]["value"]["cards"]
    assert len(illustration_card_articles) == len(illustration_card_articles_data)

    for i, article_data in enumerate(illustration_card_articles_data):
        card_element = illustration_card_articles[i]
        article_id = article_data["value"]["article"]
        article = ArticleDetailPage.objects.get(id=article_id)
        overrides = article_data["value"].get("overrides", {})

        assert_article_card_attributes(
            card_element=card_element,
            article=article,
            card_data=article_data,
            card_list_type="illustration_card",
        )

        image_id = overrides.get("image") or article.featured_image.id
        img = image_ids[image_id]
        rendered_image = srcset_image(
            img,
            "width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
            **{
                "sizes": "(min-width: 768px) 50vw, (min-width: 1440px) 680px,100vw",
                "width": img.width,
                "height": img.height,
                "loading": "lazy",
            },
        )
        img_tag = card_element.find("img")
        image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
        assert img_tag["alt"] == image_soup["alt"]
        assert img_tag["loading"] == image_soup["loading"]
        assert img_tag["width"] == image_soup["width"]
        assert img_tag["height"] == image_soup["height"]
        assert img_tag["src"] == image_soup["src"]

    # Sticker Row Section (second section in lower content)
    sticker_row_section_data = get_theme_hub_page_sticker_row_section()
    sticker_row_section = sections[1]

    assert_section_heading_attributes(
        section_element=sticker_row_section,
        heading_data=sticker_row_section_data["value"]["heading"],
        index=1,
    )

    assert sticker_row_section and sticker_row_section.find(class_="fl-stacked-article-list")
    sticker_row_articles = sticker_row_section.find_all("article", class_="fl-article-item")
    sticker_row_articles_data = sticker_row_section_data["value"]["content"][0]["value"]["cards"]
    assert len(sticker_row_articles) == len(sticker_row_articles_data)

    for i, article_data in enumerate(sticker_row_articles_data):
        card_element = sticker_row_articles[i]
        article_id = article_data["value"]["article"]
        article = ArticleDetailPage.objects.get(id=article_id)
        overrides = article_data["value"].get("overrides", {})

        assert_article_card_attributes(
            card_element=card_element,
            article=article,
            card_data=article_data,
            card_list_type="sticker_row",
        )

        image_id = overrides.get("sticker") or article.sticker.id
        img = image_ids[image_id]
        rendered_sticker = image(img, "width-400").img_tag()
        sticker_element = card_element.find("img")
        assert sticker_element.prettify() == BeautifulSoup(rendered_sticker, "html.parser").find("img").prettify()


def test_illustration_card_renders_featured_image_without_override(index_page, rf):
    """When an illustration card has no image override, the article's featured_image
    should be rendered instead of the placeholder image."""
    page = get_article_theme_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    sections = soup.find_all("section", class_="fl-section")
    illustration_section = sections[0]
    illustration_cards = illustration_section.find_all("article", class_="fl-illustration-card")

    articles = get_article_pages()
    images = get_placeholder_images()
    image_ids = {img.id: img for img in images}

    # Card at index 1 has overrides.image = None, so it should fall back
    # to the article's featured_image (mobile_image for featured_article_2)
    card_element = illustration_cards[1]
    article = articles[1]
    img_tag = card_element.find("img")

    # Should NOT be the placeholder
    assert img_tag["src"] != "/media/img/firefox/flare/card-placeholder.png"

    # Should match the article's featured_image rendered as srcset_image
    expected_img = image_ids[article.featured_image.id]
    rendered_image = srcset_image(
        expected_img,
        "width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
        **{
            "sizes": "(min-width: 768px) 50vw, (min-width: 1440px) 680px,100vw",
            "width": expected_img.width,
            "height": expected_img.height,
            "loading": "lazy",
        },
    )
    image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
    assert img_tag["alt"] == image_soup["alt"]
    assert img_tag["src"] == image_soup["src"]
    assert img_tag["width"] == image_soup["width"]
    assert img_tag["height"] == image_soup["height"]


def test_sticker_row_renders_sticker_without_override(index_page, rf):
    """When a sticker row card has no image override, the article's sticker
    should be rendered instead of the placeholder image."""
    page = get_article_theme_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    sections = soup.find_all("section", class_="fl-section")
    sticker_section = sections[2]
    sticker_row_articles = sticker_section.find_all("article", class_="fl-article-item")

    articles = get_article_pages()
    images = get_placeholder_images()
    image_ids = {img.id: img for img in images}

    # Card at index 1 has overrides.image = None (articles[3] = regular_article_2),
    # so it should fall back to the article's sticker
    card_element = sticker_row_articles[1]

    section_data = get_theme_page_sticker_row_section()
    card_data = section_data["value"]["content"][0]["value"]["cards"][1]
    article_ids = {article.id: article for article in articles}
    article = article_ids[card_data["value"]["article"]]
    sticker_element = card_element.find("img")

    # Should NOT be the Firefox logo placeholder
    assert sticker_element["src"] != "/media/img/logos/firefox/firefox-logo.svg"

    # Should match the article's sticker rendered with image()
    expected_img = image_ids[article.sticker.id]
    rendered_icon = image(expected_img, "width-400").img_tag()
    expected_soup = BeautifulSoup(rendered_icon, "html.parser").find("img")
    assert sticker_element.prettify() == expected_soup.prettify()


def test_icon_card_renders_article_icon_without_override(index_page, rf):
    """When an icon card has no icon override, the article's icon
    should be rendered instead of the default 'globe' icon."""
    page = get_article_theme_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    sections = soup.find_all("section", class_="fl-section")
    icon_section = sections[1]
    icon_card_articles = icon_section.find_all("article", class_="fl-illustration-card fl-illustration-icon-card")

    articles = get_article_pages()

    # Card at index 1 has overrides.icon = "" (articles[2] = regular_article_1, icon="apple"),
    # so it should fall back to the article's icon, not the default "globe"
    card_element = icon_card_articles[1]
    article = articles[2]
    icon_element = card_element.find("span", class_="fl-icon")
    assert icon_element is not None
    assert f"fl-icon-{article.icon}" in icon_element["class"]
    assert "fl-icon-globe" not in icon_element["class"]


def test_mobile_store_qr_code_block(index_page, placeholder_images, rf):
    page = get_mobile_store_qr_code_test_page()
    block_data = get_mobile_store_qr_code()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper, "Upper section should exist when upper_content has blocks"
    assert lower, "Lower section should exist when upper_content has blocks"

    upper_qr = upper.find("section", class_="fl-mobile-store-qr-section")
    assert upper_qr, "QR code section should render in upper content"

    heading_div = upper_qr.find("div", class_="fl-mobile-store-qr-heading")
    assert heading_div, "Heading div should render when heading_text is present"
    expected_heading = BeautifulSoup(block_data["value"]["heading"]["heading_text"], "html.parser").get_text()
    assert expected_heading in upper_qr.get_text()

    qr_code_div = upper_qr.find("div", class_="fl-mobile-store-qr-code")
    assert qr_code_div, "QR code div should be present"
    assert qr_code_div.find("svg"), "QR code SVG should be rendered inside the QR code div"

    assert upper_qr.find("div", class_="fl-mobile-store-buttons"), "Store buttons should render"

    mobile_image_div = upper_qr.find("div", class_="fl-mobile-store-mobile-image")
    assert mobile_image_div, "Mobile image div should be present"
    assert mobile_image_div.find("img"), "Mobile image should render an img element"

    lower_qr_section = lower.find("section", class_="fl-mobile-store-qr-section")
    heading_div = lower_qr_section.find("div", class_="fl-mobile-store-qr-heading")
    assert heading_div, "Heading div should render when heading_text is present"
    expected_heading = BeautifulSoup(block_data["value"]["heading"]["heading_text"], "html.parser").get_text()
    assert expected_heading in lower_qr_section.get_text()

    qr_code_div = lower_qr_section.find("div", class_="fl-mobile-store-qr-code")
    assert qr_code_div, "QR code div should be present"
    assert qr_code_div.find("svg"), "QR code SVG should be rendered inside the QR code div"

    assert lower_qr_section.find("div", class_="fl-mobile-store-buttons"), "Store buttons should render"

    lower_mobile_image_div = lower_qr_section.find("div", class_="fl-mobile-store-mobile-image")
    assert lower_mobile_image_div, "Mobile image div should be present"
    assert lower_mobile_image_div.find("img"), "Mobile image should render an img element"


def test_freeform_page_2026_split_layout(index_page, rf):
    page = get_freeform_page_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper, "Upper section should exist when upper_content has blocks"
    assert lower, "Lower section should exist when upper_content has blocks"

    # Upper content contains the QR code section
    assert upper.find("section", class_="fl-mobile-store-qr-section")

    # Lower content contains the section with cards
    sections = lower.find_all("section", class_="fl-section")
    assert len(sections) == 1
    card_articles = sections[0].find_all("article", class_="fl-illustration-card")
    assert len(card_articles) == 3, "Should render cards for Android, iOS, and Focus"


def test_freeform_page_2026_single_column_layout(index_page, rf):
    page = get_mobile_store_qr_code_test_page()
    page.upper_content = []
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not soup.find("div", class_="fl-split-page-upper"), "Upper section should not exist when upper_content is empty"
    assert not soup.find("div", class_="fl-split-page-lower"), "Lower section should not exist when upper_content is empty"
    main = soup.find("main", class_="fl-main")
    assert main and "has-gradient-bottom" in main.get("class", [])


# ---------------------------------------------------------------------------
# 2026 Blocks
# ---------------------------------------------------------------------------


def test_intro_2026_block(index_page, placeholder_images, rf):
    variants = get_intro_2026_variants()
    page = get_intro_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper, "Upper section should exist"
    assert lower, "Lower section should exist"

    # Both upper and lower contain all variants
    for region_index, region in enumerate([upper, lower]):
        intro_divs = region.find_all("div", class_="fl-intro")
        assert len(intro_divs) == len(variants)

        for index, variant in enumerate(variants):
            intro_el = intro_divs[index]
            value = variant["value"]
            intro_classes = intro_el.get("class", [])

            # Heading: first block in upper gets h1, all others get h2
            heading_text = BeautifulSoup(value["heading"]["heading_text"], "html.parser").get_text()
            heading_tag = "h1" if (region_index == 0 and index == 0) else "h2"
            heading = intro_el.find(heading_tag, class_="fl-heading")
            assert heading and heading_text in heading.get_text()

            # Settings: layout
            layout = value["settings"]["layout"]
            if layout == "vertical":
                assert "fl-intro-vertical" in intro_classes
            elif layout == "right" and value["media"]:
                assert "fl-intro-media-right" in intro_classes
            elif layout == "left" and value["media"]:
                assert "fl-intro-media-left" in intro_classes

            # Settings: slim
            if value["settings"]["slim"]:
                assert "is-slim" in intro_classes
            else:
                assert "is-slim" not in intro_classes

            # Settings: anchor_id
            anchor_id = value["settings"]["anchor_id"]
            if anchor_id:
                assert intro_el.get("id") == anchor_id
            else:
                assert not intro_el.get("id")

            # Media
            media = value.get("media")
            if media:
                media_block = media[0]
                media_el = intro_el.find("div", class_="fl-intro-media")
                assert media_el
                if media_block["type"] == "image":
                    assert_image_variants_attributes(
                        images_element=media_el,
                        images_value=media_block["value"],
                        sizes="(min-width: 1200px) 934px, (min-width: 600px) 50vw, 100vw",
                        widths="width-{200,400,600,800,1000,1200,1400,1600,1800,2000}",
                    )
                elif media_block["type"] == "video":
                    assert_video_attributes(intro_el.find("div", class_="fl-video"), media_block)
                elif media_block["type"] == "animation":
                    assert_animation_attributes(intro_el.find("div", class_="fl-video"), media_block)
                elif media_block["type"] == "qr_code":
                    qr_div = media_el.find("div", class_="fl-media-qr-code")
                    assert qr_div
                    assert qr_div.find("div", class_="fl-qr-code").find("svg")
                    if media_block["value"].get("background"):
                        assert qr_div.find("img")
            else:
                assert not intro_el.find("div", class_="fl-intro-media")


def test_sticker_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_sticker_card_2026_variants()
    page = get_sticker_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_name, region in [("upper", upper), ("lower", lower)]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        # First section has 3 cards, second has 4
        assert len(sections[0].find_all("article", class_="fl-sticker-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-sticker-card")) == 4

        # Verify card content in the 4-card section (second section, block_level=2, cards get h3)
        cards = sections[1].find_all("article", class_="fl-sticker-card")
        for i, variant in enumerate(variants):
            card_el = cards[i]
            headline_text = BeautifulSoup(variant["value"]["headline"], "html.parser").get_text()
            heading = card_el.find("h3", class_="fl-heading")
            assert heading and headline_text in heading.get_text()

            if variant["value"]["settings"].get("expand_link"):
                assert "fl-card-expand-link" in card_el.get("class", [])

            # Content body
            content_text = BeautifulSoup(variant["value"]["content"], "html.parser").get_text()
            body = card_el.find(class_="fl-body")
            assert body and content_text in body.get_text()

            # Superheading (optional)
            if variant["value"].get("superheading"):
                superheading_text = BeautifulSoup(variant["value"]["superheading"], "html.parser").get_text()
                superheading_el = card_el.find(class_="fl-superheading")
                assert superheading_el and superheading_text in superheading_el.get_text()

            # Image variants
            sticker_el = card_el.find("div", class_="fl-card-sticker")
            assert_image_variants_attributes(
                images_element=sticker_el,
                images_value=variant["value"]["image"],
                widths="width-400",
            )

            # Buttons
            for button_data in variant["value"]["buttons"]:
                if button_data["type"] == "button":
                    button_el = card_el.find("a", class_="fl-button")
                    cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-2-section.item-1-cards_list.card-{i + 1}.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_illustration_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_illustration_card_2026_variants()
    page = get_illustration_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_name, region in [("upper", upper), ("lower", lower)]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        assert len(sections[0].find_all("article", class_="fl-illustration-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-illustration-card")) == 4

        # Second section (block_level=2), section children get block_level=3 → cards h3
        cards = sections[1].find_all("article", class_="fl-illustration-card")
        for i, variant in enumerate(variants):
            card_el = cards[i]
            headline_text = BeautifulSoup(variant["value"]["headline"], "html.parser").get_text()
            heading = card_el.find("h3", class_="fl-heading")
            assert heading and headline_text in heading.get_text()

            if variant["value"]["settings"].get("expand_link"):
                assert "fl-card-expand-link" in card_el.get("class", [])

            # Content body
            content_text = BeautifulSoup(variant["value"]["content"], "html.parser").get_text()
            body = card_el.find(class_="fl-body")
            assert body and content_text in body.get_text()

            # Eyebrow (optional)
            if variant["value"].get("eyebrow"):
                eyebrow_text = BeautifulSoup(variant["value"]["eyebrow"], "html.parser").get_text()
                eyebrow_el = card_el.find(class_="fl-superheading")
                assert eyebrow_el and eyebrow_text in eyebrow_el.get_text()

            # Media (first item)
            media_el = card_el.find("div", class_="fl-card-media")
            media_value = variant["value"]["media"][0]
            if media_value["type"] == "image":
                assert_image_variants_attributes(
                    images_element=media_el,
                    images_value=media_value["value"],
                )
            elif media_value["type"] == "video":
                video_div = media_el.find("div", class_="fl-video")
                assert_video_attributes(video_div, media_value)
            elif media_value["type"] == "animation":
                animation_div = media_el.find("div", class_="fl-video")
                assert_animation_attributes(animation_div, media_value)

            # Buttons
            for button_data in variant["value"]["buttons"]:
                if button_data["type"] == "button":
                    button_el = card_el.find("a", class_="fl-button")
                    cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-2-section.item-1-cards_list.card-{i + 1}.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_step_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_step_card_2026_variants()
    page = get_step_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_name, region in [("upper", upper), ("lower", lower)]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        assert len(sections[0].find_all("article", class_="fl-step-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-step-card")) == 4

        # Second section (block_level=2), section children get block_level=3 → cards h3
        cards = sections[1].find_all("article", class_="fl-step-card")
        for i, variant in enumerate(variants):
            card_el = cards[i]
            headline_text = BeautifulSoup(variant["value"]["headline"], "html.parser").get_text()
            heading = card_el.find("h3", class_="fl-heading")
            assert heading and headline_text in heading.get_text()

            # Step index is rendered as a span
            step_index = card_el.find("span", class_="fl-step-card-index")
            assert step_index and str(i + 1) in step_index.get_text()

            if variant["value"]["settings"].get("expand_link"):
                assert "fl-card-expand-link" in card_el.get("class", [])

            # Content body (optional)
            if variant["value"].get("content"):
                content_text = BeautifulSoup(variant["value"]["content"], "html.parser").get_text()
                body = card_el.find(class_="fl-body")
                assert body and content_text in body.get_text()

            # Eyebrow (optional)
            if variant["value"].get("eyebrow"):
                eyebrow_text = BeautifulSoup(variant["value"]["eyebrow"], "html.parser").get_text()
                eyebrow_el = card_el.find(class_="fl-superheading")
                assert eyebrow_el and eyebrow_text in eyebrow_el.get_text()

            # Image variants
            media_el = card_el.find("div", class_="fl-card-media")
            assert_image_variants_attributes(
                images_element=media_el,
                images_value=variant["value"]["image"],
            )

            # Buttons
            for button_data in variant["value"]["buttons"]:
                if button_data["type"] == "button":
                    button_el = card_el.find("a", class_="fl-button")
                    cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-2-section.item-1-step_cards.card-{i + 1}.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_outlined_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_outlined_card_2026_variants()
    page = get_outlined_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_name, region in [("upper", upper), ("lower", lower)]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        # First section has 3 cards, second has 4
        assert len(sections[0].find_all("article", class_="fl-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-card")) == 4

        # Verify card content in the 4-card section (second section, block_level=2, cards get h3)
        cards = sections[1].find_all("article", class_="fl-card")
        for i, variant in enumerate(variants):
            card_el = cards[i]
            value = variant["value"]

            # Headline
            headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
            heading = card_el.find("h3", class_="fl-heading")
            assert heading and headline_text in heading.get_text()

            # Expand link
            if value["settings"].get("expand_link"):
                assert "fl-card-expand-link" in card_el.get("class", [])
            else:
                assert "fl-card-expand-link" not in card_el.get("class", [])

            # Content body
            content_text = BeautifulSoup(value["content"], "html.parser").get_text()
            body = card_el.find(class_="fl-body")
            assert body and content_text in body.get_text()

            # Sticker (optional - present when sticker has a non-null image)
            if value.get("sticker", {}).get("image"):
                sticker_el = card_el.find("div", class_="fl-card-sticker")
                assert sticker_el
                assert_image_variants_attributes(
                    images_element=sticker_el,
                    images_value=value["sticker"],
                )

            # Buttons
            for button_data in value["buttons"]:
                if button_data["type"] == "button":
                    button_el = card_el.find("a", class_="fl-button")
                    cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-2-section.item-1-cards_list.card-{i + 1}.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_icon_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_icon_card_2026_variants()
    page = get_icon_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, (region_name, region) in enumerate([("upper", upper), ("lower", lower)]):
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        # First section has 3 cards, second has 4
        assert len(sections[0].find_all("article", class_="fl-illustration-icon-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-illustration-icon-card")) == 4

        for section_index, section in enumerate(sections):
            section_variants = variants[:3] if section_index == 0 else variants
            cards = section.find_all("article", class_="fl-illustration-icon-card")
            # Upper first section: block_level=1, children h2; all other sections: children h3
            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            for i, variant in enumerate(section_variants):
                card_el = cards[i]
                value = variant["value"]

                # Headline
                headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
                heading = card_el.find(heading_tag, class_="fl-heading")
                assert heading and headline_text in heading.get_text()

                # Expand link
                if value["settings"].get("expand_link"):
                    assert "fl-card-expand-link" in card_el.get("class", [])
                else:
                    assert "fl-card-expand-link" not in card_el.get("class", [])

                # Content body
                content_text = BeautifulSoup(value["content"], "html.parser").get_text()
                body = card_el.find(class_="fl-body")
                assert body and content_text in body.get_text()

                # Icon
                icon_el = card_el.find("span", class_="fl-icon")
                assert icon_el and f"fl-icon-{value['icon']}" in icon_el.get("class", [])

                # Buttons
                for button_data in value["buttons"]:
                    if button_data["type"] == "button":
                        button_el = card_el.find("a", class_="fl-button")
                        cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                        cta_position = f"{region_name}-block-{section_index + 1}-section.item-1-cards_list.card-{i + 1}.button-1"
                        assert_button_attributes(
                            button_element=button_el,
                            button_data=button_data,
                            context=context,
                            cta_position=cta_position,
                            cta_text=cta_text,
                        )


def test_testimonial_cards_2026_block(index_page, placeholder_images, rf):
    variants = get_testimonial_card_2026_variants()
    page = get_testimonial_cards_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region in [upper, lower]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        assert len(sections[0].find_all("article", class_="fl-testimonial-card")) == 3
        assert len(sections[1].find_all("article", class_="fl-testimonial-card")) == 4

        cards = sections[1].find_all("article", class_="fl-testimonial-card")
        for i, variant in enumerate(variants):
            card_el = cards[i]
            value = variant["value"]

            # Quote content
            content_text = BeautifulSoup(value["content"], "html.parser").get_text()
            quote_el = card_el.find("blockquote", class_="fl-testimonial-card-quote")
            assert quote_el and content_text in quote_el.get_text()

            # Attribution (always present)
            attribution_text = BeautifulSoup(value["attribution"], "html.parser").get_text()
            cite_el = card_el.find("cite", class_="fl-testimonial-card-attribution")
            assert cite_el and attribution_text in cite_el.get_text()

            # Attribution role (optional)
            if value.get("attribution_role"):
                role_text = BeautifulSoup(value["attribution_role"], "html.parser").get_text()
                role_el = card_el.find("span", class_="fl-testimonial-card-role")
                assert role_el and role_text in role_el.get_text()
            else:
                assert not card_el.find("span", class_="fl-testimonial-card-role")

            # Attribution image (optional)
            image_container = card_el.find("div", class_="fl-testimonial-card-image")
            if value["attribution_image"]["image"]:
                assert image_container and image_container.find("img")
            else:
                assert not image_container


def test_line_cards_block(index_page, placeholder_images, rf):
    card_variants = get_line_card_variants()
    page = get_line_cards_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    # block-1: section containing line_cards (2 cards), block-2: standalone line_cards (4 cards)
    # Upper: section at block_level=1 (children h2), standalone at block_level=2 (h2)
    # Lower: section at block_level=2 (children h3), standalone at block_level=2 (h2)
    for region_name, region, in_section_heading_tag in [("upper", upper, "h2"), ("lower", lower, "h3")]:
        blocks_under_test = [
            {
                "variants": card_variants[:2],
                "cta_position_prefix": f"{region_name}-block-1-section.item-1-line_cards",
                "heading_tag": in_section_heading_tag,
            },
            {
                "variants": card_variants,
                "cta_position_prefix": f"{region_name}-block-2-line_cards",
                "heading_tag": "h2",
            },
        ]

        article_lists = region.find_all("div", class_="fl-stacked-article-list")
        assert len(article_lists) == 2
        assert len(article_lists[0].find_all("article", class_="fl-article-item")) == 2
        assert len(article_lists[1].find_all("article", class_="fl-article-item")) == 4

        for list_index, block_info in enumerate(blocks_under_test):
            cards = article_lists[list_index].find_all("article", class_="fl-article-item")
            position_prefix = block_info["cta_position_prefix"]

            for i, variant in enumerate(block_info["variants"]):
                card_el = cards[i]
                value = variant["value"]

                # Headline
                headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
                heading = card_el.find(block_info["heading_tag"], class_="fl-heading")
                assert heading and headline_text in heading.get_text()

                # Superheading (optional)
                if value.get("superheading"):
                    superheading_text = BeautifulSoup(value["superheading"], "html.parser").get_text()
                    superheading_el = card_el.find(class_="fl-superheading")
                    assert superheading_el and superheading_text in superheading_el.get_text()

                # Content
                content_text = BeautifulSoup(value["content"], "html.parser").get_text()
                assert content_text in card_el.get_text()

                # Buttons
                for button_index, button_data in enumerate(value["buttons"]):
                    if button_data["type"] == "button":
                        button_els = card_el.find_all("a", class_="fl-button")
                        button_el = button_els[button_index]
                        cta_text = f"{headline_text.strip()} - {button_data['value']['label'].strip()}"
                        cta_position = f"{position_prefix}.button-{button_index + 1}"
                        assert_button_attributes(
                            button_element=button_el,
                            button_data=button_data,
                            context=context,
                            cta_position=cta_position,
                            cta_text=cta_text,
                        )


def test_icon_list_with_image_block(index_page, placeholder_images, rf):
    variants = get_icon_list_with_image_variants()
    page = get_icon_list_with_image_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region in [upper, lower]:
        sections = region.find_all("section", class_="fl-section")
        assert len(sections) == 2

        for section_el, variant in zip(sections, variants):
            mediacontent = section_el.find("div", class_="fl-mediacontent")
            assert mediacontent, "Icon list with image should render fl-mediacontent"
            assert "is-narrow" in mediacontent.get("class", [])

            icon_list = section_el.find("ul", class_="icon-text-list")
            assert icon_list

            list_items = icon_list.find_all("li")
            expected_items = variant["value"]["list_items"]
            assert len(list_items) == len(expected_items)

            for li, item in zip(list_items, expected_items):
                expected_text = BeautifulSoup(item["value"]["text"], "html.parser").get_text()
                assert expected_text in li.get_text()
                icon_wrap = li.find("span", class_="fl-icon-wrap")
                assert icon_wrap


def test_showcase_2026_block(index_page, placeholder_images, rf):
    variants = get_showcase_2026_variants()
    page = get_showcase_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, region in enumerate([upper, lower]):
        showcase_sections = region.find_all("section", class_="fl-showcase")
        assert len(showcase_sections) == len(variants)

        for showcase_index, (showcase_el, variant) in enumerate(zip(showcase_sections, variants)):
            layout = variant["value"]["settings"]["layout"]
            assert f"fl-showcase-{layout}" in showcase_el.get("class", [])

            headline_text = BeautifulSoup(variant["value"]["headline"], "html.parser").get_text()
            # First showcase in upper region gets h1, all others get h2
            heading_tag = "h1" if (region_index == 0 and showcase_index == 0) else "h2"
            heading = showcase_el.find(heading_tag, class_="fl-heading")
            assert heading and headline_text in heading.get_text()

            figure = showcase_el.find("figure", class_="fl-showcase-image")
            assert figure

            # Image variants — sizes depend on layout
            layout_sizes = {
                "default": "(min-width: 1200px) 750px, 100vw",
                "expanded": "(min-width: 1200px) 950px, 100vw",
                "full": "(min-width: 1400px) 1400px, 100vw",
            }
            image_media = variant["value"]["media"][0]
            assert_image_variants_attributes(
                images_element=figure,
                images_value=image_media["value"],
                sizes=layout_sizes[layout],
            )

            caption = showcase_el.find("figcaption", class_="fl-showcase-caption")
            assert caption

            if variant["value"].get("caption_title"):
                caption_title_text = BeautifulSoup(variant["value"]["caption_title"], "html.parser").get_text()
                assert caption_title_text in caption.get_text()

            caption_description_text = BeautifulSoup(variant["value"]["caption_description"], "html.parser").get_text()
            assert caption_description_text in caption.get_text()


def test_card_gallery_2026_block(index_page, placeholder_images, rf):
    variants = get_card_gallery_2026_variants()
    page = get_card_gallery_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, (region_name, region) in enumerate([("upper", upper), ("lower", lower)]):
        gallery_sections = region.find_all("section", class_="fl-section")
        assert len(gallery_sections) == len(variants)

        for gallery_index, (gallery_el, variant) in enumerate(zip(gallery_sections, variants)):
            gallery = gallery_el.find("div", class_="fl-card-gallery")
            assert gallery

            # Gallery heading: first gallery in upper region gets h1, all others get h2
            heading_text = BeautifulSoup(variant["value"]["heading"]["heading_text"], "html.parser").get_text()
            heading_tag = "h1" if (region_index == 0 and gallery_index == 0) else "h2"
            gallery_heading = gallery.find(heading_tag, class_="fl-heading")
            assert gallery_heading and heading_text in gallery_heading.get_text()

            # Main card
            main_card = gallery.find("div", class_="fl-card-gallery-main-card")
            assert main_card
            main_headline = BeautifulSoup(variant["value"]["main_card"]["headline"], "html.parser").get_text()
            assert main_headline in main_card.get_text()

            main_icon = variant["value"]["main_card"]["icon"]
            main_icon_span = main_card.find("span", class_="fl-card-gallery-icon")
            assert main_icon_span and main_icon_span.find("span", class_=f"fl-icon-{main_icon}")

            if variant["value"]["main_card"].get("superheading"):
                main_superheading_text = BeautifulSoup(variant["value"]["main_card"]["superheading"], "html.parser").get_text()
                assert main_superheading_text in main_card.get_text()

            main_headline_text = BeautifulSoup(variant["value"]["main_card"]["headline"], "html.parser").get_text()
            for button_data in variant["value"]["main_card"]["buttons"]:
                if button_data["type"] == "button":
                    button_el = main_card.find("a", class_="fl-button")
                    cta_text = f"{main_headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-{gallery_index + 1}-card_gallery.main-card.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )

            main_figure = main_card.find("figure", class_="fl-card-gallery-card-figure")
            assert main_figure
            assert_image_variants_attributes(
                images_element=main_figure,
                images_value=variant["value"]["main_card"]["image"],
                widths="width-{400,600,800,1000,1200}",
                sizes="(min-width: 900px) 70vw, 100vw",
                break_at="md",
            )

            # Secondary card
            secondary_card = gallery.find("div", class_="fl-card-gallery-secondary-card")
            assert secondary_card
            secondary_headline = BeautifulSoup(variant["value"]["secondary_card"]["headline"], "html.parser").get_text()
            assert secondary_headline in secondary_card.get_text()

            secondary_icon = variant["value"]["secondary_card"]["icon"]
            secondary_icon_span = secondary_card.find("span", class_="fl-card-gallery-icon")
            assert secondary_icon_span and secondary_icon_span.find("span", class_=f"fl-icon-{secondary_icon}")

            if variant["value"]["secondary_card"].get("superheading"):
                secondary_superheading_text = BeautifulSoup(variant["value"]["secondary_card"]["superheading"], "html.parser").get_text()
                assert secondary_superheading_text in secondary_card.get_text()

            secondary_headline_text = BeautifulSoup(variant["value"]["secondary_card"]["headline"], "html.parser").get_text()
            for button_data in variant["value"]["secondary_card"]["buttons"]:
                if button_data["type"] == "button":
                    button_el = secondary_card.find("a", class_="fl-button")
                    cta_text = f"{secondary_headline_text.strip()} - {button_data['value']['label'].strip()}"
                    cta_position = f"{region_name}-block-{gallery_index + 1}-card_gallery.secondary-card.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )

            secondary_figure = secondary_card.find("figure", class_="fl-card-gallery-card-figure")
            assert secondary_figure
            assert_image_variants_attributes(
                images_element=secondary_figure,
                images_value=variant["value"]["secondary_card"]["image"],
                widths="width-{400,600,800,1000}",
                sizes="(min-width: 768px) 40vw, (min-width: 1024px) 30vw, 100vw",
                break_at="md",
            )

            # Callout card
            callout_card = gallery.find("div", class_="fl-card-gallery-callout-card")
            assert callout_card
            callout_headline = BeautifulSoup(variant["value"]["callout_card"]["headline"], "html.parser").get_text()
            assert callout_headline in callout_card.get_text()

            if variant["value"]["callout_card"].get("superheading"):
                callout_superheading_text = BeautifulSoup(variant["value"]["callout_card"]["superheading"], "html.parser").get_text()
                assert callout_superheading_text in callout_card.get_text()

            # CTA button (optional)
            if variant["value"].get("cta"):
                cta_wrap = gallery.find("div", class_="fl-section-cta-wrap")
                assert cta_wrap
                gallery_heading_text = BeautifulSoup(variant["value"]["heading"]["heading_text"], "html.parser").get_text()
                for button_data in variant["value"]["cta"]:
                    if button_data["type"] == "button":
                        button_el = cta_wrap.find("a", class_="fl-button")
                        cta_text = f"{gallery_heading_text.strip()} - {button_data['value']['label'].strip()}"
                        cta_position = f"{region_name}-block-{gallery_index + 1}-card_gallery.cta"
                        assert_button_attributes(
                            button_element=button_el,
                            button_data=button_data,
                            context=context,
                            cta_position=cta_position,
                            cta_text=cta_text,
                        )


# ---------------------------------------------------------------------------
# SpringfieldLinkBlock
# ---------------------------------------------------------------------------


def _springfield_link_data(link_to, **fields):
    """Build a raw data dict for SpringfieldLinkBlock.clean()."""
    data = {
        "link_to": link_to,
        "page": None,
        "file": None,
        "custom_url": "",
        "relative_url": "",
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": False,
    }
    data.update(fields)
    return data


def test_kit_intro_2026_block(index_page, rf):
    variants = get_kit_intro_2026_variants()
    page = get_kit_intro_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    intro_divs = upper.find_all("div", class_="fl-home-intro")
    assert len(intro_divs) == len(variants)

    for index, (intro_el, variant) in enumerate(zip(intro_divs, variants)):
        value = variant["value"]

        heading_text = BeautifulSoup(value["heading"]["heading_text"], "html.parser").get_text()
        # Kit intro is first block in upper (h1)
        heading = intro_el.find("h1", class_="fl-heading")
        assert heading and heading_text in heading.get_text()

        if value["heading"]["superheading_text"]:
            superheading_text = BeautifulSoup(value["heading"]["superheading_text"], "html.parser").get_text()
            superheading = intro_el.find("p", class_="fl-superheading")
            assert superheading and superheading_text in superheading.get_text()

        buttons = value["buttons"]
        button_elements = intro_el.find_all("a", class_="fl-button")
        assert len(button_elements) == len(buttons)
        for button_index, button in enumerate(buttons):
            cta_position = f"upper-block-{index + 1}-kit_intro.button-{button_index + 1}"
            cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
            assert_button_attributes(
                button_element=button_elements[button_index],
                button_data=button,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )

    # The Kit Intro block isn't allowed on the lower section
    assert not lower.find_all("div", class_="fl-home-intro")


def test_carousel_2026_block(index_page, placeholder_images, rf):
    variants = get_carousel_2026_variants()
    page = get_carousel_2026_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region_index, (region_name, region) in enumerate([("upper", upper), ("lower", lower)]):
        carousel_divs = region.find_all("div", class_="fl-carousel")
        assert len(carousel_divs) == len(variants)

        for index, (carousel_el, variant) in enumerate(zip(carousel_divs, variants)):
            value = variant["value"]

            heading_text = BeautifulSoup(value["heading"]["heading_text"], "html.parser").get_text()
            # First carousel in upper region gets h1, all others get h2
            heading_tag = "h1" if (region_index == 0 and index == 0) else "h2"
            heading = carousel_el.find(heading_tag, class_="fl-heading")
            assert heading and heading_text in heading.get_text()

            slides = value["slides"]
            slides_element = carousel_el.find("div", class_="fl-carousel-slides")
            assert slides_element

            control_elements = slides_element.find_all("li", class_="fl-carousel-control-item")
            assert len(control_elements) == len(slides)

            slide_elements = slides_element.find_all("div", class_="fl-carousel-slide")
            assert len(slide_elements) == len(slides)

            for slide_index, slide in enumerate(slides):
                slide_headline = BeautifulSoup(slide["value"]["headline"], "html.parser").get_text()
                assert control_elements[slide_index].get_text().strip() == slide_headline.strip()

                images_element = slide_elements[slide_index].find("div", class_="fl-carousel-image")
                assert images_element and images_element.find("img")

            buttons = value["buttons"]
            button_elements = carousel_el.find_all("a", class_="fl-button")
            assert len(button_elements) == len(buttons)
            for button_index, button in enumerate(buttons):
                cta_position = f"{region_name}-block-{index + 1}-carousel.button-{button_index + 1}"
                cta_text = f"{heading_text.strip()} - {button['value']['label'].strip()}"
                assert_button_attributes(
                    button_element=button_elements[button_index],
                    button_data=button,
                    context=context,
                    cta_position=cta_position,
                    cta_text=cta_text,
                )


def test_sliding_carousel_block(index_page, placeholder_images, rf):
    slides = get_sliding_carousel_slides()
    page = get_sliding_carousel_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region in [upper, lower]:
        carousel_el = region.find("div", class_="fl-sliding-carousel")

        controls = carousel_el.find_all("li", class_="fl-sliding-carousel-control")
        assert len(controls) == len(slides)

        slide_panels = carousel_el.find_all("div", class_="fl-sliding-carousel-slide")
        assert len(slide_panels) == len(slides)

        # First control is active
        assert "is-active" in controls[0].get("class", [])
        assert controls[0].get("aria-current") == "true"
        assert "is-active" not in controls[1].get("class", [])

        # First slide is visible
        assert "is-active" in slide_panels[0].get("class", [])
        assert slide_panels[0].get("aria-hidden") == "false"
        assert "is-active" not in slide_panels[1].get("class", [])
        assert slide_panels[1].get("aria-hidden") == "true"

        for i, slide in enumerate(slides):
            value = slide["value"]
            heading = value["heading"]

            # Superheading visible in control when present
            if heading["superheading_text"]:
                superheading_text = BeautifulSoup(heading["superheading_text"], "html.parser").get_text()
                superheading_el = controls[i].find(class_="fl-sliding-carousel-superheading")
                assert superheading_el and superheading_text in superheading_el.get_text()

            # Heading text present in control
            heading_text = BeautifulSoup(heading["heading_text"], "html.parser").get_text()
            heading_el = controls[i].find(class_="fl-sliding-carousel-heading-text")
            assert heading_el and heading_text in heading_el.get_text()

            # Media rendered in slide panel
            assert slide_panels[i].find("img")


def test_smart_window_explainer_page(index_page, rf):
    intro_fixture = get_smart_window_explainer_intro()
    content_fixture = get_smart_window_explainer_content()
    page = get_smart_window_explainer_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Intro: h1 heading present, no media
    upper = soup.find("div", class_="fl-smart-window-explainer-hero")
    assert upper
    intro_el = upper.find("div", class_="fl-intro")
    assert intro_el
    assert "fl-intro-has-media" not in intro_el.get("class", [])
    intro_h1 = intro_el.find("h1", class_="fl-heading")
    assert intro_h1
    intro_heading = BeautifulSoup(intro_fixture["value"]["heading"]["heading_text"], "html.parser").get_text()
    assert intro_heading in intro_h1.get_text()

    # Lower content: 3 media_content blocks, each with headline (h2) and SmartWindowInstructionsBlock
    lower = soup.find("div", class_="fl-split-page-lower")
    assert lower

    media_content_headings = lower.find_all("h2", class_="fl-heading")
    assert len(media_content_headings) == len(content_fixture) == 3

    instructions_els = lower.find_all("div", class_="fl-smart-window-instructions")
    assert len(instructions_els) == len(content_fixture) == 3

    for i, media_content in enumerate(content_fixture):
        headline_text = BeautifulSoup(media_content["value"]["headline"], "html.parser").get_text()
        assert headline_text in media_content_headings[i].get_text()

        instructions_block = media_content["value"]["content"][1]
        typewriter_text = instructions_block["value"]["typewriter_text"]
        typewriter_el = instructions_els[i].find(class_="fl-typewriter")
        assert typewriter_el
        assert typewriter_text in typewriter_el.get_text()


def test_springfield_link_block_clean_accepts_valid_relative_url():
    """clean() passes for a locale-free path."""
    result = SpringfieldLinkBlock().clean(_springfield_link_data("relative_url", relative_url="/features/"))
    assert result["relative_url"] == "/features/"


@pytest.mark.parametrize(
    "path",
    [
        "/en-US/features/",
        "/fr/features/",
        "/pt-BR/features/",
        "/de/features/",
    ],
)
def test_springfield_link_block_clean_rejects_locale_prefixed_url(path):
    """clean() raises when the relative_url value begins with a locale prefix."""
    with pytest.raises(StreamBlockValidationError) as exc_info:
        SpringfieldLinkBlock().clean(_springfield_link_data("relative_url", relative_url=path))
    assert "relative_url" in exc_info.value.block_errors


def test_springfield_link_block_clean_empty_relative_url_raises():
    """clean() raises when link_to is relative_url but no path is provided."""
    with pytest.raises(StreamBlockValidationError) as exc_info:
        SpringfieldLinkBlock().clean(_springfield_link_data("relative_url", relative_url=""))
    assert "relative_url" in exc_info.value.block_errors


def test_springfield_link_block_clean_rejects_nonexistent_relative_url():
    """clean() raises when the relative_url path does not resolve at all."""
    with pytest.raises(StreamBlockValidationError) as exc_info:
        SpringfieldLinkBlock().clean(_springfield_link_data("relative_url", relative_url="/not/a/valid/path!/"))
    assert "relative_url" in exc_info.value.block_errors
    error = exc_info.value.block_errors["relative_url"]
    assert error.message == "This URL does not match any existing static URL on the site. If linking to a page, select 'Page'"


@pytest.mark.django_db
def test_springfield_link_block_clean_rejects_wagtail_page_url(minimal_site):
    """clean() raises when the relative_url path resolves to Wagtail's catch-all, not a static page."""
    # minimal_site creates a SimpleRichTextPage at /test-page/ (a Wagtail-only URL)
    assert Page.objects.filter(slug="test-page").exists() is True

    with pytest.raises(StreamBlockValidationError) as exc_info:
        SpringfieldLinkBlock().clean(_springfield_link_data("relative_url", relative_url="/test-page/"))
    assert "relative_url" in exc_info.value.block_errors
    error = exc_info.value.block_errors["relative_url"]
    assert error.message == "This URL does not match any existing static URL on the site. If linking to a page, select 'Page'"


def test_springfield_link_block_clean_locale_validation_only_applies_to_relative_url():
    """Locale-prefix validation does not apply to other link types."""
    result = SpringfieldLinkBlock().clean(_springfield_link_data("custom_url", custom_url="/en-US/features/"))
    assert result["custom_url"] == "/en-US/features/"


def _springfield_link_value(link_to, **fields):
    """Build a SpringfieldLinkBlockURLValue via SpringfieldLinkBlock.to_python()."""
    return SpringfieldLinkBlock().to_python(_springfield_link_data(link_to, **fields))


def test_springfield_link_block_relative_url_returns_locale_aware_url(minimal_site):
    """Prepends the active locale to the stored path."""
    link_value = _springfield_link_value("relative_url", relative_url="/features/")

    with mock.patch("django.utils.translation.get_language", return_value="fr"):
        url = link_value.get_url()

    assert url == "/fr/features/"


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_springfield_link_block_relative_url_uses_url_locale_when_alias_has_no_db_record():
    """Returns /{alias_locale}/{path} when the alias locale has no Locale DB record.

    When pt-PT has no Locale DB record,the relative_url must still use the
    URL-facing locale (pt-PT) as the prefix.
    """
    # The fallback locale exists in the DB (pt-BR is a canonical locale).
    LocaleFactory(language_code="pt-BR")
    # The alias locale does not exist.
    assert Locale.objects.filter(language_code="pt-PT").exists() is False

    link_value = _springfield_link_value("relative_url", relative_url="/features/")

    with mock.patch("django.utils.translation.get_language", return_value="pt-PT"):
        url = link_value.get_url()

    assert url == "/pt-PT/features/"


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"es-CL": "es-MX"})
def test_springfield_link_block_relative_url_uses_url_locale_when_alias_and_fallback_have_no_db_record():
    """Returns /{alias_locale}/{path} when neither the alias nor the fallback locale has a DB record.

    When es-CL has no Locale DB record and its fallback (es-MX) also has no Locale
    DB record, the relative_url must still use the URL-facing locale (es-CL).
    """
    # The fallback locale does not exist.
    assert Locale.objects.filter(language_code="es-MX").exists() is False
    # The alias locale does not exist.
    assert Locale.objects.filter(language_code="es-CL").exists() is False

    link_value = _springfield_link_value("relative_url", relative_url="/features/")

    with mock.patch("django.utils.translation.get_language", return_value="es-CL"):
        url = link_value.get_url()

    assert url == "/es-CL/features/"


def test_springfield_link_block_relative_url_falls_back_when_get_active_raises():
    """Falls back to the raw path when SpringfieldLocale.get_active() raises SpringfieldLocale.DoesNotExist."""
    link_value = _springfield_link_value("relative_url", relative_url="/features/")

    with mock.patch(
        "springfield.cms.models.locale.SpringfieldLocale.get_active",
        side_effect=SpringfieldLocale.DoesNotExist,
    ):
        url = link_value.get_url()

    assert url == "/features/"


def test_springfield_link_block_relative_url_empty_returns_empty():
    """Returns an empty string when no path is stored."""
    link_value = _springfield_link_value("relative_url", relative_url="")

    assert link_value.get_url() == ""


@pytest.mark.django_db
def test_springfield_link_block_page_returns_locale_aware_url(tiny_localized_site):
    """Returns the translated page URL when the active locale has a translation."""
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with mock.patch("django.utils.translation.get_language", return_value="fr"):
        url = link_value.get_url()

    fr_page = Page.objects.get(locale__language_code="fr", slug="test-page")
    assert url == fr_page.url


@pytest.mark.django_db
def test_springfield_link_block_page_falls_back_when_get_active_raises(tiny_localized_site):
    """Falls back to the page's own URL when SpringfieldLocale.get_active() raises SpringfieldLocale.DoesNotExist."""
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with mock.patch(
        "springfield.cms.models.locale.SpringfieldLocale.get_active",
        side_effect=SpringfieldLocale.DoesNotExist,
    ):
        url = link_value.get_url()

    assert url == en_us_page.url


@pytest.mark.django_db
def test_springfield_link_block_page_falls_back_to_locale_prefix_when_get_translation_raises(tiny_localized_site):
    """Falls back to /{active_lang}/{path} when page.get_translation() raises Page.DoesNotExist."""
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with (
        mock.patch("django.utils.translation.get_language", return_value="fr"),
        mock.patch.object(en_us_page.__class__, "get_translation", side_effect=Page.DoesNotExist),
    ):
        url = link_value.get_url()

    assert url == "/fr/test-page/"


@pytest.mark.django_db
@override_settings(LANGUAGE_CODE="en")
def test_springfield_link_block_page_falls_back_when_no_translation_exists(tiny_localized_site):
    """Falls back to the page's own URL when no locale can be resolved for the active language.

    "zz-ZZ" has no Locale record. LANGUAGE_CODE is set to "en" (valid Django language,
    but no Wagtail Locale record), so get_url() returns the page.url unchanged.
    """
    # fr_grandchild exists only in fr — it has no counterpart in any other locale
    fr_grandchild = Page.objects.get(locale__language_code="fr", slug="grandchild-page")
    assert Page.objects.filter(locale__language_code="zz-ZZ", slug="grandchild-page").exists() is False

    link_value = _springfield_link_value("page", page=fr_grandchild.pk)

    with mock.patch("django.utils.translation.get_language", return_value="zz-ZZ"):
        url = link_value.get_url()

    assert url == fr_grandchild.url


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_springfield_link_block_page_constructs_alias_locale_url(tiny_localized_site):
    """
    Constructs /{alias_locale}/{path} when the active locale has a Locale record but no page tree.

    The goal here is to match the user's requested URL, so if the user requests
    /es-AR/somepage, but somepage does not exist, so the user is given the content
    from es-MX's somepage (es-MX is the fallback locale for es-AR), we want the
    page links in the content to point to the es-AR pages (not the es-MX pages).

    When the alias locale (es-AR) has a Locale DB record but no translated page, get_url()
    uses the active locale's language_code to prefix the canonical page's path, rather than
    returning the canonical page's own URL.
    """
    # Create an es-AR Locale record so SpringfieldLocale.get_active() resolves it.
    LocaleFactory(language_code="es-AR")
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    # Verify: no es-AR translation of this page exists.
    assert not Page.objects.filter(locale__language_code="es-AR", slug="test-page").exists()

    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with mock.patch("django.utils.translation.get_language", return_value="es-AR"):
        url = link_value.get_url()

    # Even though the test-page does not exist in the es-AR locale, the URL is
    # returned using the alias (es-AR) locale prefix.
    assert url == "/es-AR/test-page/"


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_springfield_link_block_page_constructs_alias_locale_url_without_locale_db_record(tiny_localized_site):
    """
    Returns /{alias_locale}/{path} when the alias locale has NO Locale DB record.

    When pt-PT has no Locale DB record, the page link should still use the URL-facing
    locale (pt-PT) as the URL prefix.
    """
    assert not Page.objects.filter(locale__language_code="pt-PT").exists()
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")

    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with mock.patch("django.utils.translation.get_language", return_value="pt-PT"):
        url = link_value.get_url()

    # The URL should use the pt-PT locale prefix.
    assert url == "/pt-PT/test-page/"


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"es-CL": "es-MX"})
def test_springfield_link_block_page_constructs_alias_locale_url_without_alias_or_fallback_locale_db_record(tiny_localized_site):
    """
    Returns /{alias_locale}/{path} when neither the alias nor the fallback
    locale has a Locale DB record.

    When es-CL has no Locale DB record and es-MX (its fallback) also has no
    Locale DB record, the page link should still use the URL-facing locale (es-CL)
    as the URL prefix.
    """
    assert not Page.objects.filter(locale__language_code="es-CL").exists()
    assert not Page.objects.filter(locale__language_code="es-MX").exists()
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")

    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with mock.patch("django.utils.translation.get_language", return_value="es-CL"):
        url = link_value.get_url()

    # The URL should use the es-CL locale prefix.
    assert url == "/es-CL/test-page/"


@pytest.mark.django_db
@override_settings(FALLBACK_LOCALES={"es-AR": "es-MX"})
def test_springfield_link_block_page_handles_absolute_page_url(tiny_localized_site):
    """
    When page.url returns an absolute URL (e.g. http://localhost:8000/en-US/test-page/),
    get_url() must still produce a correct relative path with the alias locale prefix,
    not a malformed URL like /es-AR/localhost:8000/en-US/test-page/.
    """
    LocaleFactory(language_code="es-AR")
    en_us_page = Page.objects.get(locale__language_code="en-US", slug="test-page")
    assert not Page.objects.filter(locale__language_code="es-AR", slug="test-page").exists()

    link_value = _springfield_link_value("page", page=en_us_page.pk)

    with (
        mock.patch("django.utils.translation.get_language", return_value="es-AR"),
        mock.patch.object(
            type(en_us_page),
            "url",
            new_callable=lambda: property(lambda self: "http://localhost:8000/en-US/test-page/"),
        ),
    ):
        url = link_value.get_url()

    assert url == "/es-AR/test-page/"


def test_springfield_link_block_page_none_returns_none():
    """Returns None when no page is stored."""
    link_value = _springfield_link_value("page", page=None)

    assert link_value.get_url() is None


def test_notification_block(index_page, rf):
    variants = get_notification_variants()
    page = get_notification_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region in [upper, lower]:
        notification_divs = region.find_all("div", class_="fl-notification")
        assert len(notification_divs) == len(variants)

        for index, notification in enumerate(variants):
            div = notification_divs[index]
            message = BeautifulSoup(notification["value"]["message"], "html.parser").get_text()
            settings = notification["value"]["settings"]
            color = settings.get("color")
            icon = settings.get("icon")
            closable = settings.get("closable")
            stacked = settings.get("stacked")

            assert message in div.get_text()
            if color:
                assert f"fl-notification-{color}" in div["class"]
            if icon:
                icon_el = div.find("span", class_="fl-icon")
                assert icon_el and f"fl-icon-{icon}" in icon_el["class"]
            if stacked:
                assert "fl-notification-stacked" in div["class"]
                # stacked disables closable per the component template
                assert not div.find("button", class_="fl-notification-close")
            elif closable:
                assert div.find("button", class_="fl-notification-close")

            headline_raw = notification["value"].get("headline", "")
            heading_el = div.find("p", class_="fl-notification-heading")
            assert heading_el
            if headline_raw:
                headline_text = BeautifulSoup(headline_raw, "html.parser").get_text()
                assert headline_text in heading_el.get_text()
                assert message in div.get_text()
            else:
                assert message in heading_el.get_text()


def test_uuid_block_is_not_translatable():
    """UUIDBlock stores analytics IDs, not user-facing content — it must not be sent to translators."""
    from springfield.cms.blocks import UUIDBlock

    assert UUIDBlock().get_translatable_segments("cfdf0d2c-7eee-49c2-8747-80450e22dbdd") == []


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_base_article_value_get_article_returns_fallback_translation_via_multi_target_page_chooser():
    """
    get_article() must return the fallback locale's translation even when the
    article chooser returns a base Page instance (not the specific type).

    ArticleBlock uses target_model=("cms.ArticleDetailPage", "cms.ArticleThemePage").
    Wagtail returns a base Page instance for multi-target choosers, so
    self["article"].localized calls Page.localized (Wagtail's implementation),
    which does not know about our AbstractSpringfieldCMSPage.localized override.
    The fix is self["article"].specific.localized, which routes through our override.

    This test reproduces the production bug: without .specific, get_article()
    returns the en-US source page for pt-PT requests even when a pt-BR
    translation exists.
    """

    pt_br_locale = LocaleFactory(language_code="pt-BR")
    _pt_pt_locale = LocaleFactory(language_code="pt-PT")

    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    root_page.copy_for_translation(pt_br_locale)

    en_us_article = ArticleDetailPageFactory(
        title="en-US Article",
        slug="en-us-article-chooser-test",
        parent=root_page,
    )
    pt_br_article = en_us_article.copy_for_translation(pt_br_locale)
    pt_br_article.title = "pt-BR Article"
    pt_br_article.save_revision().publish()

    # Simulate what Wagtail's multi-target PageChooserBlock returns: a base Page
    # instance, not ArticleDetailPage. This is the root cause of the production bug.
    article_as_base_page = Page.objects.get(pk=en_us_article.pk)
    assert type(article_as_base_page) is Page, "Precondition: must be base Page, not specific subclass"

    article_value = BaseArticleValue(
        ArticleBlock(),
        {"article": article_as_base_page, "overrides": {}},
    )

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        result = article_value.get_article()

    assert result.id == pt_br_article.id
    assert result.locale == pt_br_locale


@override_settings(FALLBACK_LOCALES={"pt-PT": "pt-BR"})
def test_base_article_value_get_link_url_returns_url_with_current_locale():
    """
    get_link_url() must return a URL with the current active locale, not the fallback article's locale.

    If the user is browsing in pt-PT, and clicks a link to an article that only exists in pt-BR,
    they should see the URL change to /pt-PT/article-slug/, not /pt-BR/article-slug/.
    """
    pt_br_locale = LocaleFactory(language_code="pt-BR")
    _pt_pt_locale = LocaleFactory(language_code="pt-PT")

    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    root_page.copy_for_translation(pt_br_locale)

    en_us_article = ArticleDetailPageFactory(
        title="en-US Article",
        slug="article-url-locale-test",
        parent=root_page,
    )
    pt_br_article = en_us_article.copy_for_translation(pt_br_locale)
    pt_br_article.title = "pt-BR Article"
    pt_br_article.save_revision().publish()

    article_value = BaseArticleValue(
        ArticleBlock(),
        {"article": en_us_article, "overrides": {}},
    )

    with mock.patch("django.utils.translation.get_language", return_value="pt-pt"):
        url = article_value.get_link_url()

    assert url == "/pt-PT/article-url-locale-test/"
