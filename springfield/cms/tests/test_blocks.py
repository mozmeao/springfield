# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from unittest import mock
from urllib.parse import unquote, urlparse, urlunparse

from django.conf import settings
from django.template.loader import render_to_string
from django.test import override_settings
from django.utils import translation
from django.utils.formats import date_format

import pytest
from bs4 import BeautifulSoup
from wagtail import blocks
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
    CardsListBlock,
    ComparisonTableBlock,
    FirefoxFocusButtonBlock,
    FXAccountButtonBlock,
    IconChoiceBlock,
    IconListItemValue,
    ImpactDashBlock,
    QRCodeModalButtonBlock,
    SectionBlock,
    SetAsDefaultButtonBlock,
    ShowcaseBlock,
    SpringfieldLinkBlock,
    TabBlock,
    TabsBlock,
    TwoColumnCardBlock,
    UITourButtonBlock,
    UntranslatableCharBlock,
    UUIDBlock,
    icon_display_label,
)
from springfield.cms.fixtures.article_page_fixtures import (
    get_article_pages,
    get_article_theme_hub_page,
    get_article_theme_page,
    get_theme_hub_illustration_cards_section,
    get_theme_hub_page_pictogram_row_section,
    get_theme_hub_page_upper_content,
    get_theme_page_icon_cards_section,
    get_theme_page_illustration_cards_section,
    get_theme_page_intro,
    get_theme_page_pictogram_row_section,
)
from springfield.cms.fixtures.banner_fixtures import get_banner_test_page, get_banner_variants
from springfield.cms.fixtures.base_fixtures import get_placeholder_images
from springfield.cms.fixtures.blog_fixtures import (
    FEATURED_DESCRIPTIONS,
    FEATURED_TITLES,
    IMAGE_CAPTION,
    create_blog_article,
    get_blog_article_content,
    get_blog_index_page,
    get_blog_tags,
    get_blog_topics,
)
from springfield.cms.fixtures.button_fixtures import get_button_blocks, get_button_variants, get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import get_card_sections, get_card_test_page, get_card_variants
from springfield.cms.fixtures.card_gallery_fixtures import get_card_gallery_test_page, get_card_gallery_variants
from springfield.cms.fixtures.cards_fixtures import (
    get_illustration_cards_sections,
    get_illustration_cards_test_page,
    get_outlined_cards_sections,
    get_outlined_cards_test_page,
    get_pictogram_cards_sections,
    get_pictogram_cards_test_page,
    get_step_card_variants,
    get_step_cards_test_page,
)
from springfield.cms.fixtures.carousel_fixtures import get_carousel_test_page, get_carousel_variants
from springfield.cms.fixtures.comparison_table_fixtures import (
    cell as comparison_cell,
    get_comparison_table_test_page,
    get_comparison_table_variants,
    image_header_cell,
    result_cell,
    row as comparison_row,
)
from springfield.cms.fixtures.enterprise_download_fixtures import get_enterprise_download_test_page
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
from springfield.cms.icon_utils import icon_value_fn
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


def _render_context(request, block_text="Heading", block_position="block-1-intro") -> dict:
    """
    Minimal parent context a button block needs to render in isolation.

    `fluent_l10n` is normally injected by the page/snippet context (see
    `springfield.cms.pattern_contexts`); we supply it here so set_as_default
    (whose snippet uses Fluent) renders without a context KeyError.
    """
    return {
        "block_text": block_text,
        "block_position": block_position,
        "request": request,
        "fluent_l10n": fluent_l10n(["en"], settings.FLUENT_DEFAULT_FILES),
    }


def _render_button(btn_type, request, **label_kwargs):
    snippet_pk = get_set_as_default_snippet().id if btn_type == "set_as_default_button" else None
    block, raw = _button_block_and_value(btn_type, snippet_pk=snippet_pk, **label_kwargs)
    bound = block.to_python(raw)
    return block.render(bound, context=_render_context(request))


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
    elif first_item["type"] == "video":
        video_el = element.find("div", class_="fl-video")
        assert_video_attributes(video_element=video_el, video_data=first_item)


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


class TestButtonCtaText:
    """
    Test data-cta-text for ButtonBlock and UITourButtonBlock.
    """

    @pytest.mark.parametrize("btn_type", ["button", "uitour_button", "focus_button"])
    def test_cta_text_uses_localized_pretranslated_label(self, rf, pretranslated_phrase_snippet, btn_type):
        """Pretranslated label: data-cta-text uses the locale-resolved label for the active locale."""
        es_mx = LocaleFactory(language_code="es-MX")
        PretranslatedPhrase.objects.create(
            locale=es_mx,
            translation_key=pretranslated_phrase_snippet.translation_key,
            label="Obtén Firefox",
            live=True,
        )
        block, raw = _button_block_and_value(btn_type, pretranslated_label=pretranslated_phrase_snippet.pk)

        with translation.override("en-US"):
            context = _render_context(rf.get("/"), block_text="English Heading")
            html_en = block.render(block.to_python(raw), context=dict(context))
            assert _get_cta_text(html_en) == "English Heading - Get Firefox"
        with translation.override("es-MX"):
            context = _render_context(rf.get("/"), block_text="Título en Español")
            html_es = block.render(block.to_python(raw), context=dict(context))
            assert _get_cta_text(html_es) == "Título en Español - Obtén Firefox"

    @pytest.mark.parametrize("btn_type", ["button", "uitour_button", "focus_button"])
    def test_cta_text_uses_custom_label(self, rf, btn_type):
        """Custom label: data-cta-text tracks the editor-typed text."""
        with translation.override("en-US"):
            context = _render_context(rf.get("/"), block_text="English Heading")
            block, raw = _button_block_and_value(btn_type, custom_label="Learn more")
            html = block.render(block.to_python(raw), context=dict(context))
            assert _get_cta_text(html) == "English Heading - Learn more"
        with translation.override("es-MX"):
            context = _render_context(rf.get("/"), block_text="Título en Español")
            block, raw = _button_block_and_value(btn_type, custom_label="Saber más")
            html = block.render(block.to_python(raw), context=dict(context))
            assert _get_cta_text(html) == "Título en Español - Saber más"


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


def test_home_pictogram_cards_list_block(index_page, placeholder_images, rf):
    test_page = get_home_test_page()

    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    cards_list = get_cards_list()

    cards_list_div = soup.find("div", class_="fl-card-grid")
    assert cards_list_div

    card_elements = cards_list_div.find_all("article", class_="fl-card")

    cards = cards_list["value"]["cards"]
    assert len(card_elements) == len(cards)

    for index, card in enumerate(cards):
        card_element = card_elements[index]
        content_items = card["value"]["content"]

        heading_block = next(b for b in content_items if b["type"] == "heading")
        heading_text = BeautifulSoup(heading_block["value"]["heading_text"], "html.parser").get_text()
        heading_el = card_element.find("h2", class_="fl-heading")
        assert heading_el and heading_text in heading_el.get_text()

        pictogram_wrapper = card_element.find("div", class_="fl-card-media-pictogram")
        assert pictogram_wrapper and pictogram_wrapper.find("img")


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
    illustration_card_articles = illustration_card_article_section.find_all("article", class_="fl-card")
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
    icon_card_articles = icon_card_section.find_all("article", class_="fl-card")
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

    # Pictogram Row Articles
    pictogram_row_section_data = get_theme_page_pictogram_row_section()
    pictogram_row_section = sections[2]

    assert_section_heading_attributes(
        section_element=pictogram_row_section,
        heading_data=pictogram_row_section_data["value"]["heading"],
        index=2,
    )

    assert pictogram_row_section and pictogram_row_section.find(class_="fl-stacked-article-list")
    pictogram_row_articles = pictogram_row_section.find_all("article", class_="fl-article-item")
    pictogram_row_articles_data = pictogram_row_section_data["value"]["content"][0]["value"]["cards"]
    assert len(pictogram_row_articles) == len(pictogram_row_articles_data)

    for i, article_data in enumerate(pictogram_row_articles_data):
        card_element = pictogram_row_articles[i]
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
        pictogram_element = card_element.find("img")
        assert pictogram_element.prettify() == BeautifulSoup(rendered_icon, "html.parser").find("img").prettify()


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
    illustration_card_articles = illustration_section.find_all("article", class_="fl-card")
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

    # Pictogram Row Section (second section in lower content)
    pictogram_row_section_data = get_theme_hub_page_pictogram_row_section()
    pictogram_row_section = sections[1]

    assert_section_heading_attributes(
        section_element=pictogram_row_section,
        heading_data=pictogram_row_section_data["value"]["heading"],
        index=1,
    )

    assert pictogram_row_section and pictogram_row_section.find(class_="fl-stacked-article-list")
    pictogram_row_articles = pictogram_row_section.find_all("article", class_="fl-article-item")
    pictogram_row_articles_data = pictogram_row_section_data["value"]["content"][0]["value"]["cards"]
    assert len(pictogram_row_articles) == len(pictogram_row_articles_data)

    for i, article_data in enumerate(pictogram_row_articles_data):
        card_element = pictogram_row_articles[i]
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
        rendered_pictogram = image(img, "width-400").img_tag()
        pictogram_element = card_element.find("img")
        assert pictogram_element.prettify() == BeautifulSoup(rendered_pictogram, "html.parser").find("img").prettify()


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
    illustration_cards = illustration_section.find_all("article", class_="fl-card")

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


