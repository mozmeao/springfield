# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from unittest import mock
from urllib.parse import parse_qs, urlparse, urlunparse

from django.conf import settings
from django.template.loader import render_to_string
from django.test import override_settings
from django.utils import translation
from django.utils.formats import date_format

import pytest
from bs4 import BeautifulSoup
from wagtail.blocks import CharBlock, StreamBlockValidationError, StructBlockValidationError
from wagtail.documents.models import Document
from wagtail.images.jinja2tags import image, srcset_image
from wagtail.models import Locale, Page, Site

from lib.l10n_utils import fluent_l10n, get_locale
from springfield.cms.blocks import (
    ROADMAP_STATUS_LABELS,
    ROADMAP_TAG_ICONS,
    ROADMAP_TAG_LABELS,
    UI_TOUR_CLASSES,
    UITOUR_BUTTON_NEW_TAB,
    ArticleBlock,
    BaseArticleValue,
    ButtonBlock,
    ButtonRowBlock,
    FirefoxFocusButtonBlock,
    FXAccountButtonBlock,
    QRCodeModalButtonBlock,
    SectionBlock,
    SetAsDefaultButtonBlock,
    SpringfieldLinkBlock,
    TwoColumnCardBlock,
    UITourButtonBlock,
    UntranslatableCharBlock,
    UUIDBlock,
)
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
from springfield.cms.fixtures.banner_fixtures import get_banner_test_page, get_banner_variants
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_blocks, get_button_variants, get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import get_card_sections, get_card_test_page, get_card_variants
from springfield.cms.fixtures.card_gallery_fixtures import get_card_gallery_test_page, get_card_gallery_variants
from springfield.cms.fixtures.cards_fixtures import (
    get_illustration_cards_sections,
    get_illustration_cards_test_page,
    get_outlined_cards_sections,
    get_outlined_cards_test_page,
    get_step_card_variants,
    get_step_cards_test_page,
    get_sticker_cards_sections,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.carousel_fixtures import get_carousel_test_page, get_carousel_variants
from springfield.cms.fixtures.featured_image_section_fixtures import (
    get_featured_image_section_test_page,
    get_featured_image_section_variants,
)
from springfield.cms.fixtures.freeformpage import (
    get_freeform_page_test_page,
    get_mobile_store_qr_code,
    get_mobile_store_qr_code_test_page,
)
from springfield.cms.fixtures.homepage_fixtures import (
    get_cards_list,
    get_home_carousel,
    get_home_intro,
    get_home_test_page,
    get_kit_banner,
)
from springfield.cms.fixtures.icon_cards_fixtures import (
    get_icon_card_variants,
    get_icon_cards_sections,
    get_icon_cards_test_page,
)
from springfield.cms.fixtures.icon_list_with_image_fixtures import (
    get_icon_list_with_image_test_page,
    get_icon_list_with_image_variants,
)
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page, get_intro_variants
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page, get_kit_banner_variants
from springfield.cms.fixtures.kit_intro_fixtures import get_kit_intro_test_page, get_kit_intro_variants
from springfield.cms.fixtures.line_cards_fixtures import (
    get_line_card_variants,
    get_line_cards_test_page,
)
from springfield.cms.fixtures.media_content_fixtures import (
    get_media_content_narrow_variants,
    get_media_content_sections,
    get_media_content_test_page,
    get_media_content_variants,
)
from springfield.cms.fixtures.notification_fixtures import get_notification_test_page, get_notification_variants
from springfield.cms.fixtures.roadmap_list_fixtures import (
    get_roadmap_list_section_variants,
    get_roadmap_list_test_page,
    get_roadmap_page_intro,
)
from springfield.cms.fixtures.showcase_fixtures import get_showcase_test_page, get_showcase_variants
from springfield.cms.fixtures.sliding_carousel_fixtures import (
    get_sliding_carousel_slides,
    get_sliding_carousel_test_page,
)
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import (
    get_smart_window_explainer_content,
    get_smart_window_explainer_intro,
    get_smart_window_explainer_test_page,
)
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_snippet, get_set_as_default_snippet
from springfield.cms.fixtures.testimonial_card_fixtures import (
    get_testimonial_cards_sections,
    get_testimonial_cards_test_page,
)
from springfield.cms.fixtures.topic_list_fixtures import get_topic_list_lower_variants, get_topic_list_test_page, get_topic_list_upper_variants
from springfield.cms.fixtures.two_column_cards_fixtures import get_two_column_cards_test_page, get_two_column_cards_variants
from springfield.cms.models import ArticleDetailPage, PretranslatedPhrase, SpringfieldImage
from springfield.cms.models.locale import SpringfieldLocale
from springfield.cms.templatetags.cms_tags import add_utm_parameters
from springfield.cms.tests.factories import ArticleDetailPageFactory, LocaleFactory
from springfield.firefox.firefox_details import firefox_desktop
from springfield.firefox.templatetags.misc import app_store_url, fxa_button, play_store_url

pytestmark = [
    pytest.mark.django_db,
]

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_BTN_SETTINGS = {
    "theme": "",
    "icon": "",
    "icon_position": "right",
    "analytics_id": "00000000-0000-0000-0000-000000000001",
}

_BTN_LINK = {
    "link_to": "custom_url",
    "page": None,
    "file": None,
    "custom_url": "https://mozilla.org",
    "anchor": "",
    "email": "",
    "phone": "",
    "new_window": False,
    "relative_url": "",
}

# The non-download button blocks
_BUTTON_BLOCK_TYPES_NOT_DOWNLOAD = ["button", "uitour_button", "fxa_button", "set_as_default_button", "focus_button", "qr_code_modal_button"]


def _button_block_and_value(btn_type, *, custom_label=None, pretranslated_label=None, snippet_pk=None):
    """Return (block_instance, raw_value_dict) for a given button type."""
    value = {"settings": dict(_BTN_SETTINGS)}
    if custom_label is not None:
        value["custom_label"] = custom_label
    if pretranslated_label is not None:
        value["pretranslated_label"] = pretranslated_label

    if btn_type == "button":
        block = ButtonBlock()
        value["link"] = dict(_BTN_LINK)
    elif btn_type == "uitour_button":
        block = UITourButtonBlock()
        value["button_type"] = UITOUR_BUTTON_NEW_TAB
    elif btn_type == "fxa_button":
        block = FXAccountButtonBlock()
    elif btn_type == "set_as_default_button":
        block = SetAsDefaultButtonBlock()
        value["snippet"] = snippet_pk
    elif btn_type == "focus_button":
        block = FirefoxFocusButtonBlock()
        value["store"] = "android"
    elif btn_type == "qr_code_modal_button":
        block = QRCodeModalButtonBlock()
        value["url"] = "https://www.mozilla.org/firefox/mobile/"
        value["heading"] = "Get Firefox on your phone"
        value["content"] = "Take Firefox with you."
    else:  # pragma: no cover
        raise ValueError(btn_type)
    return block, value


def _render_context(request):
    """
    Minimal parent context a button block needs to render in isolation.

    `fluent_l10n` is normally injected by the page/snippet context (see
    `springfield.cms.pattern_contexts`); we supply it here so set_as_default
    (whose snippet uses Fluent) renders without a context KeyError.
    """
    return {
        "block_text": "Heading",
        "block_position": "1",
        "request": request,
        "fluent_l10n": fluent_l10n(["en"], settings.FLUENT_DEFAULT_FILES),
    }


def _render_button(btn_type, request, **label_kwargs):
    snippet_pk = get_set_as_default_snippet().id if btn_type == "set_as_default_button" else None
    block, raw = _button_block_and_value(btn_type, snippet_pk=snippet_pk, **label_kwargs)
    bound = block.to_python(raw)
    return block.render(bound, context=_render_context(request))


def _fxa_utm_campaign(html):
    """
    Return the ``utm_campaign`` query-param value from a rendered FXA button.
    """
    a = BeautifulSoup(html, "html.parser").find("a")
    return parse_qs(urlparse(a["href"]).query).get("utm_campaign", [None])[0]


def _get_cta_text(html):
    """Return the data-cta-text attribute from a rendered button (any element type)."""
    el = BeautifulSoup(html, "html.parser").find(attrs={"data-cta-text": True})
    return el["data-cta-text"] if el else None


def resolve_button_label(button_data: dict) -> str:
    """
    Resolve the rendered label for a non-download LabelSourceMixin button.

    Return either the pretranslated_label (snippet FK) or the custom_label.
    """
    value = button_data["value"]
    snippet_id = value.get("pretranslated_label")
    if snippet_id:
        snippet = PretranslatedPhrase.objects.filter(pk=snippet_id).first()
        if snippet:
            return snippet.label
    return value.get("custom_label", "") or ""


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
    label = resolve_button_label(button_data)
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


def resolve_download_button_label(button_data: dict) -> str:
    """Resolve the rendered button label from pretranslated_label (snippet) or custom_label."""
    value = button_data["value"]
    snippet_id = value.get("pretranslated_label")
    if snippet_id:
        snippet = PretranslatedPhrase.objects.filter(pk=snippet_id).first()
        if snippet:
            return snippet.label
    return value.get("custom_label", "")


def assert_download_button_attributes(
    button_element: BeautifulSoup, button_data: dict, context: dict, cta_position: str | None = None, cta_text: str | None = None
):
    label = resolve_download_button_label(button_data)
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
        cta_text = f"{headline_text.strip()} - {buttons[0]['value']['custom_label'].strip()}"

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


def assert_heading_block(element: BeautifulSoup, heading_data: dict, heading_tag: str = "h2"):
    heading_text = BeautifulSoup(heading_data["heading_text"], "html.parser").get_text().strip()
    superheading_text = BeautifulSoup(heading_data.get("superheading_text", ""), "html.parser").get_text().strip()
    subheading_text = BeautifulSoup(heading_data.get("subheading_text", ""), "html.parser").get_text().strip()

    heading_el = element.find(heading_tag, class_="fl-heading")
    assert heading_el and heading_text in heading_el.get_text()

    if superheading_text:
        superheading_el = element.find("p", class_="fl-superheading")
        assert superheading_el and superheading_text in superheading_el.get_text()

    if subheading_text:
        subheading_el = element.find("p", class_="fl-subheading")
        assert subheading_el and subheading_text in subheading_el.get_text()


def assert_pricing_heading_block(element: BeautifulSoup, block_data: dict, heading_tag: str = "h2"):
    pricing_heading_el = element.find("div", class_="fl-pricing-heading")
    assert pricing_heading_el

    heading_text = BeautifulSoup(block_data["value"]["heading_text"], "html.parser").get_text().strip()
    heading_el = pricing_heading_el.find(heading_tag, class_="fl-heading")
    assert heading_el and heading_text in heading_el.get_text()

    subheading_text = BeautifulSoup(block_data["value"].get("subheading_text", ""), "html.parser").get_text().strip()
    if subheading_text:
        subheading_el = pricing_heading_el.find("p", class_="fl-subheading")
        assert subheading_el and subheading_text in subheading_el.get_text()


def assert_icon_list_block(element: BeautifulSoup, block_data: dict):
    icon_list_el = element.find("ul", class_="fl-icon-text-list")
    assert icon_list_el
    list_items_data = block_data["value"]["list_items"]
    list_item_els = icon_list_el.find_all("li")
    assert len(list_item_els) == len(list_items_data)
    for item_el, item_data in zip(list_item_els, list_items_data):
        item_text = BeautifulSoup(item_data["value"]["text"], "html.parser").get_text()
        assert item_text in item_el.get_text()
        icon_name = item_data["value"]["icon"]
        assert item_el.find("span", class_=f"fl-icon-{icon_name}")


def assert_numbered_list_block(element: BeautifulSoup, block_data: dict):
    numbered_list_el = element.find("ol", class_="fl-numbered-list")
    assert numbered_list_el
    items_data = block_data["value"]["list_items"]
    item_els = numbered_list_el.find_all("li", class_="fl-numbered-list-item")
    assert len(item_els) == len(items_data)
    for item_el, item_data in zip(item_els, items_data):
        heading = BeautifulSoup(item_data["value"]["heading"], "html.parser").get_text()
        text = BeautifulSoup(item_data["value"]["text"], "html.parser").get_text()
        assert heading in item_el.find("div", class_="fl-numbered-list-item-heading").get_text()
        assert text in item_el.find("div", class_="fl-numbered-list-item-text").get_text()


def assert_timeline_block(element: BeautifulSoup, block_data: dict, heading_tag: str = "h2"):
    timeline_el = element.find("ol", class_="fl-timeline")
    assert timeline_el
    items_data = block_data["value"]["list_items"]
    item_els = timeline_el.find_all("li", class_="fl-timeline-item")
    assert len(item_els) == len(items_data)
    for item_el, item_data in zip(item_els, items_data):
        assert_heading_block(item_el, item_data["value"], heading_tag=heading_tag)


def assert_media_block(element: BeautifulSoup, block_data: dict):
    first_item = block_data["value"][0]
    if first_item["type"] == "image":
        images_el = element.find("div", class_="image-variants-display")
        assert_image_variants_attributes(images_element=images_el, images_value=first_item["value"])


class TestDownloadFirefoxButtonBlock:
    """Unit tests for DownloadFirefoxButtonBlock.clean() and get_context()."""

    def test_clean_pretranslated_label_only_is_valid(self, download_firefox_button_block, pretranslated_phrase_snippet):
        download_firefox_button_block.clean({"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}})

    def test_clean_custom_label_only_is_valid(self, download_firefox_button_block):
        download_firefox_button_block.clean({"pretranslated_label": None, "custom_label": "Try Firefox", "settings": {}})

    def test_clean_neither_pretranslated_label_nor_custom_label_raises(self, download_firefox_button_block):
        with pytest.raises(StructBlockValidationError) as exc_info:
            download_firefox_button_block.clean({"pretranslated_label": None, "custom_label": "", "settings": {}})
        assert "pretranslated_label" in exc_info.value.block_errors

    def test_clean_whitespace_only_custom_label_treated_as_empty(self, download_firefox_button_block):
        with pytest.raises(StructBlockValidationError) as exc_info:
            download_firefox_button_block.clean({"pretranslated_label": None, "custom_label": "   ", "settings": {}})
        assert "pretranslated_label" in exc_info.value.block_errors

    def test_clean_both_pretranslated_label_and_custom_label_raises(self, download_firefox_button_block, pretranslated_phrase_snippet):
        with pytest.raises(StructBlockValidationError) as exc_info:
            download_firefox_button_block.clean({"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "Also this", "settings": {}})
        assert "custom_label" in exc_info.value.block_errors

    def test_get_context_uses_pretranslated_label(self, download_firefox_button_block, pretranslated_phrase_snippet):
        value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
        context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == "Get Firefox"

    def test_get_context_uses_localized_snippet(self, download_firefox_button_block, pretranslated_phrase_snippet):
        """get_localized() returns the locale-specific label for the active locale."""
        es_mx_locale = LocaleFactory(language_code="es-MX")
        es_mx_snippet = PretranslatedPhrase.objects.create(
            locale=es_mx_locale,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        with translation.override("es-mx"):
            value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
            context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == es_mx_snippet.label

    def test_get_context_falls_back_to_snippet_when_get_localized_returns_none(self, download_firefox_button_block, pretranslated_phrase_snippet):
        """When get_localized() returns None (no translation, no fallback), falls back to the snippet's own label."""
        # Create a FR locale so Locale.get_active() resolves, but don't create a FR snippet.
        # get_localized() will find no FR translation and no configured fallback → returns None.
        LocaleFactory(language_code="fr")
        with translation.override("fr"):
            value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
            context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == pretranslated_phrase_snippet.label

    def test_get_context_uses_custom_label(self, download_firefox_button_block):
        value = {"pretranslated_label": None, "custom_label": "Download Now", "settings": {}}
        context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == "Download Now"

    def test_get_context_pretranslated_takes_priority_over_custom_label(self, download_firefox_button_block, pretranslated_phrase_snippet):
        value = {
            "pretranslated_label": pretranslated_phrase_snippet,
            "custom_label": "This gets ignored because pretranslated_label is set",
            "settings": {},
        }
        context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == "Get Firefox"

    def test_get_context_no_label_set(self, download_firefox_button_block):
        value = {"pretranslated_label": None, "custom_label": "", "settings": {}}
        context = download_firefox_button_block.get_context(value)
        assert "button_label" not in context


class TestLabelSourceMixin:
    """Test the LabelSourceMixin."""

    def test_clean_rejects_non_live_snippet(self, download_firefox_button_block):
        """LocalizedLiveSnippetChooserBlock.clean rejects live=False snippets."""
        draft_snippet = PretranslatedPhrase.objects.create(
            translation_key="11111111-1111-1111-1111-111111111111",
            locale=Locale.get_default(),
            label="Draft Phrase",
            live=False,
        )
        value = {"pretranslated_label": draft_snippet, "custom_label": "", "settings": {}}
        with pytest.raises(StructBlockValidationError):
            download_firefox_button_block.clean(value)

    def test_get_context_exposes_button_label_en_us_from_pretranslated_label(self, download_firefox_button_block, pretranslated_phrase_snippet):
        """Test the context's button_label_en_us."""
        value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
        context = download_firefox_button_block.get_context(value)
        assert context["button_label_en_us"] == "Get Firefox"

    def test_get_context_button_label_en_us_stays_english_when_active_locale_differs(
        self, download_firefox_button_block, pretranslated_phrase_snippet
    ):
        """Test the context's button_label and button_label_en_us for a non-en-US translation."""
        es_mx_locale = LocaleFactory(language_code="es-MX")
        PretranslatedPhrase.objects.create(
            locale=es_mx_locale,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        with translation.override("es-mx"):
            value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
            context = download_firefox_button_block.get_context(value)
        # User-visible label is localized.
        assert context["button_label"] == "Obtén Firefox"
        # Analytics-safe English source is unchanged.
        assert context["button_label_en_us"] == "Get Firefox"

    def test_get_context_button_label_en_us_resolves_english_when_stored_fk_is_localized(
        self, download_firefox_button_block, pretranslated_phrase_snippet
    ):
        """
        When a translated button has pretranslated text, the button_label_en_us is in English.
        """
        es_mx_locale = LocaleFactory(language_code="es-MX")
        es_mx_snippet = PretranslatedPhrase.objects.create(
            locale=es_mx_locale,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        with translation.override("es-mx"):
            # The stored FK is the locale-specific phrase, as the migration produces.
            value = {"pretranslated_label": es_mx_snippet, "custom_label": "", "settings": {}}
            context = download_firefox_button_block.get_context(value)
        assert context["button_label"] == "Obtén Firefox"
        assert context["button_label_en_us"] == "Get Firefox"

    def test_get_context_button_label_en_us_falls_back_to_custom_label(self, download_firefox_button_block):
        """For the custom_label path, button_label_en_us is the custom text as-is."""
        value = {"pretranslated_label": None, "custom_label": "Custom text", "settings": {}}
        context = download_firefox_button_block.get_context(value)
        assert context["button_label_en_us"] == "Custom text"

    def test_get_searchable_content_includes_both_label_sources(self, download_firefox_button_block, pretranslated_phrase_snippet):
        """Test the get_searchable_content value."""
        value = {"pretranslated_label": pretranslated_phrase_snippet, "custom_label": "", "settings": {}}
        content = download_firefox_button_block.get_searchable_content(value)
        assert "Get Firefox" in content

        value = {"pretranslated_label": None, "custom_label": "Click me", "settings": {}}
        content = download_firefox_button_block.get_searchable_content(value)
        assert "Click me" in content


class TestButtonBlockLabelRendering:
    """Tests that every button template renders the locale-resolved `button_label`."""

    @pytest.mark.parametrize("btn_type", _BUTTON_BLOCK_TYPES_NOT_DOWNLOAD)
    def test_render_uses_button_label(self, btn_type, rf):
        html = _render_button(btn_type, rf.get("/"), custom_label="Zqxlabel123")
        assert "Zqxlabel123" in html, f"{btn_type} did not render the custom_label via button_label"
        assert "None" not in html

    @pytest.mark.parametrize("btn_type", _BUTTON_BLOCK_TYPES_NOT_DOWNLOAD)
    def test_render_with_no_label_set_emits_no_none(self, btn_type, rf):
        """
        Test a block with neither pretranslated_label nor custom_label.

        Such a block must render without raising an error, and without emitting
        a literal 'None'.
        """
        html = _render_button(btn_type, rf.get("/"))
        assert "None" not in html


class TestButtonBlockCleanComposition:
    """Test ButtonBlock's clean() method."""

    def test_label_missing_and_link_invalid_surfaces_both_errors(self):
        block = ButtonBlock()
        value = block.to_python(
            {
                "settings": dict(_BTN_SETTINGS),
                "pretranslated_label": None,
                "custom_label": "",
                "link": {**_BTN_LINK, "custom_url": ""},  # custom_url type with blank url -> link error
            }
        )
        with pytest.raises(StructBlockValidationError) as exc:
            block.clean(value)
        assert "pretranslated_label" in exc.value.block_errors  # mixin's missing-label error
        assert "link" in exc.value.block_errors  # child block's own error

    def test_label_missing_and_link_valid_surfaces_only_label_error(self):
        block = ButtonBlock()
        value = block.to_python(
            {
                "settings": dict(_BTN_SETTINGS),
                "pretranslated_label": None,
                "custom_label": "",
                "link": dict(_BTN_LINK),  # valid
            }
        )
        with pytest.raises(StructBlockValidationError) as exc:
            block.clean(value)
        assert "pretranslated_label" in exc.value.block_errors
        assert "link" not in exc.value.block_errors  # no cross-pollination

    def test_set_as_default_label_missing_and_snippet_missing_surfaces_both_errors(self):
        """Verify that SetAsDefault.clean() raises errors as expected."""
        block = SetAsDefaultButtonBlock()
        value = block.to_python(
            {
                "settings": dict(_BTN_SETTINGS),
                "pretranslated_label": None,
                "custom_label": "",
                "snippet": None,  # required chooser left empty -> snippet error
            }
        )
        with pytest.raises(StructBlockValidationError) as exc:
            block.clean(value)
        assert "pretranslated_label" in exc.value.block_errors  # mixin's missing-label error
        assert "snippet" in exc.value.block_errors  # child chooser's own error


class TestFXAButtonUtmCampaign:
    """
    Test the FXAButton.

    fxa_button derives utm_campaign from the stable English label
    (button_label_en_us), so the campaign slug is locale-invariant. The visible
    label still localizes; only the analytics slug is the same across locales.
    """

    def test_analytics_attributes_are_locale_invariant_when_pretranslated_label_set(self, rf, pretranslated_phrase_snippet):
        es_mx = LocaleFactory(language_code="es-MX")
        PretranslatedPhrase.objects.create(
            locale=es_mx,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        block, raw = _button_block_and_value("fxa_button", pretranslated_label=pretranslated_phrase_snippet.pk)
        ctx = _render_context(rf.get("/"))

        # Build a fresh value inside each locale: the snippet's localized lookup
        # caches on the instance, so reusing one bound value across locales would
        # leak the first locale's result into the second.
        with translation.override("en-US"):
            html_en = block.render(block.to_python(raw), context=dict(ctx))
        with translation.override("es-mx"):
            html_es = block.render(block.to_python(raw), context=dict(ctx))

        # button_label_en_us is the en-US source label regardless of active locale,
        # so both utm_campaign and data-cta-text are identical across locales.
        assert _fxa_utm_campaign(html_en) == _fxa_utm_campaign(html_es) == "get_firefox"
        assert _get_cta_text(html_en) == _get_cta_text(html_es) == "Heading - Get Firefox"

    def test_analytics_attributes_derive_from_custom_label(self, rf):
        # For the custom_label path button_label_en_us == custom_label, so both
        # utm_campaign and data-cta-text follow the editor-typed text.
        ctx = _render_context(rf.get("/"))

        block_a, raw_a = _button_block_and_value("fxa_button", custom_label="Log in")
        html_a = block_a.render(block_a.to_python(raw_a), context=dict(ctx))
        assert _fxa_utm_campaign(html_a) == "log_in"
        assert _get_cta_text(html_a) == "Heading - Log in"

        block_b, raw_b = _button_block_and_value("fxa_button", custom_label="Sign up")
        html_b = block_b.render(block_b.to_python(raw_b), context=dict(ctx))
        assert _fxa_utm_campaign(html_b) == "sign_up"
        assert _get_cta_text(html_b) == "Heading - Sign up"


class TestButtonCtaText:
    """
    Test data-cta-text for ButtonBlock and UITourButtonBlock.

    All LabelSourceMixin buttons set analytics_text to the stable English label
    (button_label_en_us) so analytics aggregate across locales. The visible label
    still localizes; only the analytics attribute uses the English source.

    FirefoxFocusButtonBlock is the exception: it uses only block_text in
    analytics_text (no button label), so the CTA text is locale-invariant by
    default regardless of the label.
    """

    @pytest.mark.parametrize("btn_type", ["button", "uitour_button"])
    def test_cta_text_is_locale_invariant_when_pretranslated_label_set(self, rf, pretranslated_phrase_snippet, btn_type):
        """Pretranslated label: data-cta-text uses the en-US source label regardless of active locale."""
        es_mx = LocaleFactory(language_code="es-MX")
        PretranslatedPhrase.objects.create(
            locale=es_mx,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        block, raw = _button_block_and_value(btn_type, pretranslated_label=pretranslated_phrase_snippet.pk)
        ctx = _render_context(rf.get("/"))

        with translation.override("en-US"):
            html_en = block.render(block.to_python(raw), context=dict(ctx))
        with translation.override("es-mx"):
            html_es = block.render(block.to_python(raw), context=dict(ctx))

        assert _get_cta_text(html_en) == _get_cta_text(html_es) == "Heading - Get Firefox"

    @pytest.mark.parametrize("btn_type", ["button", "uitour_button"])
    def test_cta_text_derives_from_custom_label(self, rf, btn_type):
        """Custom label: data-cta-text tracks the editor-typed text."""
        ctx = _render_context(rf.get("/"))
        block, raw = _button_block_and_value(btn_type, custom_label="Learn more")
        html = block.render(block.to_python(raw), context=dict(ctx))
        assert _get_cta_text(html) == "Heading - Learn more"

    def test_focus_button_cta_text_is_block_heading_only(self, rf):
        """FirefoxFocusButtonBlock: analytics_text is block_text only — button label is excluded."""
        ctx = _render_context(rf.get("/"))
        block, raw = _button_block_and_value("focus_button", custom_label="Download Focus")
        html = block.render(block.to_python(raw), context=dict(ctx))
        assert _get_cta_text(html) == "Heading"


def assert_tags_content_item(tags_value: list, rendered_element: BeautifulSoup):
    tags_element = rendered_element.find("div", class_="fl-tags")
    assert tags_element
    tag_elements = tags_element.find_all("span", class_="fl-tag")
    assert len(tag_elements) == len(tags_value)
    for tag_element, tag_data in zip(tag_elements, tags_value):
        assert_tag_attributes(tag_element, tag_data)


def assert_rich_text_content_item(
    rich_text_value: str,
    rendered_element: BeautifulSoup,
    heading_text: str,
    cta_position_prefix: str,
):
    content_text = BeautifulSoup(rich_text_value, "html.parser").get_text()
    assert content_text in rendered_element.get_text()

    rich_text_soup = BeautifulSoup(rich_text_value, "html.parser")
    for link_index, link in enumerate(rich_text_soup.find_all("a")):
        uid = link.get("uid")
        if uid:
            link_text = link.get_text().strip()
            rendered_link = rendered_element.find("a", attrs={"data-cta-uid": uid})
            assert rendered_link is not None, f"Rich text link uid={uid!r} not found in rendered HTML"
            assert _UUID_RE.match(uid), f"Rich text link {link.get('href')!r} has invalid uid: {uid!r}"
            expected_cta_text = f"{heading_text.strip()} - {link_text}" if heading_text.strip() else link_text
            expected_cta_position = f"{cta_position_prefix}.link-{link_index + 1}"
            assert rendered_link["data-cta-text"] == expected_cta_text
            assert rendered_link["data-cta-position"] == expected_cta_position


def assert_buttons_content_item(
    buttons_value: list,
    rendered_element: BeautifulSoup,
    context: dict,
    cta_position_prefix: str,
    heading_text: str,
):
    buttons_wrapper = rendered_element.find("div", class_="fl-buttons")
    assert buttons_wrapper
    button_elements = buttons_wrapper.find_all("a", class_="fl-button")
    assert len(button_elements) == len(buttons_value)
    for button_index, button in enumerate(buttons_value):
        button_element = button_elements[button_index]
        cta_position = f"{cta_position_prefix}.button-{button_index + 1}"
        cta_text = f"{heading_text.strip()} - {button['value']['custom_label'].strip()}"
        assert_button_attributes(
            button_element=button_element,
            button_data=button,
            context=context,
            cta_position=cta_position,
            cta_text=cta_text,
        )


def assert_content_items(
    content_items: list,
    rendered_element: BeautifulSoup,
    context: dict,
    cta_position_prefix: str,
    heading_text: str,
):
    assert len(content_items) > 0
    for item in content_items:
        if item["type"] == "tags":
            assert_tags_content_item(item["value"], rendered_element)
        elif item["type"] == "rich_text":
            assert_rich_text_content_item(item["value"], rendered_element, heading_text, cta_position_prefix)
        elif item["type"] == "buttons":
            assert_buttons_content_item(item["value"], rendered_element, context, cta_position_prefix, heading_text)


def assert_media_content_variants(region, variants, section_prefix, context, heading_tag="h3"):
    for index, variant in enumerate(variants):
        div = region.find_all("div", class_="fl-mediacontent")[index]
        value = variant["value"]

        # Heading
        heading_value = value["heading"]
        assert_heading_block(div, heading_value, heading_tag=heading_tag)

        # Content items
        heading_text = BeautifulSoup(heading_value["heading_text"], "html.parser").get_text()
        content_items = value["content"]
        cta_position_prefix = f"{section_prefix}.item-{index + 1}-media_content"
        assert_content_items(content_items, div, context, cta_position_prefix, heading_text)

        # Media
        media_element = div.find("div", class_="fl-mediacontent-media")
        assert media_element

        media_value = value["media"][0]
        if media_value["type"] == "image":
            assert_image_variants_attributes(images_element=media_element, images_value=media_value["value"])
        elif media_value["type"] == "video":
            video_div = div.find("div", class_="fl-video")
            assert_video_attributes(video_div, media_value)

        # Settings: media_after → fl-mediacontent-reverse; narrow → is-narrow
        if value["settings"].get("media_after"):
            assert "fl-mediacontent-reverse" in div.get("class", [])
        else:
            assert "fl-mediacontent-reverse" not in div.get("class", [])

        if value["settings"].get("narrow"):
            assert "is-narrow" in div.get("class", [])
        else:
            assert "is-narrow" not in div.get("class", [])


def test_media_content_block(index_page, placeholder_images, rf):
    sections = get_media_content_sections()
    variants = get_media_content_variants()
    narrow_variants = get_media_content_narrow_variants()
    page = get_media_content_test_page()

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
    assert_media_content_variants(upper_section_elements[0], variants, "upper-block-1-section", context, heading_tag="h2")
    assert_media_content_variants(upper_section_elements[1], narrow_variants, "upper-block-2-section", context, heading_tag="h3")

    # Lower region: all sections have block_level=2 (children get h3)
    lower_section_elements = lower.find_all("section", class_="fl-section")
    assert len(lower_section_elements) == len(sections)
    assert len(lower_section_elements[0].find_all("div", class_="fl-mediacontent")) == len(variants)
    assert len(lower_section_elements[1].find_all("div", class_="fl-mediacontent")) == len(narrow_variants)
    assert_media_content_variants(lower_section_elements[0], variants, "lower-block-1-section", context, heading_tag="h3")
    assert_media_content_variants(lower_section_elements[1], narrow_variants, "lower-block-2-section", context, heading_tag="h3")


def test_buttons(index_page, rf):
    test_page = get_buttons_test_page()
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
            buttons_data = next(b for b in block["value"]["content"] if b["type"] == "buttons")["value"]
            # Store/uitour/qr_code_modal buttons don't render as <a class="fl-button">
            non_store_data = [b for b in buttons_data if b["type"] not in ["store_button", "uitour_button", "qr_code_modal_button"]]
            store_data = [b for b in buttons_data if b["type"] == "store_button"]

            button_elements = [el for el in intro.find_all("a", class_="fl-button") if "Extended Support Release" not in el.get("data-cta-text", "")]
            assert len(button_elements) == len(non_store_data)

            heading_text = BeautifulSoup(block["value"]["heading"]["heading_text"], "html.parser").get_text()

            for btn_index, (button_data, button_element) in enumerate(zip(non_store_data, button_elements)):
                if button_data["type"] == "button":
                    cta_position = f"{block_prefix}block-{block_index + 1}-intro.button-{btn_index + 1}"
                    cta_text = f"{heading_text.strip()} - {button_data['value']['custom_label'].strip()}"
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
                        inner_html = f"{icon_html}{button_data['value']['custom_label']}"
                    rendered_fxa_button = fxa_button(
                        ctx=context,
                        entrypoint=entrypoint,
                        button_text=button_data["value"]["custom_label"],
                        optional_parameters={
                            "utm_campaign": utm_parameters["utm_campaign"],
                        },
                        optional_attributes={
                            "data-cta-text": f"{heading_text.strip()} - {button_data['value']['custom_label'].strip()}",
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
                    assert button_data["value"]["custom_label"] in button_element.get_text()
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


def test_uitour_buttons_2026(index_page, rf):
    test_page = get_buttons_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Collect all uitour_button entries from the fixture blocks, keyed by analytics_id.
    uitour_buttons_data = {}
    for block in get_button_blocks():
        for content_item in block["value"].get("content", []):
            if content_item["type"] != "buttons":
                continue
            for btn in content_item["value"]:
                if btn["type"] == "uitour_button":
                    analytics_id = btn["value"]["settings"]["analytics_id"]
                    uitour_buttons_data[analytics_id] = btn["value"]

    assert uitour_buttons_data, "Expected UITour button fixture data"

    # Each uitour_button renders as <div class="ui-tour is-hidden"><button ...>
    uitour_wrappers = soup.find_all("div", class_="ui-tour")
    rendered_by_uid = {el.find("button")["data-cta-uid"]: el for el in uitour_wrappers if el.find("button")}

    assert len(rendered_by_uid) == len(uitour_buttons_data), f"Expected {len(uitour_buttons_data)} UITour buttons, found {len(rendered_by_uid)}"

    for analytics_id, btn_value in uitour_buttons_data.items():
        wrapper = rendered_by_uid.get(analytics_id)
        assert wrapper, f"No rendered UITour button found for analytics_id={analytics_id}"

        assert "is-hidden" in wrapper["class"], f"{analytics_id}: wrapper should start hidden"

        button_el = wrapper.find("button")
        button_type = btn_value["button_type"]
        expected_class = UI_TOUR_CLASSES[button_type]
        assert expected_class in button_el["class"], f"{analytics_id}: expected class '{expected_class}' on button, got {button_el['class']}"

        assert btn_value["custom_label"] in button_el.get_text(), f"{analytics_id}: expected label '{btn_value['custom_label']}' in button text"


def test_banner_block(index_page, placeholder_images, rf):
    banners = get_banner_variants()
    test_page = get_banner_test_page()

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
            if settings.get("centralize_content"):
                inner = banner_element.find("div", class_="fl-banner-content-inner")
                assert "fl-banner-content-inner-centralize-content" in inner["class"]
            anchor_id = settings.get("anchor_id")
            if anchor_id:
                assert banner_element.parent.get("id") == anchor_id

            heading_block = banner["value"]["heading"]
            assert_section_heading_attributes(section_element=banner_element, heading_data=heading_block, index=heading_index_offset + index)

            heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

            # Content items
            content_items = banner["value"]["content"]
            cta_position_prefix = f"{region_name}-block-{index + 1}-banner"
            assert_content_items(content_items, banner_element, context, cta_position_prefix, heading_text)

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


def test_topic_list_block(index_page, placeholder_images, rf):
    upper_variants = get_topic_list_upper_variants()
    lower_variants = get_topic_list_lower_variants()
    test_page = get_topic_list_test_page()

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
                    cta_text = f"{heading_text.strip()} - {button['value']['custom_label'].strip()}"
                    assert_button_attributes(
                        button_element=button_element,
                        button_data=button,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_kit_banner_block(index_page, placeholder_images, rf):
    banners = get_kit_banner_variants()
    test_page = get_kit_banner_test_page()

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
            background_theme = settings.get("background_theme")
            if background_theme == "dark-purple-gradient":
                assert "fl-banner-dark-purple-gradient" in banner_element["class"]
            else:
                assert "fl-banner-dark-purple-gradient" not in banner_element["class"]

            heading_block = banner["value"]["heading"]
            assert_section_heading_attributes(
                section_element=banner_element,
                heading_data=heading_block,
                index=heading_index_offset + index,
            )

            heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

            # Content items
            content_items = banner["value"]["content"]
            cta_position_prefix = f"{region_name}-block-{index + 1}-kit_banner"
            assert_content_items(content_items, banner_element, context, cta_position_prefix, heading_text)


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
    cta_text = f"{heading_text.strip()} - {resolve_download_button_label(button).strip()}"
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
        cta_text=f"{heading_text} - {button['value']['custom_label'].strip()}",
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


def test_freeform_page_split_layout(index_page, rf):
    page = get_freeform_page_test_page()

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


def test_freeform_page_single_column_layout(index_page, rf):
    page = get_mobile_store_qr_code_test_page()
    page.upper_content = []
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.specific.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not soup.find("div", class_="fl-split-page-upper"), "Upper section should not exist when upper_content is empty"
    assert not soup.find("div", class_="fl-split-page-lower"), "Lower section should not exist when upper_content is empty"
    main = soup.find("div", class_="fl-main")
    assert main and "has-gradient-bottom" in main.get("class", [])


# ---------------------------------------------------------------------------
# 2026 Blocks
# ---------------------------------------------------------------------------


def test_intro_block(index_page, placeholder_images, rf):
    variants = get_intro_variants()
    page = get_intro_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper, "Upper section should exist"
    assert lower, "Lower section should exist"

    # Both upper and lower contain all variants
    for region_index, region in enumerate([upper, lower]):
        region_name = "upper" if region_index == 0 else "lower"
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

            # Content items
            content_items = value.get("content", [])
            cta_position_prefix = f"{region_name}-block-{index + 1}-intro"
            assert_content_items(content_items, intro_el, context, cta_position_prefix, heading_text)

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


# Cards


def assert_cards_list_settings(grid_el: BeautifulSoup, settings: dict):
    classes = grid_el.get("class", [])
    container_width = settings.get("container_width", "")
    cards_per_row = settings.get("cards_per_row", "")
    two_wide_xs = settings.get("two_wide_xs", False)

    if container_width and container_width != "scroll":
        assert f"container-{container_width}" in classes
    if cards_per_row:
        assert f"cols-{cards_per_row}-md" in classes
    if two_wide_xs:
        assert "two-col-xs" in classes
    if container_width == "scroll":
        assert "fl-card-grid-scroll" in classes
        assert grid_el.get("data-js") == "fl-card-grid-scroll"
        assert grid_el.find("div", class_="fl-card-grid-scroll-inner")


def assert_sticker_card(card_el, variant, context, region_name, heading_tag, block_index, card_index):
    value = variant["value"]
    headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
    heading = card_el.find(heading_tag, class_="fl-heading")
    assert heading and headline_text in heading.get_text()

    if value["settings"].get("expand_link"):
        assert "fl-card-expand-link" in card_el.get("class", [])

    content_text = BeautifulSoup(value["content"], "html.parser").get_text()
    body = card_el.find(class_="fl-body")
    assert body and content_text in body.get_text()

    if value.get("superheading"):
        superheading_text = BeautifulSoup(value["superheading"], "html.parser").get_text()
        superheading_el = card_el.find(class_="fl-superheading")
        assert superheading_el and superheading_text in superheading_el.get_text()

    sticker_el = card_el.find("div", class_="fl-card-sticker")
    assert_image_variants_attributes(
        images_element=sticker_el,
        images_value=value["image"],
        widths="width-400",
    )

    for button_data in value["buttons"]:
        if button_data["type"] == "button":
            button_el = card_el.find("a", class_="fl-button")
            cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
            cta_position = f"{region_name}-block-{block_index}-section.item-1-cards_list.card-{card_index}.button-1"
            assert_button_attributes(
                button_element=button_el,
                button_data=button_data,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )


def assert_illustration_card(card_el, variant, context, region_name, heading_tag, block_index, card_index):
    value = variant["value"]
    headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
    heading = card_el.find(heading_tag, class_="fl-heading")
    assert heading and headline_text in heading.get_text()

    if value["settings"].get("expand_link"):
        assert "fl-card-expand-link" in card_el.get("class", [])

    content_text = BeautifulSoup(value["content"], "html.parser").get_text()
    body = card_el.find(class_="fl-body")
    assert body and content_text in body.get_text()

    if value.get("eyebrow"):
        eyebrow_text = BeautifulSoup(value["eyebrow"], "html.parser").get_text()
        eyebrow_el = card_el.find(class_="fl-superheading")
        assert eyebrow_el and eyebrow_text in eyebrow_el.get_text()

    media_el = card_el.find("div", class_="fl-card-media")
    media_value = value["media"][0]
    if media_value["type"] == "image":
        assert_image_variants_attributes(images_element=media_el, images_value=media_value["value"])
    elif media_value["type"] == "video":
        assert_video_attributes(media_el.find("div", class_="fl-video"), media_value)
    elif media_value["type"] == "animation":
        assert_animation_attributes(media_el.find("div", class_="fl-video"), media_value)

    for button_data in value["buttons"]:
        if button_data["type"] == "button":
            button_el = card_el.find("a", class_="fl-button")
            cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
            cta_position = f"{region_name}-block-{block_index}-section.item-1-cards_list.card-{card_index}.button-1"
            assert_button_attributes(
                button_element=button_el,
                button_data=button_data,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )


def assert_outlined_card(card_el, variant, context, region_name, heading_tag, block_index, card_index):
    value = variant["value"]
    headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
    heading = card_el.find(heading_tag, class_="fl-heading")
    assert heading and headline_text in heading.get_text()

    if value["settings"].get("expand_link"):
        assert "fl-card-expand-link" in card_el.get("class", [])
    else:
        assert "fl-card-expand-link" not in card_el.get("class", [])

    content_text = BeautifulSoup(value["content"], "html.parser").get_text()
    body = card_el.find(class_="fl-body")
    assert body and content_text in body.get_text()

    if value.get("sticker", {}).get("image"):
        sticker_el = card_el.find("div", class_="fl-card-sticker")
        assert sticker_el
        assert_image_variants_attributes(images_element=sticker_el, images_value=value["sticker"])

    for button_data in value["buttons"]:
        if button_data["type"] == "button":
            button_el = card_el.find("a", class_="fl-button")
            cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
            cta_position = f"{region_name}-block-{block_index}-section.item-1-cards_list.card-{card_index}.button-1"
            assert_button_attributes(
                button_element=button_el,
                button_data=button_data,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )


def assert_icon_card(card_el, variant, context, region_name, heading_tag, block_index, card_index):
    value = variant["value"]
    headline_text = BeautifulSoup(value["headline"], "html.parser").get_text()
    heading = card_el.find(heading_tag, class_="fl-heading")
    assert heading and headline_text in heading.get_text()

    if value["settings"].get("expand_link"):
        assert "fl-card-expand-link" in card_el.get("class", [])
    else:
        assert "fl-card-expand-link" not in card_el.get("class", [])

    content_text = BeautifulSoup(value["content"], "html.parser").get_text()
    body = card_el.find(class_="fl-body")
    assert body and content_text in body.get_text()

    icon_el = card_el.find("span", class_="fl-icon")
    assert icon_el and f"fl-icon-{value['icon']}" in icon_el.get("class", [])

    for button_data in value["buttons"]:
        if button_data["type"] == "button":
            button_el = card_el.find("a", class_="fl-button")
            cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
            cta_position = f"{region_name}-block-{block_index}-section.item-1-cards_list.card-{card_index}.button-1"
            assert_button_attributes(
                button_element=button_el,
                button_data=button_data,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )


def assert_testimonial_card(card_el, card_data):
    value = card_data["value"]

    content_text = BeautifulSoup(value["content"], "html.parser").get_text()
    quote_el = card_el.find("blockquote", class_="fl-testimonial-card-quote")
    assert quote_el and content_text in quote_el.get_text()

    attribution_text = BeautifulSoup(value["attribution"], "html.parser").get_text()
    cite_el = card_el.find("cite", class_="fl-testimonial-card-attribution")
    assert cite_el and attribution_text in cite_el.get_text()

    if value.get("attribution_role"):
        role_text = BeautifulSoup(value["attribution_role"], "html.parser").get_text()
        role_el = card_el.find("span", class_="fl-testimonial-card-role")
        assert role_el and role_text in role_el.get_text()
    else:
        assert not card_el.find("span", class_="fl-testimonial-card-role")

    image_container = card_el.find("div", class_="fl-testimonial-card-image")
    if value["attribution_image"]["image"]:
        assert image_container and image_container.find("img")
    else:
        assert not image_container


def test_sticker_cards_block(index_page, placeholder_images, rf):
    sections_data = get_sticker_cards_sections()
    page = get_sticker_cards_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            grid_el = section_el.find("div", class_="fl-card-grid")
            assert grid_el
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            assert_cards_list_settings(grid_el, section_data["value"]["content"][0]["value"]["settings"])

            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            cards = section_el.find_all("article", class_="fl-card")
            assert len(cards) == len(section_cards_data)
            for i, card_data in enumerate(section_cards_data):
                assert_card_block(cards[i], card_data, context, region_name, heading_tag, section_index + 1, i + 1)


def test_illustration_cards_block(index_page, placeholder_images, rf):
    sections_data = get_illustration_cards_sections()
    page = get_illustration_cards_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            grid_el = section_el.find("div", class_="fl-card-grid")
            assert grid_el
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            assert_cards_list_settings(grid_el, section_data["value"]["content"][0]["value"]["settings"])

            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            cards = section_el.find_all("article", class_="fl-card")
            assert len(cards) == len(section_cards_data)
            for i, card_data in enumerate(section_cards_data):
                assert_card_block(cards[i], card_data, context, region_name, heading_tag, section_index + 1, i + 1)


def test_step_cards_block(index_page, placeholder_images, rf):
    variants = get_step_card_variants()
    page = get_step_cards_test_page()

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
                    cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
                    cta_position = f"{region_name}-block-2-section.item-1-step_cards.card-{i + 1}.button-1"
                    assert_button_attributes(
                        button_element=button_el,
                        button_data=button_data,
                        context=context,
                        cta_position=cta_position,
                        cta_text=cta_text,
                    )


def test_outlined_cards_block(index_page, placeholder_images, rf):
    sections_data = get_outlined_cards_sections()
    page = get_outlined_cards_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            grid_el = section_el.find("div", class_="fl-card-grid")
            assert grid_el
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            assert_cards_list_settings(grid_el, section_data["value"]["content"][0]["value"]["settings"])

            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            cards = section_el.find_all("article", class_="fl-card")
            assert len(cards) == len(section_cards_data)
            for i, card_data in enumerate(section_cards_data):
                assert_card_block(cards[i], card_data, context, region_name, heading_tag, section_index + 1, i + 1)


def test_icon_cards_block(index_page, placeholder_images, rf):
    sections_data = get_icon_cards_sections()
    page = get_icon_cards_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            grid_el = section_el.find("div", class_="fl-card-grid")
            assert grid_el
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            assert_cards_list_settings(grid_el, section_data["value"]["content"][0]["value"]["settings"])

            # Upper first section: block_level=1, children h2; all other sections: children h3
            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            cards = section_el.find_all("article", class_="fl-card")
            assert len(cards) == len(section_cards_data)
            for i, card_data in enumerate(section_cards_data):
                assert_card_block(cards[i], card_data, context, region_name, heading_tag, section_index + 1, i + 1)


def test_featured_image_section_block(index_page, placeholder_images, rf):
    variants = get_featured_image_section_variants()
    page = get_featured_image_section_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    icon_cards = get_icon_card_variants()[:3]
    variant = variants[0]
    value = variant["value"]

    for region_name, region in [("upper", upper), ("lower", lower)]:
        sections = region.find_all("section", class_="fl-featured-image-section")
        assert len(sections) == 1
        section = sections[0]

        # Heading: upper block is h1 (first heading on page), lower block is h2
        heading_index = 0 if region_name == "upper" else 1
        assert_section_heading_attributes(section, value["heading"], heading_index)

        # Media image
        media_el = section.find("div", class_="fl-featured-image-section-media")
        assert media_el
        assert_image_variants_attributes(
            images_element=media_el,
            images_value=value["media"][0]["value"],
            sizes="100vw",
        )

        # Cards: upper block_level=1 → content block_level=2 → h2; lower block_level=2 → content block_level=3 → h3
        card_heading_tag = "h2" if region_name == "upper" else "h3"
        card_els = section.find_all("article", class_="fl-card")
        assert len(card_els) == len(icon_cards)

        block_position_prefix = f"{region_name}-block-1-featured_image_section.item-1-cards_list"

        for card_index, card_data in enumerate(icon_cards):
            card_el = card_els[card_index]
            content_items = card_data["value"]["content"]

            heading_item = next(item for item in content_items if item["type"] == "heading")
            headline_text = BeautifulSoup(heading_item["value"]["heading_text"], "html.parser").get_text()
            heading_el = card_el.find(card_heading_tag, class_="fl-heading")
            assert heading_el and headline_text in heading_el.get_text()

            buttons_item = next((item for item in content_items if item["type"] == "buttons"), None)
            if buttons_item:
                buttons_item_index = content_items.index(buttons_item) + 1
                for btn_index, button_data in enumerate(buttons_item["value"]["buttons"], start=1):
                    if button_data["type"] == "button":
                        button_el = card_el.find("a", class_="fl-button")
                        cta_position = f"{block_position_prefix}.card-{card_index + 1}.item-{buttons_item_index}-buttons.button-{btn_index}"
                        cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
                        assert_button_attributes(
                            button_element=button_el,
                            button_data=button_data,
                            context=context,
                            cta_position=cta_position,
                            cta_text=cta_text,
                        )


def test_testimonial_cards_block(index_page, placeholder_images, rf):
    sections_data = get_testimonial_cards_sections()
    page = get_testimonial_cards_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            grid_el = section_el.find("div", class_="fl-card-grid")
            assert grid_el
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            assert_cards_list_settings(grid_el, section_data["value"]["content"][0]["value"]["settings"])

            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"
            cards = section_el.find_all("article", class_="fl-card")
            assert len(cards) == len(section_cards_data)
            for i, card_data in enumerate(section_cards_data):
                assert_card_block(cards[i], card_data, context, region_name, heading_tag, section_index + 1, i + 1)


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
                        cta_text = f"{headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
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

            icon_list = section_el.find("ul", class_="fl-icon-text-list")
            assert icon_list

            list_items = icon_list.find_all("li")
            expected_items = variant["value"]["list_items"]
            assert len(list_items) == len(expected_items)

            for li, item in zip(list_items, expected_items):
                expected_text = BeautifulSoup(item["value"]["text"], "html.parser").get_text()
                assert expected_text in li.get_text()
                icon_wrap = li.find("span", class_="fl-icon-wrap")
                assert icon_wrap


def test_showcase_block(index_page, placeholder_images, rf):
    variants = get_showcase_variants()
    page = get_showcase_test_page()

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


def test_card_gallery_block(index_page, placeholder_images, rf):
    variants = get_card_gallery_variants()
    page = get_card_gallery_test_page()

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
                    cta_text = f"{main_headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
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
                    cta_text = f"{secondary_headline_text.strip()} - {button_data['value']['custom_label'].strip()}"
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
                        cta_text = f"{gallery_heading_text.strip()} - {button_data['value']['custom_label'].strip()}"
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


def test_kit_intro_block(index_page, rf):
    variants = get_kit_intro_variants()
    page = get_kit_intro_test_page()

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
            cta_text = f"{heading_text.strip()} - {button['value']['custom_label'].strip()}"
            assert_button_attributes(
                button_element=button_elements[button_index],
                button_data=button,
                context=context,
                cta_position=cta_position,
                cta_text=cta_text,
            )

    # The Kit Intro block isn't allowed on the lower section
    assert not lower.find_all("div", class_="fl-home-intro")


def test_carousel_block(index_page, placeholder_images, rf):
    variants = get_carousel_variants()
    page = get_carousel_test_page()

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
                cta_text = f"{heading_text.strip()} - {button['value']['custom_label'].strip()}"
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
        heading_text = BeautifulSoup(media_content["value"]["heading"]["heading_text"], "html.parser").get_text()
        assert heading_text in media_content_headings[i].get_text()

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
            heading_el = div.find("div", class_="fl-notification-heading")
            assert heading_el
            if headline_raw:
                headline_text = BeautifulSoup(headline_raw, "html.parser").get_text()
                assert headline_text in heading_el.get_text()
                assert message in div.get_text()
            else:
                assert message in heading_el.get_text()


def test_two_column_cards_block(index_page, rf):
    variants = get_two_column_cards_variants()
    page = get_two_column_cards_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    # Each variant is a section containing one two_column_cards block.
    tcc_variants = [(section_index, section["value"]["content"][0]) for section_index, section in enumerate(variants)]

    # ns.headings persists across both page regions: upper runs first, so lower
    # starts with ns_headings = len(tcc_variants) (all sections have a heading).
    for region_name, region, ns_headings_start in [
        ("upper", upper, 0),
        ("lower", lower, len(tcc_variants)),
    ]:
        block_containers = region.find_all("div", class_="fl-two-column-cards")
        assert len(block_containers) == len(tcc_variants)

        ns_headings = ns_headings_start
        for (section_index, tcc_data), container in zip(tcc_variants, block_containers):
            section_number = section_index + 1
            # The page template sets block_level=1 for the first heading block,
            # block_level=2 for all subsequent ones. Each section adds 1 for
            # its content, so card headings are h(outer_block_level + 1).
            outer_block_level = 1 if ns_headings == 0 else 2
            card_heading_tag = f"h{outer_block_level + 1}"
            ns_headings += 1
            settings = tcc_data["value"]["settings"]

            anchor_id = settings.get("anchor_id", "")
            if anchor_id:
                assert container.get("id") == anchor_id

            theme = settings.get("theme", "")
            if theme:
                assert f"fl-two-column-cards-{theme}" in container.get("class", [])

            reduce_card_padding = settings.get("reduce_card_padding", False)
            if reduce_card_padding:
                assert "reduce-card-padding" in container.get("class", [])
            else:
                assert "reduce-card-padding" not in container.get("class", [])

            card_wrappers = container.find_all("div", class_="fl-two-column-card-wrapper")
            assert len(card_wrappers) == 2

            for card_index, card_wrapper in enumerate(card_wrappers):
                card_data = tcc_data["value"]["cards"][card_index]["value"]
                card_number = card_index + 1
                card_el = card_wrapper.find("div", class_="fl-two-column-card")

                image_position = card_data["settings"].get("image_position", "")
                if image_position and image_position != "default":
                    assert f"image-is-stuck-{image_position}" in card_el.get("class", [])
                else:
                    assert not any("image-is-stuck" in cls for cls in card_el.get("class", []))

                tag = card_data["tag"]
                if tag:
                    tag_el = card_wrapper.find("span", class_="fl-card-tag")
                    assert tag_el and tag in tag_el.get_text()

                heading_text = ""
                assert card_data["content"], "Each card must have content blocks for the test to verify correct rendering"
                for content_index, block_data in enumerate(card_data["content"]):
                    block_type = block_data["type"]
                    content_position = (
                        f"{region_name}-block-{section_number}-section"
                        f".item-1-two_column_cards.card-{card_number}"
                        f".content-{content_index + 1}-{block_type}"
                    )
                    if block_type == "heading":
                        assert_heading_block(card_el, block_data["value"], heading_tag=card_heading_tag)
                        heading_text = BeautifulSoup(block_data["value"]["heading_text"], "html.parser").get_text()
                    elif block_type == "button_row":
                        button_data = block_data["value"]["buttons"][0]
                        cta_text = f"{heading_text} - {button_data['value']['custom_label'].strip()}"
                        assert_button_attributes(
                            button_element=card_el.find("a", class_="fl-button"),
                            button_data=button_data,
                            context=context,
                            cta_position=content_position + ".button-1",
                            cta_text=cta_text,
                        )
                    elif block_type == "pricing_heading":
                        assert_pricing_heading_block(card_el, block_data, heading_tag=card_heading_tag)
                    elif block_type == "timeline":
                        assert_timeline_block(card_el, block_data, heading_tag=card_heading_tag)
                    elif block_type == "icon_list":
                        assert_icon_list_block(card_el, block_data)
                    elif block_type == "numbered_list":
                        assert_numbered_list_block(card_el, block_data)
                    elif block_type == "media":
                        assert_media_block(card_el, block_data)


def _make_card_value(image_position, content_types):
    """Build a card value dict ready for to_python(), placing a media block at the given indices."""
    block = TwoColumnCardBlock()
    content_blocks = []
    for index, block_type in enumerate(content_types):
        if block_type == "media":
            content_blocks.append({"type": "media", "value": [], "id": f"test-media-{index}"})
        else:
            content_blocks.append({"type": "rich_text", "value": f"<p>text {index}</p>", "id": f"test-rt-{index}"})
    raw = {
        "settings": {"image_position": image_position},
        "tag": "",
        "content": content_blocks,
    }
    return block.to_python(raw)


@pytest.mark.parametrize(
    "image_position, content_types, is_valid",
    [
        ("top", ["media", "rich_text", "rich_text"], True),
        ("top", ["rich_text", "media", "rich_text"], False),
        ("top-right", ["media", "rich_text", "rich_text"], True),
        ("top-right", ["rich_text", "rich_text", "media"], False),
        ("full-top", ["media", "rich_text"], True),
        ("full-top", ["rich_text", "media"], False),
        ("bottom", ["rich_text", "rich_text", "media"], True),
        ("bottom", ["media", "rich_text", "rich_text"], False),
        ("bottom-left", ["rich_text", "rich_text", "media"], True),
        ("bottom-left", ["rich_text", "media", "rich_text"], False),
        ("full-bottom", ["rich_text", "media"], True),
        ("full-bottom", ["media", "rich_text"], False),
        ("left", ["rich_text", "media", "rich_text"], True),
        ("right", ["media", "rich_text", "rich_text"], True),
        ("default", ["media", "rich_text", "rich_text"], True),
        ("", ["media", "rich_text", "rich_text"], True),
    ],
)
def test_two_column_card_media_position_validation(image_position, content_types, is_valid):
    block = TwoColumnCardBlock()
    value = _make_card_value(image_position, content_types)
    if is_valid:
        block.clean(value)
    else:
        with pytest.raises(StructBlockValidationError):
            block.clean(value)


def test_two_column_card_media_position_validation_no_media_skips_check():
    block = TwoColumnCardBlock()
    value = _make_card_value("top", ["rich_text", "rich_text"])
    block.clean(value)


def test_uuid_block_is_not_translatable():
    """UUIDBlock stores analytics IDs, not user-facing content — it must not be sent to translators."""

    assert UUIDBlock().get_translatable_segments("cfdf0d2c-7eee-49c2-8747-80450e22dbdd") == []


def test_untranslatable_char_block_excludes_content_from_translation():
    """
    UntranslatableCharBlock holds internal/config values (field identifiers, hidden
    field defaults), not user-facing copy — its content must never be sent to translators.

    A plain CharBlock has no get_translatable_segments method, so wagtail_localize's
    extractor treats its value as a translatable string (the isinstance branch); defining
    the method to return [] is what opts this value out of extraction.
    """
    assert not hasattr(CharBlock(), "get_translatable_segments")
    assert UntranslatableCharBlock().get_translatable_segments("office_phone") == []


def test_untranslatable_char_block_restore_returns_value_unchanged():
    """
    Because nothing is extracted for translation, ingesting translated segments must
    return the original value untouched — even if segments are somehow supplied.
    """
    block = UntranslatableCharBlock()
    assert block.restore_translated_segments("name", []) == "name"
    assert block.restore_translated_segments("name", ["ignored"]) == "name"


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


def _make_button_row_value(count, allow_uitour=False):
    block = ButtonRowBlock(allow_uitour=allow_uitour)
    variants = get_button_variants()
    buttons = [dict(variants["primary"], id=f"test-btn-{i}") for i in range(count)]
    return block.to_python({"buttons": buttons})


def test_button_row_block_three_buttons_is_valid():
    block = ButtonRowBlock()
    block.clean(_make_button_row_value(3))


def test_button_row_block_four_buttons_raises():
    block = ButtonRowBlock()
    with pytest.raises(StructBlockValidationError):
        block.clean(_make_button_row_value(4))


def test_section_block_accepts_button_row():
    block = SectionBlock(require_heading=False)
    child_block_names = [name for name, _ in block.declared_blocks["content"].child_blocks.items()]
    assert "button_row" in child_block_names


def test_two_column_card_accepts_button_row():
    block = TwoColumnCardBlock()
    child_block_names = list(block.declared_blocks["content"].child_blocks.keys())
    assert "button_row" in child_block_names
    assert "button" not in child_block_names


_DOWNLOAD_BUTTON_CONTEXT = {
    "analytics_id": "test-analytics-id",
    "theme_class": "",
    "label": "Get Firefox",
    "cta_text": "Get Firefox",
    "block_position": "test-position",
    "icon_name": "",
    "icon_position": "right",
    "exclude_unsupported_content": True,
    "enable_marketing_attribution": False,
    "show_default_browser_checkbox": False,
    "show_store_button": False,
    "is_preview": False,
    "utm_parameters": None,
    "flare_styles": True,
    "params": "",
}


def _render_download_button(rf, specific_version):
    request = rf.get("/en-US/")
    html = render_to_string(
        "components/download-firefox-button.html",
        {**_DOWNLOAD_BUTTON_CONTEXT, "request": request, "specific_version": specific_version},
    )
    return BeautifulSoup(html, "html.parser").find("a", class_="download-link")


def test_download_button_default_uses_thanks_url(rf):
    link = _render_download_button(rf, "default")
    assert link["href"] == "/thanks/"
    assert link.get("data-version-forced") is None


def test_download_button_forced_uses_direct_url(rf):
    link = _render_download_button(rf, "win64")
    assert "/thanks/" not in link["href"]
    assert link["data-version-forced"] == "true"


@pytest.mark.parametrize("specific_version", ["win", "win64", "win64-aarch64", "osx", "linux64", "linux64-aarch64"])
def test_download_button_forced_versions_produce_direct_url(rf, specific_version):
    link = _render_download_button(rf, specific_version)
    assert "/thanks/" not in link["href"]
    assert link["data-version-forced"] == "true"


def test_button_row_block_allow_uitour_exposes_uitour_type():
    block_with = ButtonRowBlock(allow_uitour=True)
    block_without = ButtonRowBlock(allow_uitour=False)
    button_types_with = list(block_with.declared_blocks["buttons"].child_blocks.keys())
    button_types_without = list(block_without.declared_blocks["buttons"].child_blocks.keys())
    assert "uitour_button" in button_types_with
    assert "uitour_button" not in button_types_without


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


def test_roadmap_list_section_block(index_page, rf):
    intro_fixture = get_roadmap_page_intro()
    intro_value = intro_fixture[0]["value"]
    intro_heading_data = intro_value["heading"]
    intro_button_data = intro_value["content"][0]["value"][0]["value"]

    section_variants = get_roadmap_list_section_variants()
    page = get_roadmap_list_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    context = page.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")

    # Intro: superheading, heading, subheading
    superheading_el = soup.find("p", class_="fl-superheading")
    assert superheading_el and BeautifulSoup(intro_heading_data["superheading_text"], "html.parser").get_text() in superheading_el.get_text()
    intro_heading_el = soup.find("h1", class_="fl-heading")
    expected_heading_text = BeautifulSoup(intro_heading_data["heading_text"], "html.parser").get_text()
    assert intro_heading_el and expected_heading_text in intro_heading_el.get_text()
    subheading_el = soup.find("p", class_="fl-subheading")
    expected_subheading = BeautifulSoup(intro_heading_data["subheading_text"], "html.parser").get_text()
    assert subheading_el and expected_subheading in subheading_el.get_text()

    # Intro button links to what's new index page with correct analytics
    whatsnew_index = Page.objects.get(id=intro_button_data["link"]["page"]).specific
    intro_button = soup.find("a", href=whatsnew_index.get_url())
    assert intro_button and intro_button_data["custom_label"] in intro_button.get_text()
    assert intro_button["data-cta-text"] == f"{expected_heading_text} - {intro_button_data['custom_label']}"
    assert intro_button["data-cta-uid"] == intro_button_data["settings"]["analytics_id"]
    assert intro_button["data-cta-position"] == "intro.button-1"

    # Filters
    filters = soup.find_all("div", class_="fl-roadmap-list-filter")
    assert len(filters) == 1
    filter_el = filters[0]
    filter_options = filter_el.find_all("button", class_="fl-roadmap-filter-button")
    filter_options = [f for f in filter_options if f.get("data-filter")]
    assert len(filter_options) == len(ROADMAP_TAG_LABELS)
    for button in filter_options:
        assert button.has_attr("data-filter")
        tag = button["data-filter"]
        assert tag in ROADMAP_TAG_LABELS, f"Unexpected filter tag {tag}"
        assert str(ROADMAP_TAG_LABELS[tag]) in button.get_text(), f"Expected label for tag {tag}"

    last_updated_el = filter_el.find("p")
    assert last_updated_el
    assert f"Last updated: {date_format(page.last_published_at, 'DATE_FORMAT')}" in last_updated_el.get_text()

    section_divs = soup.find_all("section", class_="fl-roadmap-list-section")
    assert len(section_divs) == len(section_variants)

    for section_index, (section_data, section_div) in enumerate(zip(section_variants, section_divs)):
        section_value = section_data["value"]
        block_number = section_index + 1

        # Headline renders as h2 (page has an intro so block_level=2)
        headline_el = section_div.find("h2")
        assert headline_el and section_value["headline"] in headline_el.get_text()

        # Subheadline
        subheadline = section_value.get("subheadline", "")
        if subheadline:
            subheadline_el = section_div.find("p", class_="fl-subheading")
            subheadline_text = BeautifulSoup(subheadline, "html.parser").get_text()
            assert subheadline_el and subheadline_text in subheadline_el.get_text()

        # Items list
        item_list = section_div.find("ul", class_="fl-roadmap-list")
        assert item_list
        item_elements = item_list.find_all("li", class_="fl-roadmap-item")
        assert len(item_elements) == len(section_value["list_items"])

        for item_index, (item_fixture, item_el) in enumerate(zip(section_value["list_items"], item_elements)):
            item_number = item_index + 1
            item_value = item_fixture["value"]
            expected_position = f"block-{block_number}-roadmap_list_section.item-{item_number}"

            # Icon
            icon = item_value.get("icon", "")
            if icon:
                icon_el = item_el.find("span", class_="fl-icon")
                assert icon_el, f"Expected icon element for item {item_number}"
                assert f"fl-icon-{icon}" in icon_el["class"], f"Expected icon {icon} for item {item_number}"

            # Title renders as h3 (block_level 2 → child level 3)
            title_el = item_el.find("h3")
            assert title_el and item_value["title"] in title_el.get_text()

            # Status badge
            status = item_value["status"]
            status_badge = item_el.find("span", class_=f"fl-roadmap-status-{status}")
            if status:
                assert status_badge, f"Expected status badge for {status}"
                assert str(ROADMAP_STATUS_LABELS[status]) in status_badge.get_text()
            else:
                assert not status_badge, f"Did not expect status badge for item {item_number}"

            # Tags
            tags = item_value.get("tags", [])
            if tags:
                assert item_el.has_attr("data-tags"), f"Expected data-tags attribute for item {item_number}"
                assert item_el["data-tags"] == ",".join(tags), f"Expected data-tags to be comma-separated list of tags for item {item_number}"
                tags_container = item_el.find("div", class_="fl-roadmap-tags")
                assert tags_container
                tag_elements = tags_container.find_all("span", class_="fl-tag")
                assert len(tag_elements) == len(tags)
                for tag, tag_el in zip(tags, tag_elements):
                    assert str(ROADMAP_TAG_LABELS[tag]) in tag_el.get_text()
                    icon_el = tag_el.find("span", class_="fl-icon")
                    assert icon_el, f"Expected icon element for tag {tag} in item {item_number}"
                    assert f"fl-icon-{ROADMAP_TAG_ICONS[tag]}" in icon_el["class"], f"Expected icon for tag {tag} in item {item_number}"
            else:
                assert not item_el.find("div", class_="fl-roadmap-tags")

            # Description
            description_text = BeautifulSoup(item_value["description"], "html.parser").get_text()
            assert description_text in item_el.get_text()

            # Learn more button
            learn_more_url = item_value["learn_more_link"].get("custom_url", "")
            if learn_more_url:
                learn_more_button = item_el.find("a", attrs={"data-cta-position": f"{expected_position}.learn-more"})
                assert learn_more_button, f"Expected learn more button for item {item_number}"
                assert learn_more_button["href"] == add_utm_parameters(context, learn_more_url)
                expected_learn_more_text = f"{item_value['title']} - Learn more"
                assert learn_more_button["data-cta-text"] == expected_learn_more_text
                learn_more_analytics_id = item_value.get("learn_more_analytics_id", "")
                if learn_more_analytics_id:
                    assert learn_more_button["data-cta-uid"] == learn_more_analytics_id

            # Secondary button
            secondary_url = item_value["secondary_button_link"].get("custom_url", "")
            secondary_label = item_value.get("secondary_button_label", "")
            if secondary_url and secondary_label:
                secondary_button = item_el.find("a", attrs={"data-cta-position": f"{expected_position}.secondary-button"})
                assert secondary_button, f"Expected secondary button for item {item_number}"
                assert secondary_button["href"] == add_utm_parameters(context, secondary_url)
                assert secondary_label in secondary_button.get_text()
                expected_secondary_text = f"{item_value['title']} - {secondary_label}"
                assert secondary_button["data-cta-text"] == expected_secondary_text
                secondary_analytics_id = item_value.get("secondary_button_analytics_id", "")
                if secondary_analytics_id:
                    assert secondary_button["data-cta-uid"] == secondary_analytics_id
                secondary_icon = item_value.get("secondary_button_icon", "")
                secondary_icon_position = item_value.get("secondary_button_icon_position", "right")
                if secondary_icon:
                    assert item_el.find("span", class_=f"fl-icon-{secondary_icon}")
                    icon_wrapper = item_el.find("span", class_=f"fl-icon-{secondary_icon_position}")
                    assert icon_wrapper, f"Expected icon position {secondary_icon_position} for item {item_number}"


# ---------------------------------------------------------------------------
# Card block
# ---------------------------------------------------------------------------


def assert_card_block(card_el, card_data, context, region_name, heading_tag, block_index, card_index):
    value = card_data["value"]
    s = value["settings"]

    classes = card_el.get("class", [])
    variant = s.get("variant", "")
    align = s.get("align", "start") or "start"

    if variant:
        assert f"fl-card-{variant}" in classes
    assert f"fl-card-{align}" in classes

    if s.get("expand_link"):
        assert "fl-card-expand-link" in classes
    else:
        assert "fl-card-expand-link" not in classes

    content_items = value["content"]
    block_text = ""
    for item in content_items:
        if item["type"] == "heading":
            block_text = BeautifulSoup(item["value"]["heading_text"], "html.parser").get_text().strip()
            break

    for item_index, content_item in enumerate(content_items, start=1):
        block_type = content_item["type"]
        item_position = f"{region_name}-block-{block_index}-section.item-1-cards_list.card-{card_index}.item-{item_index}-{block_type}"

        if block_type == "heading":
            heading_text = BeautifulSoup(content_item["value"]["heading_text"], "html.parser").get_text()
            heading = card_el.find(heading_tag, class_="fl-heading")
            assert heading and heading_text in heading.get_text()

            superheading_raw = content_item["value"].get("superheading_text", "")
            if superheading_raw:
                superheading_text = BeautifulSoup(superheading_raw, "html.parser").get_text()
                superheading_el = card_el.find("p", class_="fl-superheading")
                assert superheading_el and superheading_text in superheading_el.get_text()

        elif block_type == "content":
            content_text = BeautifulSoup(content_item["value"], "html.parser").get_text()
            assert content_text in card_el.get_text()

        elif block_type == "icon":
            icon_wrapper = card_el.find("div", class_="fl-card-media-icon")
            assert icon_wrapper
            icon_name = content_item["value"]["icon"]
            icon_el = icon_wrapper.find("span", class_="fl-icon")
            assert icon_el and f"fl-icon-{icon_name}" in icon_el.get("class", [])

        elif block_type == "pictogram":
            pictogram_wrapper = card_el.find("div", class_="fl-card-media-pictogram")
            assert pictogram_wrapper and pictogram_wrapper.find("img")

        elif block_type == "media":
            assert card_el.find("img") or card_el.find("video")

        elif block_type == "tags_list":
            for tag in content_item["value"]:
                assert tag["title"] in card_el.get_text()
                tag_el = card_el.find("span", class_=f"fl-tag-{tag['color']}")
                assert tag_el and tag["title"] in tag_el.get_text()

        elif block_type == "testimonial":
            t = content_item["value"]
            blockquote = card_el.find("blockquote", class_="fl-card-testimonial")
            assert blockquote
            quote_text = BeautifulSoup(t["content"], "html.parser").get_text()
            assert quote_text in blockquote.get_text()
            attribution_text = BeautifulSoup(t["attribution"], "html.parser").get_text()
            cite_el = blockquote.find("cite", class_="fl-card-testimonial-attribution")
            assert cite_el and attribution_text in cite_el.get_text()
            if t.get("attribution_role"):
                role_text = BeautifulSoup(t["attribution_role"], "html.parser").get_text()
                role_el = blockquote.find("span", class_="fl-card-testimonial-role")
                assert role_el and role_text in role_el.get_text()
            if t.get("attribution_image", {}).get("image"):
                img_container = blockquote.find("div", class_="fl-card-testimonial-image")
                assert img_container and img_container.find("img")

        elif block_type == "buttons":
            for btn_index, button_data in enumerate(content_item["value"]["buttons"], start=1):
                if button_data["type"] != "button":
                    continue
                btn_position = f"{item_position}.button-{btn_index}"
                button_el = card_el.find("a", attrs={"data-cta-position": btn_position})
                assert button_el, f"Expected button with data-cta-position={btn_position}"
                button_label = button_data["value"].get("custom_label", "")
                expected_cta_text = f"{block_text} - {button_label}" if block_text else button_label
                assert_button_attributes(
                    button_element=button_el,
                    button_data=button_data,
                    context=context,
                    cta_position=btn_position,
                    cta_text=expected_cta_text,
                )


def test_card_block(index_page, placeholder_images, rf):
    get_card_variants()
    sections_data = get_card_sections()
    page = get_card_test_page()

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
        assert len(sections) == len(sections_data)

        for section_index, (section_el, section_data) in enumerate(zip(sections, sections_data)):
            section_cards_data = section_data["value"]["content"][0]["value"]["cards"]
            heading_tag = "h2" if (region_index == 0 and section_index == 0) else "h3"

            rendered_cards = section_el.find_all("article", class_="fl-card")
            assert len(rendered_cards) == len(section_cards_data)

            for card_i, (card_el, card_data) in enumerate(zip(rendered_cards, section_cards_data)):
                assert_card_block(
                    card_el=card_el,
                    card_data=card_data,
                    context=context,
                    region_name=region_name,
                    heading_tag=heading_tag,
                    block_index=section_index + 1,
                    card_index=card_i + 1,
                )