def test_pictogram_row_renders_pictogram_without_override(index_page, rf):
    """When a pictogram row card has no image override, the article's pictogram
    should be rendered instead of the placeholder image."""
    page = get_article_theme_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    sections = soup.find_all("section", class_="fl-section")
    pictogram_section = sections[2]
    pictogram_row_articles = pictogram_section.find_all("article", class_="fl-article-item")

    articles = get_article_pages()
    images = get_placeholder_images()
    image_ids = {img.id: img for img in images}

    # Card at index 1 has overrides.image = None (articles[3] = regular_article_2),
    # so it should fall back to the article's pictogram
    card_element = pictogram_row_articles[1]

    section_data = get_theme_page_pictogram_row_section()
    card_data = section_data["value"]["content"][0]["value"]["cards"][1]
    article_ids = {article.id: article for article in articles}
    article = article_ids[card_data["value"]["article"]]
    pictogram_element = card_element.find("img")

    # Should NOT be the Firefox logo placeholder
    assert pictogram_element["src"] != "/media/img/logos/firefox/firefox-logo.svg"

    # Should match the article's pictogram rendered with image()
    expected_img = image_ids[article.sticker.id]
    rendered_icon = image(expected_img, "width-400").img_tag()
    expected_soup = BeautifulSoup(rendered_icon, "html.parser").find("img")
    assert pictogram_element.prettify() == expected_soup.prettify()


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
    icon_card_articles = icon_section.find_all("article", class_="fl-card")

    articles = get_article_pages()

    # Card at index 1 has overrides.icon = "" (articles[2] = regular_article_1),
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


def test_enterprise_download_block(index_page, rf):
    page = get_enterprise_download_test_page()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper, "Upper section should exist when upper_content has blocks"
    assert lower, "Lower section should exist when content has blocks"

    for region in (upper, lower):
        download_section = region.find("section", id="download")
        assert download_section, "Enterprise download section should render"
        assert "Enterprise downloads" in download_section.get_text()

        download_lists = download_section.find("div", class_="fl-enterprise-download-lists")
        assert download_lists, "Download lists container should render"
        assert download_lists.find("section", class_="fl-enterprise-download-win64"), "Windows section should render"
        assert download_lists.find("section", class_="fl-enterprise-download-mac"), "macOS section should render"
        assert download_lists.find("section", class_="fl-enterprise-download-linux"), "Linux section should render"

        win64_links = download_section.find(id="win64-download-list").find_all("a", class_="download-link")
        assert any(link["href"].startswith("https://download.mozilla.org/?product=firefox-latest-ssl&os=win64") for link in win64_links)

        mac_links = download_section.find(id="mac-download-list").find_all("a", class_="download-link")
        assert any(link["href"].startswith("https://download.mozilla.org/?product=firefox-latest-ssl&os=osx") for link in mac_links)

        linux_links = download_section.find(id="linux-download-list").find_all("a", class_="download-link")
        assert any(link["href"].startswith("https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64") for link in linux_links)

        resources = download_section.find("div", class_="fl-enterprise-download-resources")
        assert resources, "Resources block should render"
        assert resources.find("a", href="https://firefox-admin-docs.mozilla.org/")
        assert resources.find("a", href="https://github.com/mozilla/policy-templates/releases")

        assert download_section.find("p", class_="fl-body"), "ESR download language paragraph should render"


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
    card_articles = sections[0].find_all("article", class_="fl-card")
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


def test_pictogram_cards_block(index_page, placeholder_images, rf):
    sections_data = get_pictogram_cards_sections()
    page = get_pictogram_cards_test_page()

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

            description = showcase_el.find("div", class_="fl-showcase-description")
            if variant["value"].get("description"):
                description_text = BeautifulSoup(variant["value"]["description"], "html.parser").get_text()
                assert description, "Expected .fl-showcase-description to be present when description is set"
                assert description_text in description.get_text()
            else:
                assert not description, "Expected .fl-showcase-description to be absent when no description is set"

            figure = showcase_el.find("figure", class_="fl-showcase-media")
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

            if variant["value"].get("caption_description"):
                caption_description_text = BeautifulSoup(variant["value"]["caption_description"], "html.parser").get_text()
                assert caption_description_text in caption.get_text()

            cta = showcase_el.find("div", class_="fl-showcase-cta")
            if variant["value"].get("cta"):
                assert cta, "Expected .fl-showcase-cta to be present when CTA buttons are set"
            else:
                assert not cta, "Expected .fl-showcase-cta to be absent when no CTA buttons are set"


def _render_showcase(media, allow_tabs=False):
    """Render a ShowcaseBlock around the given raw media stream."""
    block = ShowcaseBlock(allow_tabs=allow_tabs)
    value = block.to_python(
        {
            "settings": {"layout": "default"},
            "headline": '<p data-block-key="2026shx1">Showcase headline</p>',
            "media": media,
            "caption_description": '<p data-block-key="2026shx2">Showcase caption</p>',
        }
    )
    return BeautifulSoup(block.render(value, context={}), "html.parser")


def test_showcase_block_wraps_tabs_media_in_a_div_not_a_figure():
    """Tabs are controls the visitor operates, so <figure> is the wrong element.

    The classes have to stay the same either way -- the layout CSS hangs off
    .fl-showcase-media, not off the tag name.
    """
    soup = _render_showcase(
        [
            {
                "type": "tabs",
                "value": {"section_id": "hub", "tabs": [{"tab_name": "First tab", "description": "<p>Tab description</p>"}]},
                "id": "2026shx0-0000-0000-0000-000000000001",
            }
        ],
        allow_tabs=True,
    )

    assert soup.find("figure") is None
    assert soup.find("figcaption") is None

    media = soup.find("div", class_="fl-showcase-media")
    assert media and media.find("div", class_="fl-media-tabs")
    assert media.find("div", class_="fl-showcase-caption")


def test_showcase_block_keeps_figure_for_non_interactive_media(placeholder_images):
    soup = _render_showcase(get_showcase_variants()[0]["value"]["media"])

    assert soup.find("div", class_="fl-showcase-media") is None

    figure = soup.find("figure", class_="fl-showcase-media")
    assert figure and figure.find("img")
    assert figure.find("figcaption", class_="fl-showcase-caption")


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


COMPARISON_RESULT_RENDERING = {
    "yes": ("fl-icon-checkmark-circle-fill", "Yes"),
    "no": ("fl-icon-close-circle-fill", "No"),
    "limited": ("fl-icon-circle-semi-filled", "Limited"),
}


def assert_comparison_result(cell_el: BeautifulSoup, result_data: dict):
    result_el = cell_el.find("div", class_="fl-comparison-result")
    assert result_el is not None

    icon_class, choice_label = COMPARISON_RESULT_RENDERING[result_data["result"]]
    icon_el = result_el.find("span", class_="fl-comparison-result-icon").find("span", class_="fl-icon")
    assert icon_class in icon_el.get("class")
    # The visible label is the accessible name, so the icon stays decorative.
    assert icon_el.get("aria-hidden") == "true"

    expected_label = result_data["label"] or choice_label
    assert result_el.find("span", class_="fl-comparison-result-label").get_text(strip=True) == expected_label


def assert_comparison_image_header(cell_el: BeautifulSoup, image_header_data: dict):
    wrapper_el = cell_el.find("div", class_="fl-comparison-image-header")
    assert wrapper_el is not None
    assert wrapper_el.find("span", class_="fl-comparison-image-header-text").get_text(strip=True) == image_header_data["label"]

    img_els = wrapper_el.find("span", class_="fl-comparison-image-header-media").find_all("img")
    has_dark_mode = bool(image_header_data.get("dark_mode_image"))
    assert len(img_els) == (2 if has_dark_mode else 1)
    for img_el in img_els:
        assert img_el.get("alt") == image_header_data["alt"]
        assert img_el.get("loading") == "lazy"
        assert img_el.get("srcset")
    if has_dark_mode:
        assert "display-light" in img_els[0].get("class", [])
        assert "display-dark" in img_els[1].get("class", [])


def assert_comparison_cell_contents(cell_el: BeautifulSoup, cell_data: dict):
    """A cell renders its optional content when added, else its plain text."""
    optional_content = cell_data.get("optional_content") or []
    if not optional_content:
        assert cell_el.get_text(strip=True) == cell_data["content"]
        return

    child = optional_content[0]
    if child["type"] == "comparison_result":
        assert_comparison_result(cell_el, child["value"])
    else:
        assert_comparison_image_header(cell_el, child["value"])


def comparison_cell_is_filled(cell_data: dict) -> bool:
    return bool(cell_data["content"] or cell_data.get("optional_content"))


def assert_comparison_table(wrapper_el: BeautifulSoup, block_data: dict):
    value = block_data["value"]
    mobile_behavior = value["mobile_behavior"]
    highlighted_column = value.get("highlighted_column") or None
    # Tables saved before the variant setting existed have no such key.
    variant = value.get("variant", "default")

    wrapper_classes = wrapper_el.get("class", [])
    assert mobile_behavior in wrapper_classes
    # The default variant adds no modifier class, so it keeps the base palette.
    if variant == "default":
        assert "browser-comparison" not in wrapper_classes
    else:
        assert variant in wrapper_classes

    header_cells_data = [c["value"] for c in value["header_row"][0]["value"]["cells"]]
    header_cell_els = wrapper_el.find("thead").find_all(["th", "td"])
    assert len(header_cell_els) == len(header_cells_data)
    for i, (cell_el, cell_data) in enumerate(zip(header_cell_els, header_cells_data)):
        assert_comparison_cell_contents(cell_el, cell_data)
        # A column header carries an accessible name; an empty cell is a plain
        # <td>, so it never trips the empty-table-header accessibility check.
        if comparison_cell_is_filled(cell_data):
            assert cell_el.name == "th"
            assert cell_el.get("scope") == "col"
        else:
            assert cell_el.name == "td"
        col_index = i + 1
        if highlighted_column and highlighted_column == col_index:
            assert "highlighted" in cell_el.get("class", [])
        else:
            assert "highlighted" not in cell_el.get("class", [])
        if cell_data["column_span"] > 1:
            assert cell_el.get("colspan") == str(cell_data["column_span"])

    content_rows_data = value["content_rows"]
    tr_elements = wrapper_el.find("tbody").find_all("tr")
    assert len(tr_elements) == len(content_rows_data)
    for tr, row_data in zip(tr_elements, content_rows_data):
        cells_data = [c["value"] for c in row_data["value"]["cells"]]
        cell_els = tr.find_all(["th", "td"])
        assert len(cell_els) == len(cells_data)
        for i, (cell_el, cell_data) in enumerate(zip(cell_els, cells_data)):
            assert_comparison_cell_contents(cell_el, cell_data)
            # The row's label cell is its row header, so screen readers can
            # announce which row a value belongs to.
            if i == 0 and comparison_cell_is_filled(cell_data):
                assert cell_el.name == "th"
                assert cell_el.get("scope") == "row"
            else:
                assert cell_el.name == "td"
            col_index = i + 1
            if highlighted_column and highlighted_column == col_index:
                assert "highlighted" in cell_el.get("class", [])
            else:
                assert "highlighted" not in cell_el.get("class", [])
            if cell_data["column_span"] > 1:
                assert cell_el.get("colspan") == str(cell_data["column_span"])


def test_comparison_table_variants(index_page, rf):
    page = get_comparison_table_test_page()
    variants = get_comparison_table_variants()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    upper = soup.find("div", class_="fl-split-page-upper")
    lower = soup.find("div", class_="fl-split-page-lower")
    assert upper and lower

    for region in (upper, lower):
        tables = region.find_all("div", class_="fl-comparison-table-wrapper")
        assert len(tables) == len(variants)
        for index, variant in enumerate(variants):
            table = tables[index]
            assert_comparison_table(table, variant)


def _render_comparison_table(header_cells, content_rows, mobile_behavior="scroll", highlighted_column=None, variant="default"):
    block = ComparisonTableBlock()
    value = block.to_python(
        {
            "variant": variant,
            "highlighted_column": highlighted_column,
            "mobile_behavior": mobile_behavior,
            "header_row": [comparison_row(cells=header_cells, row_id="hr")],
            "content_rows": content_rows,
        }
    )
    return BeautifulSoup(block.render(value), "html.parser")


def _render_comparison_result_row(cell_data):
    """One-row table whose only value cell holds ``cell_data``."""
    return _render_comparison_table(
        header_cells=[comparison_cell(""), comparison_cell("Firefox")],
        content_rows=[comparison_row(cells=[comparison_cell("Blocks trackers"), cell_data], row_id="r0")],
    )


@pytest.mark.parametrize(
    ("result", "icon_class", "label"),
    (
        ("yes", "fl-icon-checkmark-circle-fill", "Yes"),
        ("no", "fl-icon-close-circle-fill", "No"),
        ("limited", "fl-icon-circle-semi-filled", "Limited"),
    ),
)
def test_comparison_result_renders_icon_and_result_name(result, icon_class, label):
    """Each result choice picks its own icon, labelled with the result's name."""
    cell_data = result_cell(result, cell_id="c1")
    soup = _render_comparison_result_row(cell_data)

    result_el = soup.find("div", class_="fl-comparison-result")
    assert icon_class in result_el.find("span", class_="fl-icon").get("class")
    assert result_el.find("span", class_="fl-comparison-result-label").get_text(strip=True) == label


def test_comparison_result_label_can_be_overridden():
    """An author-supplied label replaces the result's name, keeping its icon."""
    cell_data = result_cell("limited", "Some features", cell_id="c1")
    soup = _render_comparison_result_row(cell_data)

    result_el = soup.find("div", class_="fl-comparison-result")
    assert "fl-icon-circle-semi-filled" in result_el.find("span", class_="fl-icon").get("class")
    assert result_el.find("span", class_="fl-comparison-result-label").get_text(strip=True) == "Some features"


def test_comparison_cell_optional_content_replaces_plain_text():
    cell_data = result_cell("yes", cell_id="c1")
    cell_data["value"]["content"] = "Ignored text"
    soup = _render_comparison_result_row(cell_data)

    value_cell = soup.find("tbody").find_all(["th", "td"])[1]
    assert "Ignored text" not in value_cell.get_text()
    assert_comparison_result(value_cell, cell_data["value"]["optional_content"][0]["value"])


def test_comparison_header_cell_with_image_header_is_a_column_header(placeholder_images):
    header_cell = image_header_cell("Firefox", cell_id="h1")
    soup = _render_comparison_table(
        header_cells=[comparison_cell(""), header_cell],
        content_rows=[comparison_row(cells=[comparison_cell("Blocks trackers"), result_cell("yes", cell_id="c1")], row_id="r0")],
    )

    header_cell_els = soup.find("thead").find_all(["th", "td"])
    # The empty corner cell stays a plain <td>; the image header cell is a real
    # column header, named by the label under the image.
    assert header_cell_els[0].name == "td"
    assert header_cell_els[1].name == "th"
    assert header_cell_els[1].get("scope") == "col"
    assert_comparison_image_header(header_cell_els[1], header_cell["value"]["optional_content"][0]["value"])


def test_comparison_image_header_renders_author_alt_text(placeholder_images):
    header_cell = image_header_cell("Firefox", cell_id="h1")
    header_cell["value"]["optional_content"][0]["value"]["alt"] = "Firefox logo"
    soup = _render_comparison_table(
        header_cells=[comparison_cell(""), header_cell],
        content_rows=[comparison_row(cells=[comparison_cell("Blocks trackers"), result_cell("yes", cell_id="c1")], row_id="r0")],
    )

    assert_comparison_image_header(soup.find("thead").find_all(["th", "td"])[1], header_cell["value"]["optional_content"][0]["value"])


def _comparison_variant_wrapper_classes(variant):
    soup = _render_comparison_table(
        header_cells=[comparison_cell(""), comparison_cell("Firefox")],
        content_rows=[comparison_row(cells=[comparison_cell("Blocks trackers"), comparison_cell("Yes")], row_id="r0")],
        variant=variant,
    )
    return soup.find("div", class_="fl-comparison-table-wrapper").get("class", [])


def test_comparison_table_browser_variant_adds_modifier_class():
    """The variant class is what swaps the highlight and border colors in CSS."""
    assert "browser-comparison" in _comparison_variant_wrapper_classes("browser-comparison")


def test_comparison_table_default_variant_adds_no_modifier_class():
    classes = _comparison_variant_wrapper_classes("default")

    assert "browser-comparison" not in classes
    assert "default" not in classes


def test_comparison_table_renders_when_variant_key_absent_from_stored_json():
    """Tables saved before the variant setting existed have no such key at all."""
    block = ComparisonTableBlock()
    value = block.to_python(
        {
            "mobile_behavior": "scroll",
            "header_row": [comparison_row(cells=[comparison_cell("PREMIUM")], row_id="hr")],
            "content_rows": [comparison_row(cells=[comparison_cell("24 hrs/day")], row_id="r0")],
        }
    )

    assert value["variant"] == "default"

    wrapper = BeautifulSoup(block.render(value), "html.parser").find("div", class_="fl-comparison-table-wrapper")

    assert "browser-comparison" not in wrapper.get("class", [])


def test_comparison_table_renders_cells_saved_before_optional_content_existed():
    """Cells saved before optional_content existed have no such key at all."""
    block = ComparisonTableBlock()
    legacy_cell = {"type": "item", "value": {"content": "24 hrs/day", "column_span": 1}, "id": "c0"}
    value = block.to_python(
        {
            "mobile_behavior": "scroll",
            "header_row": [comparison_row(cells=[{"type": "item", "value": {"content": "PREMIUM", "column_span": 1}, "id": "h0"}], row_id="hr")],
            "content_rows": [comparison_row(cells=[legacy_cell], row_id="r0")],
        }
    )

    assert len(value["content_rows"][0]["cells"][0]["optional_content"]) == 0

    soup = BeautifulSoup(block.render(value), "html.parser")

    assert soup.find("div", class_="fl-comparison-result") is None
    assert soup.find("thead").find("th").get_text(strip=True) == "PREMIUM"
    assert soup.find("tbody").find("th").get_text(strip=True) == "24 hrs/day"


class TestIconDisplayLabel:
    def test_default_label(self):
        """The icon_display_label() function returns all characters in title case."""
        assert icon_display_label("arrow-clockwise-16") == "Arrow Clockwise"

    def test_screenshot_camera_override(self):
        """For an exception, icon_display_label() returns the expected value."""
        assert icon_display_label("screenshot-camera-16") == "Camera (Screenshot)"


class TestIconValueFn:
    def test_strips_directory_and_size_suffix(self):
        assert icon_value_fn("desktop-16/arrows-and-chevrons/forward-16") == "forward"

    def test_strips_directory_only_when_no_size_suffix(self):
        assert icon_value_fn("desktop-16/permissions/auto-play-false") == "auto-play-false"

    def test_flat_path_strips_size_suffix(self):
        assert icon_value_fn("activity-16") == "activity"

    def test_flat_path_no_suffix_unchanged(self):
        assert icon_value_fn("globe") == "globe"

    def test_screenshot_camera_mapping(self):
        assert icon_value_fn("desktop-16/screenshot/screenshot-camera-16") == "screenshot-camera"

    def test_colliding_path_returns_dash_joined_value(self):
        assert icon_value_fn("mobile-24/arrows-chevrons/forward-24") == "mobile-24-arrows-chevrons-forward-24"

    def test_non_colliding_path_returns_css_name(self):
        assert icon_value_fn("mobile-24/cursors/cursors-24") == "cursors"


def _make_icon_list_item_value(icon_name, thumbnail_url=None):
    """Build an IconListItemValue without triggering a filesystem scan."""
    # Use __new__ to skip __init__ on both classes, avoiding the directory scan.
    block = blocks.StructBlock.__new__(blocks.StructBlock)
    icon_block = IconChoiceBlock.__new__(IconChoiceBlock)
    icon_block._thumbnails_source = {icon_name: thumbnail_url or f"/static/icons/{icon_name}.svg"}
    block.child_blocks = {"icon": icon_block}

    value = IconListItemValue(block, [("icon", icon_name), ("text", "<p>hello</p>")])
    return value


class TestIconListItemValue:
    """Tests for IconListItemValue computed properties."""

    def test_icon_name_returns_stored_value(self):
        value = _make_icon_list_item_value("arrow-clockwise")
        assert value.icon_name == "arrow-clockwise"

    def test_icon_name_empty_string(self):
        value = _make_icon_list_item_value("")
        assert value.icon_name == ""

    def test_icon_url_looks_up_from_thumbnail_source(self):
        expected_url = "/static/img/firefox/flare/icons/desktop-16/activity/activity-16.svg"
        value = _make_icon_list_item_value("activity", thumbnail_url=expected_url)
        assert value.icon_url == expected_url

    def test_icon_url_returns_empty_for_unknown_icon(self):
        block = blocks.StructBlock.__new__(blocks.StructBlock)
        icon_block = IconChoiceBlock.__new__(IconChoiceBlock)
        icon_block._thumbnails_source = {"activity": "/some/url.svg"}
        block.child_blocks = {"icon": icon_block}
        value = IconListItemValue(block, [("icon", "unknown"), ("text", "<p>hello</p>")])
        assert value.icon_url == ""

    def test_icon_url_returns_empty_for_empty_icon(self):
        block = blocks.StructBlock.__new__(blocks.StructBlock)
        icon_block = IconChoiceBlock.__new__(IconChoiceBlock)
        icon_block._thumbnails_source = {"activity": "/some/url.svg"}
        block.child_blocks = {"icon": icon_block}
        value = IconListItemValue(block, [("icon", ""), ("text", "<p>hello</p>")])
        assert value.icon_url == ""


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


def test_button_row_block_honours_max_buttons_override():
    block = ButtonRowBlock(max_buttons=5)
    block.clean(_make_button_row_value(5))

    with pytest.raises(StructBlockValidationError):
        block.clean(_make_button_row_value(6))


def test_cards_list_block_passes_max_buttons_down_to_cards():
    """The Referral Hub page raises its cards' button limit to 5 this way."""
    block = CardsListBlock(max_buttons=5)
    card = block.child_blocks["cards"].child_blocks["card"]
    button_row = card.child_blocks["content"].child_blocks["buttons"]

    assert button_row.child_blocks["buttons"].meta.max_num == 5


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


def _make_button_row_raw(count=1, spacing="", alignment="", help_text=""):
    variants = get_button_variants()
    buttons = [dict(variants["primary"], id=f"test-btnrow-{i}") for i in range(count)]
    return {"spacing": spacing, "alignment": alignment, "buttons": buttons, "help_text": help_text}


def _render_button_row(raw_value, rf):
    request = rf.get("/en-US/")
    block = ButtonRowBlock()
    bound = block.to_python(raw_value)
    return block.render(bound, context=_render_context(request))


def test_button_row_renders_center_class_by_default(rf):
    html = _render_button_row(_make_button_row_raw(alignment=""), rf)
    assert "is-center" in html


def test_button_row_renders_start_alignment(rf):
    html = _render_button_row(_make_button_row_raw(alignment="start"), rf)
    assert "is-start" in html


def test_button_row_renders_end_alignment(rf):
    html = _render_button_row(_make_button_row_raw(alignment="end"), rf)
    assert "is-end" in html


@pytest.mark.parametrize("spacing", ["small", "large"])
def test_button_row_renders_spacing_class(spacing, rf):
    html = _render_button_row(_make_button_row_raw(spacing=spacing), rf)
    assert f"fl-buttons-spacing-{spacing}" in html


def test_button_row_no_spacing_class_when_empty(rf):
    html = _render_button_row(_make_button_row_raw(spacing=""), rf)
    assert "fl-buttons-spacing" not in html


def test_button_row_renders_help_text(rf):
    raw = _make_button_row_raw(help_text='<p data-block-key="test">Help text here.</p>')
    html = _render_button_row(raw, rf)
    assert "fl-button-row-help-text" in html
    assert "Help text here." in html


def test_button_row_omits_help_text_div_when_empty(rf):
    html = _render_button_row(_make_button_row_raw(help_text=""), rf)
    assert "fl-button-row-help-text" not in html


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

    top_media = value.get("media", [])
    if top_media:
        top_item = top_media[0]
        if top_item["type"] == "icon":
            icon_wrapper = card_el.find("div", class_="fl-card-media-icon")
            assert icon_wrapper
            icon_name = top_item["value"]
            icon_el = icon_wrapper.find("span", class_="fl-icon")
            assert icon_el and f"fl-icon-{icon_name}" in icon_el.get("class", [])
        elif top_item["type"] == "pictogram":
            pictogram_wrapper = card_el.find("div", class_="fl-card-media-pictogram")
            assert_image_variants_attributes(images_element=pictogram_wrapper, images_value=top_item["value"])
        elif top_item["type"] == "media":
            top_media_el = card_el.find("div", class_="fl-card-top-media")
            assert_media_block(top_media_el, top_item)

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

        elif block_type == "pictogram":
            pictogram_wrapper = card_el.find("div", class_="fl-card-media-pictogram")
            assert_image_variants_attributes(images_element=pictogram_wrapper, images_value=content_item["value"])

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


def test_image_caption_block(minimal_site, placeholder_images, rf):
    index_page = get_blog_index_page()
    image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
    privacy = get_blog_topics()["privacy"]
    privacy_tag = get_blog_tags()["privacy"]
    content = get_blog_article_content(image, image_caption=IMAGE_CAPTION)
    # A second block covers the image variants, which the fixture image doesn't use.
    content.append(
        {
            "type": "image_caption",
            "value": {
                "image": {
                    "image": image.id,
                    "settings": {
                        "dark_mode_image": dark_image.id,
                        "mobile_image": mobile_image.id,
                        "dark_mode_mobile_image": dark_mobile_image.id,
                    },
                },
                "caption": '<p data-block-key="eee55555">Caption below an image with dark mode and mobile variants.</p>',
            },
            "id": "88888888-8888-8888-8888-888888888888",
        }
    )
    article = create_blog_article(
        index_page=index_page,
        title=FEATURED_TITLES[0],
        slug="test-image-caption-article",
        topic=privacy,
        tags=[privacy_tag],
        image=image,
        description=FEATURED_DESCRIPTIONS[0],
        content=content,
    )

    request = rf.get(article.get_full_url())
    response = article.serve(request)
    assert response.status_code == 200

    context = article.get_context(request)
    soup = BeautifulSoup(response.content, "html.parser")
    blocks_data = [block for block in content if block["type"] == "image_caption"]
    figures = soup.find_all("figure", class_="fl-image-caption")
    assert len(figures) == len(blocks_data)

    for figure, block_data in zip(figures, blocks_data):
        assert_image_variants_attributes(
            figure.find("div", class_="image-variants-display"),
            block_data["value"]["image"],
        )

        caption_source = BeautifulSoup(block_data["value"]["caption"], "html.parser")
        figcaption = figure.find("figcaption", class_="fl-image-caption-text")
        assert figcaption
        assert "fl-body" in figcaption["class"]
        assert "fl-body-sm" in figcaption["class"]
        assert figcaption.get_text().strip() == caption_source.get_text().strip()
        # The caption is rendered without its wrapping <p>, but inline rich text formatting is kept.
        assert not figcaption.find("p")
        for tag_name in ("b", "i"):
            assert bool(figcaption.find(tag_name)) == bool(caption_source.find(tag_name))
        expected_link = caption_source.find("a")
        rendered_link = figcaption.find("a")
        assert bool(rendered_link) == bool(expected_link)
        if expected_link:
            assert rendered_link["href"] == add_utm_parameters(context, expected_link["href"])
            assert rendered_link.get_text() == expected_link.get_text()


# Referral controls (inside TabBlock)

REFERRAL_CONTROLS_LABELS = {
    "copy_label": "Grab your link",
    "copy_success_label": "Got it!",
    "email_label": "Send an email",
    "email_subject": "Firefox is worth a look",
    "email_body": "Try this browser. {invite link} Hope you like it.",
    "qr_heading": "QR code",
    "qr_label": "Point a camera at this",
}

# The referral program has two distinct URLs, and the controls must share the
# second one, never the first:
#
#   Hub    /invite/?ref_key=TEST23456X000000            the referrer's private page
#   Invite /get-firefox/?invitation=1ABCDEFGHJKMNPQRS   the link handed to friends
#
# ReferralHubPage.get_context maps ref_key -> invite_url through
# springfield.firefox.referral.crypto: a 16-character Crockford base32 referral
# ID becomes a key-version character plus its FF1 ciphertext. These tests only
# need a code of the right shape -- the real mapping is covered by
# test_referral_pages and the referral crypto tests -- so INVITE_CODE is a
# stand-in rather than a cipher output.
# TEST23456X000000 is a real dummy ref_key from bootstrap_dummy_referral_data.
REFERRAL_HUB_URL = "/invite/?ref_key=TEST23456X000000"
INVITE_CODE = "1ABCDEFGHJKMNPQRS"
INVITE_URL = f"http://testserver/get-firefox/?invitation={INVITE_CODE}"


def _referral_controls_stream(**overrides):
    """The raw stream value for a tab's referral controls, with default labels."""
    return [{"type": "referral_controls", "value": dict(REFERRAL_CONTROLS_LABELS, **overrides)}]


def _tab_value(referral_controls=True, **overrides):
    """Build a TabBlock value.

    ``referral_controls`` takes True for the default labels, False for a tab
    without controls, or an explicit raw stream list to vary a single field.
    """
    raw = {
        "tab_name": "First tab",
        "heading": "<p>Tab heading</p>",
        "description": "<p>Tab description</p>",
        "note": "<p>Tab note</p>",
        "referral_controls": [],
    }
    if referral_controls is True:
        raw["referral_controls"] = _referral_controls_stream()
    elif referral_controls:
        raw["referral_controls"] = referral_controls
    raw.update(overrides)
    return TabBlock().to_python(raw)


_UNSET = object()


def _render_tab(referral_controls=True, invite_url=INVITE_URL, install_count=_UNSET, **overrides):
    """Render a TabBlock.

    ``install_count`` defaults to being absent from the context entirely, which
    is the situation on every page type other than the Referral Hub.
    """
    block = TabBlock()
    value = _tab_value(referral_controls=referral_controls, **overrides)
    context = {"invite_url": invite_url, "section_id": "hub", "tab_index": 1}
    if install_count is not _UNSET:
        context["install_count"] = install_count
    return block.render(value, context=context)


def test_tab_block_renders_referral_controls_with_all_labels():
    soup = BeautifulSoup(_render_tab(), "html.parser")

    controls = soup.find("div", class_="fl-referral-controls")
    assert controls is not None

    copy_button = controls.find("button", attrs={"data-js": "fl-copy-to-clipboard"})
    assert copy_button["data-copy-value"] == INVITE_URL
    assert copy_button["data-label-success"] == REFERRAL_CONTROLS_LABELS["copy_success_label"]
    assert copy_button.find("span", class_="fl-copy-to-clipboard-label").get_text(strip=True) == (REFERRAL_CONTROLS_LABELS["copy_label"])
    assert (
        copy_button.find("span", class_="fl-copy-to-clipboard-label-success").get_text(strip=True) == (REFERRAL_CONTROLS_LABELS["copy_success_label"])
    )

    email_link = controls.find("a", class_="fl-referral-controls-share-email")
    assert REFERRAL_CONTROLS_LABELS["email_label"] in email_link.get_text(strip=True)
    assert email_link["href"].startswith("mailto:?subject=")

    qr_button = controls.find("button", class_="fl-referral-controls-qr-button")
    assert qr_button.get_text(strip=True) == REFERRAL_CONTROLS_LABELS["qr_label"]
    assert controls.find("p", class_="fl-referral-controls-qr-label").get_text(strip=True) == (REFERRAL_CONTROLS_LABELS["qr_label"])
    assert controls.find("h3", class_="fl-heading").get_text(strip=True) == REFERRAL_CONTROLS_LABELS["qr_heading"]


def test_tab_block_referral_controls_qr_button_targets_its_dialog():
    """The QR is behind a dialog, so the trigger has to actually reach it.

    flare-dialogs.es6.js pairs the two by id alone: a trigger whose
    data-target-id matches nothing is a silently dead button, which no
    label or markup assertion would catch.
    """
    controls = BeautifulSoup(_render_tab(), "html.parser").find("div", class_="fl-referral-controls")

    qr_button = controls.find("button", class_="fl-referral-controls-qr-button")
    assert "fl-dialog-trigger" in qr_button["class"]

    dialog = controls.find("dialog", id=qr_button["data-target-id"])
    assert dialog is not None
    assert dialog["aria-label"] == REFERRAL_CONTROLS_LABELS["qr_label"]
    # The code itself is in the dialog, not on the page behind it.
    assert dialog.find("div", class_="fl-referral-controls-qr-code") is not None
    # ...and the dialog can be dismissed once open.
    assert dialog.find("button", class_="fl-dialog-close-button") is not None


def test_tabs_block_renders_a_distinct_qr_dialog_id_per_tab():
    """Two tabs on one page must not share a dialog id.

    flare-dialogs.es6.js resolves a trigger through `getElementById`, which
    returns the first match in the document, so an id that did not vary per tab
    would leave every QR button opening the first tab's dialog. Only TabsBlock
    can show this: the single-tab tests render one instance, where a hardcoded
    id looks perfectly correct.
    """
    block = TabsBlock()
    value = block.to_python(
        {
            "section_id": "hub",
            "tabs": [{"tab_name": name, "referral_controls": _referral_controls_stream()} for name in ("First tab", "Second tab")],
        }
    )
    soup = BeautifulSoup(block.render(value, context={"invite_url": INVITE_URL}), "html.parser")

    # Pair each panel's trigger with the dialog in that same panel, rather than
    # zipping two document-order lists that would line up either way. Keying on
    # the trigger's target collapses the mapping if the tabs share an id.
    targets_to_dialogs = {
        panel.select_one(".fl-referral-controls-qr-button")["data-target-id"]: panel.select_one(".fl-referral-controls dialog")["id"]
        for panel in soup.select(".fl-tab")
    }

    assert len(targets_to_dialogs) == 2
    assert all(target == dialog_id for target, dialog_id in targets_to_dialogs.items())


def _render_tablist(tabs):
    """Render TabsBlock and return its tablist, given raw tab dicts."""
    block = TabsBlock()
    value = block.to_python({"section_id": "hub", "tabs": tabs})
    soup = BeautifulSoup(block.render(value, context={"invite_url": INVITE_URL}), "html.parser")
    return soup.find("div", attrs={"role": "tablist"})


def test_tabs_block_tab_button_renders_its_icon_alongside_the_name():
    tablist = _render_tablist([{"tab_name": "First tab", "icon": "gift"}])

    button = tablist.find("button", attrs={"role": "tab"})
    icon_span = button.find("span", class_="fl-icon")
    assert icon_span and "fl-icon-gift" in icon_span["class"]
    # Decorative only: the tab name is the accessible name, so the icon must not
    # be announced as a second, duplicate label.
    assert icon_span["aria-hidden"] == "true"
    assert button.find("span", class_="fl-tabs-tab-label").get_text(strip=True) == "First tab"


def test_tabs_block_tab_button_omits_the_icon_when_none_is_chosen():
    """The icon is optional, including for tabs saved before the field existed.

    An unchosen IconChoiceBlock stores "", which would otherwise render a bare
    `fl-icon` span: an empty mask box taking up space beside the name.
    """
    tablist = _render_tablist([{"tab_name": "First tab", "icon": ""}, {"tab_name": "Legacy tab"}])

    buttons = tablist.find_all("button", attrs={"role": "tab"})
    assert len(buttons) == 2
    for button in buttons:
        assert button.find("span", class_="fl-icon") is None
    assert [b.get_text(strip=True) for b in buttons] == ["First tab", "Legacy tab"]


def _email_href(html):
    return BeautifulSoup(html, "html.parser").find("a", class_="fl-referral-controls-share-email")["href"]


def _email_params(html):
    """Read the mailto: params the way a mail client does.

    Deliberately percent-decode only, rather than using parse_qs: parse_qs also
    turns "+" into a space, which would mask the difference between RFC 6068
    percent-encoding and form encoding. A mail client treats "+" literally, so a
    body encoded with quote_plus shows up full of plus signs.
    """
    href = _email_href(html)
    # mailto: has no netloc, so the params live in the path; split it by hand.
    query = href.split("?", 1)[1]
    return {key: unquote(raw) for key, raw in (param.split("=", 1) for param in query.split("&"))}


def test_tab_block_referral_controls_email_body_uses_percent_encoded_spaces():
    """Spaces must be %20, never "+", or mail clients render the plus signs."""
    href = _email_href(_render_tab())

    assert "+" not in href
    assert "%20" in href


def test_tab_block_referral_controls_email_href_encodes_subject_and_body():
    params = _email_params(_render_tab())

    assert params["subject"] == REFERRAL_CONTROLS_LABELS["email_subject"]
    # The {invite link} placeholder is replaced in place, keeping the copy
    # written around it on both sides.
    assert params["body"] == f"Try this browser. {INVITE_URL} Hope you like it."


def test_tab_block_referral_controls_email_body_appends_link_when_placeholder_removed():
    """The link must survive an editor deleting the {invite link} placeholder."""
    html = _render_tab(referral_controls=_referral_controls_stream(email_body="Just some copy with no placeholder."))

    assert _email_params(html)["body"] == f"Just some copy with no placeholder.\n\n{INVITE_URL}"


def test_tab_block_referral_controls_email_body_replaces_every_placeholder():
    html = _render_tab(referral_controls=_referral_controls_stream(email_body="{invite link} or later: {invite link}"))

    assert _email_params(html)["body"] == f"{INVITE_URL} or later: {INVITE_URL}"
    assert "{invite link}" not in html


def test_tab_block_referral_controls_email_body_encodes_ampersands_in_the_invite_url():
    """An unencoded & in the body would truncate it and inject a mailto header."""
    invite_url = f"{INVITE_URL}&utm_source=referral"
    html = _render_tab(invite_url=invite_url)
    params = _email_params(html)

    # The whole URL survives, and the body is not cut off at the "&"...
    assert params["body"] == f"Try this browser. {invite_url} Hope you like it."
    # ...nor did the tail leak out as a separate mailto header.
    assert set(params) == {"subject", "body"}


def test_tab_block_referral_controls_qr_code_encodes_invite_url():
    soup = BeautifulSoup(_render_tab(), "html.parser")
    qr = soup.find("div", class_="fl-referral-controls-qr-code")

    # The QR is decorative: the copy button already exposes the link, and the
    # trigger button carries qr_label as its accessible name.
    assert qr["aria-hidden"] == "true"
    assert qr.find("svg") is not None


def test_tab_block_referral_controls_qr_heading_precedes_the_code():
    """The heading introduces the QR code, so it has to come before it.

    The dialog places its heading slot above its body, and the assertion is on
    document order rather than on the slot markup so that restructuring the
    dialog cannot silently drop the heading below the image.
    """
    dialog = BeautifulSoup(_render_tab(), "html.parser").find("dialog")

    heading = dialog.find("h3", class_="fl-heading")
    assert heading.get_text(strip=True) == REFERRAL_CONTROLS_LABELS["qr_heading"]

    svg = dialog.find("div", class_="fl-referral-controls-qr-code").find("svg")
    # find_all_next only walks forwards, so reaching the svg proves the order.
    assert svg in heading.find_all_next("svg")


def test_tab_block_referral_controls_omits_qr_heading_when_blank():
    """qr_heading is optional, and an empty one must not leave an empty <h3>."""
    html = _render_tab(referral_controls=_referral_controls_stream(qr_heading=""))
    dialog = BeautifulSoup(html, "html.parser").find("dialog")

    assert dialog.find("h3") is None
    # ...and the QR code itself is still there.
    assert dialog.find("div", class_="fl-referral-controls-qr-code").find("svg") is not None


def test_tab_block_referral_controls_never_expose_the_hub_url():
    """The controls share the invite link, never the referrer's own hub URL.

    Sharing the hub URL would hand a friend the referrer's private dashboard
    (and their ref_key) instead of a Firefox download page.
    """
    html = _render_tab()
    controls = BeautifulSoup(html, "html.parser").find("div", class_="fl-referral-controls")
    rendered = str(controls)

    assert "ref_key" not in rendered
    assert "/invite/" not in rendered
    assert "TEST23456X000000" not in rendered
    # ...and the invite link is what actually reaches both share affordances.
    # Asserted per affordance rather than as an occurrence count, so that adding
    # or removing a display of the link cannot break this test -- and so the
    # assertions above cannot pass vacuously on controls that rendered nothing.
    assert controls.find("button", attrs={"data-js": "fl-copy-to-clipboard"})["data-copy-value"] == INVITE_URL
    assert INVITE_URL in _email_params(html)["body"]


def test_tab_block_omits_referral_controls_when_not_added():
    soup = BeautifulSoup(_render_tab(referral_controls=False), "html.parser")

    assert soup.find("div", class_="fl-referral-controls") is None


def test_tab_block_renders_when_referral_controls_key_absent_from_stored_json():
    """Tabs saved before referral_controls existed have no such key at all.

    tab.html includes the field unguarded, which is only safe because
    StructBlock.to_python falls back to the child's get_default() for missing
    keys, and an empty StreamValue renders to nothing. Guards against a future
    swap to a plain StructBlock, whose StructValue would always be truthy and
    would start rendering controls on every pre-existing tab.
    """
    block = TabBlock()
    legacy_raw = {
        "tab_name": "Legacy tab",
        "heading": "<p>Legacy heading</p>",
        "description": "<p>Legacy description</p>",
        "note": "<p>Legacy note</p>",
    }
    value = block.to_python(legacy_raw)

    assert len(value["referral_controls"]) == 0

    html = block.render(value, context={"invite_url": INVITE_URL, "section_id": "hub", "tab_index": 1})
    soup = BeautifulSoup(html, "html.parser")

    assert soup.find("div", class_="fl-referral-controls") is None
    # The rest of the panel still renders.
    assert soup.find("p", class_="fl-tab-description").get_text(strip=True) == "Legacy description"


def test_tab_block_omits_referral_controls_when_invite_url_missing():
    """A Referral Hub page opened without ?ref_key= has an empty invite_url."""
    soup = BeautifulSoup(_render_tab(invite_url=""), "html.parser")

    assert soup.find("div", class_="fl-referral-controls") is None
    assert soup.find("button", attrs={"data-js": "fl-copy-to-clipboard"}) is None


def test_tab_block_renders_referral_controls_between_description_and_note():
    soup = BeautifulSoup(_render_tab(), "html.parser")
    panel = soup.find("div", class_="fl-tab")

    order = []
    for child in panel.find_all(["p", "small", "div"], recursive=True):
        classes = child.get("class") or []
        if "fl-tab-description" in classes:
            order.append("description")
        elif "fl-referral-controls" in classes:
            order.append("controls")
        elif "fl-tab-note" in classes:
            order.append("note")

    assert order == ["description", "controls", "note"]


# Impact dashboard / badges (inside TabBlock)


def _badge(number, singular="person", plural="people", badge_name="Connector", message=None):
    """A raw badge dict. ``message`` is left out entirely unless given."""
    badge = {
        "number": number,
        "singular_label": singular,
        "plural_label": plural,
        "badge_name": badge_name,
    }
    if message is not None:
        badge["message"] = message
    return badge


def _impact_dash(badges, locked_summary=None):
    """A raw impact_dash stream value holding one dashboard with these badges.

    ``locked_summary`` defaults to being absent from the stored JSON entirely,
    which is both a dashboard saved before the field existed and one an editor
    left blank.
    """
    value = {"badges": badges}
    if locked_summary is not None:
        value["locked_summary"] = locked_summary
    return [{"type": "impact_dash", "value": value}]


def _render_impact_dash(numbers=(1, 5, 25), install_count=_UNSET, badges=None, locked_summary=None):
    html = _render_tab(
        referral_controls=False,
        install_count=install_count,
        impact_dash=_impact_dash(
            badges if badges is not None else [_badge(n) for n in numbers],
            locked_summary=locked_summary,
        ),
    )
    return BeautifulSoup(html, "html.parser")


def _badge_elements(soup):
    return soup.select("ul.fl-impact-dash li.fl-badge")


def _summary_element(soup):
    return soup.find("p", class_="fl-impact-dash-summary")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 0),
        ("", 0),
        ("abc", 0),
        ([], 0),
        (-5, 0),
        (0, 0),
        (7, 7),
        ("7", 7),
        (7.9, 7),
    ],
)
def test_impact_dash_coerce_count(raw, expected):
    """A missing or junk context value must degrade to 0, never raise."""
    assert ImpactDashBlock._coerce_count(raw) == expected


@pytest.mark.parametrize(
    ("install_count", "number", "is_achieved"),
    [
        (0, 1, False),
        (4, 5, False),
        (5, 5, True),  # the boundary: >= not >
        (6, 5, True),
        (342, 25, True),
    ],
)
def test_impact_dash_badge_achieved_at_threshold_boundary(install_count, number, is_achieved):
    resolved = ImpactDashBlock._badge_context(_badge(number), install_count)

    assert resolved["is_achieved"] is is_achieved


@pytest.mark.parametrize("number", [0, -5, None])
def test_impact_dash_badge_below_one_is_clamped_and_not_achieved(number):
    """Legacy JSON only, but a 0 threshold must not unlock for every visitor."""
    resolved = ImpactDashBlock._badge_context(_badge(number), install_count=0)

    assert resolved["number"] == 1
    assert resolved["is_achieved"] is False
    assert ImpactDashBlock._badge_context(_badge(number), install_count=1)["is_achieved"] is True


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (0, "person"),
        (1, "person"),
        (2, "people"),
        (342, "people"),
    ],
)
def test_impact_dash_label_is_singular_only_for_exactly_one(number, expected):
    """The label agrees with the badge's own number, not the install count."""
    assert ImpactDashBlock._badge_context(_badge(number), install_count=1)["label"] == expected


def test_impact_dash_label_falls_back_to_singular_when_plural_blank():
    """Only reachable via legacy JSON, but must never render a bare number."""
    resolved = ImpactDashBlock._badge_context(_badge(5, plural="  "), install_count=0)

    assert resolved["label"] == "person"


def test_tab_block_renders_one_badge_per_entry_in_order():
    badges = _badge_elements(_render_impact_dash(numbers=(1, 5, 25), install_count=0))

    assert len(badges) == 3
    assert [b.find("span", class_="fl-badge-number").get_text(strip=True) for b in badges] == ["1", "5", "25"]


def test_tab_block_renders_badge_number_and_label():
    badges = _badge_elements(_render_impact_dash(numbers=(1, 5), install_count=0))

    assert badges[0].find("span", class_="fl-badge-label").get_text(strip=True) == "person"
    assert badges[1].find("span", class_="fl-badge-label").get_text(strip=True) == "people"


def test_tab_block_marks_only_achieved_badges():
    """Guards the includecontents bool-prop footgun.

    If is_achieved reached the component as the string "False" it would be
    truthy and every badge would render achieved.
    """
    badges = _badge_elements(_render_impact_dash(numbers=(1, 5, 25), install_count=5))

    assert [b.get("data-achieved") for b in badges] == ["true", "true", "false"]
    assert ["is-achieved" in b["class"] for b in badges] == [True, True, False]


def test_tab_block_impact_dash_locked_when_install_count_absent_from_context():
    """TabBlock is reachable from MediaBlock on pages that never set the count."""
    soup = _render_impact_dash(numbers=(1, 5), install_count=_UNSET)

    assert len(_badge_elements(soup)) == 2
    assert soup.select("li.fl-badge.is-achieved") == []


@pytest.mark.parametrize("install_count", [None, "", "abc"])
def test_tab_block_impact_dash_locked_when_install_count_not_numeric(install_count):
    soup = _render_impact_dash(numbers=(1, 5), install_count=install_count)

    assert soup.select("li.fl-badge.is-achieved") == []


def test_tab_block_omits_impact_dash_when_not_added():
    soup = BeautifulSoup(_render_tab(referral_controls=False, impact_dash=[]), "html.parser")

    assert soup.find("ul", class_="fl-impact-dash") is None


def test_tab_block_renders_when_impact_dash_key_absent_from_stored_json():
    """Tabs saved before impact_dash existed have no such key at all."""
    block = TabBlock()
    value = block.to_python({"tab_name": "Legacy tab", "description": "<p>Legacy description</p>"})

    assert len(value["impact_dash"]) == 0

    html = block.render(value, context={"section_id": "hub", "tab_index": 1})
    soup = BeautifulSoup(html, "html.parser")

    assert soup.find("ul", class_="fl-impact-dash") is None
    assert soup.find("p", class_="fl-tab-description").get_text(strip=True) == "Legacy description"


def test_tab_block_renders_badge_without_image():
    soup = _render_impact_dash(numbers=(5,), install_count=0)

    assert _badge_elements(soup)[0].find("div", class_="fl-badge-media") is None


def test_tab_block_renders_impact_dash_between_referral_controls_and_note():
    html = _render_tab(install_count=5, impact_dash=_impact_dash([_badge(1)]))
    panel = BeautifulSoup(html, "html.parser").find("div", class_="fl-tab")

    order = []
    for child in panel.find_all(["p", "small", "div", "ul"], recursive=True):
        classes = child.get("class") or []
        if "fl-tab-description" in classes:
            order.append("description")
        elif "fl-referral-controls" in classes:
            order.append("controls")
        elif "fl-impact-dash" in classes:
            order.append("impact_dash")
        elif "fl-tab-note" in classes:
            order.append("note")

    assert order == ["description", "controls", "impact_dash", "note"]


@pytest.mark.django_db
def test_tab_block_renders_badge_image(placeholder_images):
    image = placeholder_images[0]
    badges = [{"number": 5, "singular_label": "person", "plural_label": "people", "image": image.pk}]
    soup = _render_impact_dash(install_count=0, badges=badges)

    media = _badge_elements(soup)[0].find("div", class_="fl-badge-media")
    assert media is not None
    # Decorative: the number and label already carry the meaning.
    assert media["aria-hidden"] == "true"

    img = media.find("img", class_="fl-badge-image")
    assert img["alt"] == ""
    assert img["loading"] == "lazy"
    assert "srcset" in img.attrs


def test_tab_block_renders_badge_name_below_the_number_and_label():
    badges = _badge_elements(_render_impact_dash(numbers=(5,), install_count=0))

    name = badges[0].find("p", class_="fl-badge-name")
    assert name.get_text(strip=True) == "Connector"

    description = badges[0].find("div", class_="fl-badge-description")
    children = description.find_all(["p", "div"], recursive=False)
    classes = [c for el in children for c in (el.get("class") or [])]
    assert classes.index("fl-badge-value") < classes.index("fl-badge-name")


def test_tab_block_renders_distinct_badge_name_per_badge():
    badges = _badge_elements(
        _render_impact_dash(
            install_count=0,
            badges=[_badge(1, badge_name="Connector"), _badge(5, badge_name="Supporter")],
        )
    )

    assert [b.find("p", class_="fl-badge-name").get_text(strip=True) for b in badges] == ["Connector", "Supporter"]


def test_tab_block_omits_badge_name_element_when_blank():
    """Blank is only reachable via legacy JSON, but must not leave an empty tag."""
    badges = _badge_elements(_render_impact_dash(install_count=0, badges=[_badge(5, badge_name="   ")]))

    assert badges[0].find("p", class_="fl-badge-name") is None
    # The rest of the badge still renders.
    assert badges[0].find("span", class_="fl-badge-number").get_text(strip=True) == "5"


def test_impact_dash_badge_context_strips_the_badge_name():
    resolved = ImpactDashBlock._badge_context(_badge(5, badge_name="  Supporter  "), install_count=0)

    assert resolved["badge_name"] == "Supporter"


# Impact dashboard summary: one line above the badges, picked by progress


def _summary_source(install_count, badges, locked_summary=""):
    """_summary_source over raw badge dicts, resolved at this install count."""
    resolved = [ImpactDashBlock._badge_context(badge, install_count) for badge in badges]

    return ImpactDashBlock._summary_source({"locked_summary": locked_summary}, resolved)


# Deliberately not in ascending order: the message must be chosen by number, not
# by position in the editor's list.
_MESSAGE_BADGES = [
    _badge(1, message="first friend"),
    _badge(25, message="twenty-five friends"),
    _badge(5, message="five friends"),
]


@pytest.mark.parametrize(
    ("install_count", "expected"),
    [
        (1, "first friend"),
        (4, "first friend"),
        (5, "five friends"),  # the boundary: the 5 badge is unlocked at exactly 5
        (24, "five friends"),
        (25, "twenty-five friends"),
        (342, "twenty-five friends"),  # nothing beyond the top badge to move on to
    ],
)
def test_impact_dash_summary_comes_from_the_furthest_badge_unlocked(install_count, expected):
    assert _summary_source(install_count, _MESSAGE_BADGES) == expected


def test_impact_dash_summary_falls_back_to_locked_summary_when_nothing_unlocked():
    source = _summary_source(0, _MESSAGE_BADGES, locked_summary="Invite your first friend.")

    assert source == "Invite your first friend."


def test_impact_dash_summary_is_empty_when_nothing_unlocked_and_no_locked_summary():
    assert _summary_source(0, _MESSAGE_BADGES) == ""


def test_impact_dash_summary_is_empty_when_the_unlocked_badge_has_no_message():
    """Blank means silence, not the locked copy, which would deny the milestone."""
    badges = [_badge(1, message="first friend"), _badge(5, message="   ")]

    assert _summary_source(5, badges, locked_summary="Invite your first friend.") == ""


def test_impact_dash_summary_prefers_the_first_of_duplicate_thresholds():
    """Two badges at the same number is editor error, but must be deterministic."""
    badges = [_badge(5, message="first five"), _badge(5, message="second five")]

    assert _summary_source(5, badges) == "first five"


def test_impact_dash_summary_ignores_messages_on_still_locked_badges():
    badges = [_badge(1, message="first friend"), _badge(5, message="five friends")]

    assert _summary_source(1, badges) == "first friend"


@pytest.mark.parametrize("raw", [None, "", "   ", "\n"])
def test_impact_dash_resolve_summary_is_empty_when_not_filled_in(raw):
    assert ImpactDashBlock._resolve_summary(raw, install_count=5) == ""


def test_impact_dash_resolve_summary_replaces_every_token():
    resolved = ImpactDashBlock._resolve_summary("{install count} down, {install count} to go", install_count=7)

    assert resolved == "7 down, 7 to go"


def test_impact_dash_resolve_summary_keeps_copy_without_the_token():
    """The token is optional: nothing is appended, unlike the invite link."""
    assert ImpactDashBlock._resolve_summary("Thanks for spreading the word.", install_count=7) == "Thanks for spreading the word."


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("{install_count}", "{install_count}"),  # underscored: not the token
        ("{installs}", "{installs}"),
        ("{ install count }", "{ install count }"),
        ("100% of {install count} friends", "100% of 7 friends"),
        ("{{install count}}", "{7}"),
    ],
)
def test_impact_dash_resolve_summary_leaves_other_braces_alone(raw, expected):
    """A literal replace, so stray braces cannot raise the way str.format would."""
    assert ImpactDashBlock._resolve_summary(raw, install_count=7) == expected


def test_impact_dash_resolve_summary_substitutes_zero():
    """A referrer with no installs yet still gets a sentence, not a blank."""
    assert ImpactDashBlock._resolve_summary("You have {install count} installs", install_count=0) == "You have 0 installs"


def test_tab_block_renders_the_unlocked_badge_message_with_the_count_substituted():
    soup = _render_impact_dash(
        install_count=342,
        badges=[
            _badge(1, message="Off the mark with {install count}."),
            _badge(25, message="You have helped {install count} people switch to Firefox."),
        ],
        locked_summary="Invite your first friend.",
    )

    assert _summary_element(soup).get_text(strip=True) == "You have helped 342 people switch to Firefox."


def test_tab_block_renders_the_locked_summary_before_any_badge_is_unlocked():
    soup = _render_impact_dash(
        install_count=0,
        badges=[_badge(1, message="first friend")],
        locked_summary="Nobody yet -- invite your first friend.",
    )

    assert _summary_element(soup).get_text(strip=True) == "Nobody yet -- invite your first friend."


def test_tab_block_renders_the_locked_summary_when_install_count_absent_from_context():
    """TabBlock is reachable from MediaBlock on pages that never set the count."""
    soup = _render_impact_dash(
        install_count=_UNSET,
        badges=[_badge(1, message="first friend")],
        locked_summary="{install count} so far",
    )

    assert _summary_element(soup).get_text(strip=True) == "0 so far"


def test_tab_block_omits_summary_element_when_the_chosen_message_is_blank():
    soup = _render_impact_dash(numbers=(1, 5), install_count=5, locked_summary="   ")

    assert _summary_element(soup) is None
    # The badges are unaffected by there being no message to show.
    assert len(_badge_elements(soup)) == 2


def test_tab_block_renders_impact_dash_saved_before_the_message_fields_existed():
    soup = _render_impact_dash(numbers=(1, 5), install_count=5)

    assert _summary_element(soup) is None
    assert len(_badge_elements(soup)) == 2


def test_tab_block_renders_summary_above_the_badge_list():
    html = _render_tab(
        referral_controls=False,
        install_count=5,
        impact_dash=_impact_dash([_badge(1, message="{install count} installs")]),
    )
    panel = BeautifulSoup(html, "html.parser").find("div", class_="fl-tab")

    order = [c for el in panel.find_all(["p", "ul"]) for c in (el.get("class") or []) if c in {"fl-impact-dash-summary", "fl-impact-dash"}]
    assert order == ["fl-impact-dash-summary", "fl-impact-dash"]


def test_tab_block_does_not_render_the_message_on_the_badge_itself():
    """The message is the dashboard's summary line, not badge copy."""
    soup = _render_impact_dash(install_count=5, badges=[_badge(5, message="five friends")])

    assert "five friends" not in _badge_elements(soup)[0].get_text()


def test_tab_block_escapes_html_typed_into_a_message():
    """A CharBlock is plain text; markup in it must never reach the DOM as markup."""
    soup = _render_impact_dash(install_count=5, badges=[_badge(5, message="<b>{install count}</b> installs")])

    summary = _summary_element(soup)
    assert summary.find("b") is None
    assert summary.get_text(strip=True) == "<b>5</b> installs"


def test_impact_dash_badge_context_strips_the_message():
    resolved = ImpactDashBlock._badge_context(_badge(5, message="  five friends  "), install_count=5)

    assert resolved["message"] == "five friends"


# Comparison table (inside TabBlock)


def _tab_comparison_table():
    """A raw comparison_table stream value holding one table."""
    return [get_comparison_table_variants()[0]]


def test_tab_block_renders_comparison_table():
    html = _render_tab(referral_controls=False, comparison_table=_tab_comparison_table())
    wrapper = BeautifulSoup(html, "html.parser").find("div", class_="fl-comparison-table-wrapper")

    assert wrapper is not None
    assert_comparison_table(wrapper, _tab_comparison_table()[0])


def test_tab_block_omits_comparison_table_when_not_added():
    soup = BeautifulSoup(_render_tab(referral_controls=False, comparison_table=[]), "html.parser")

    assert soup.find("div", class_="fl-comparison-table-wrapper") is None


def test_tab_block_renders_when_comparison_table_key_absent_from_stored_json():
    """Tabs saved before comparison_table existed have no such key at all."""
    block = TabBlock()
    value = block.to_python({"tab_name": "Legacy tab", "description": "<p>Legacy description</p>"})

    assert len(value["comparison_table"]) == 0

    soup = BeautifulSoup(block.render(value, context={"section_id": "hub", "tab_index": 1}), "html.parser")

    assert soup.find("div", class_="fl-comparison-table-wrapper") is None
    assert soup.find("p", class_="fl-tab-description").get_text(strip=True) == "Legacy description"
