# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.template.loader import render_to_string

import pytest
from bs4 import BeautifulSoup
from wagtail.documents.models import Document
from wagtail.images.jinja2tags import image, srcset_image
from wagtail.models import Page

from lib.l10n_utils import get_locale
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
from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_blocks, get_buttons_test_page
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
from springfield.cms.fixtures.homepage_fixtures import (
    get_card_gallery,
    get_cards_list,
    get_home_carousel,
    get_home_intro,
    get_home_test_page,
    get_kit_banner,
    get_showcase_variants,
)
from springfield.cms.fixtures.inline_notification_fixtures import get_inline_notification_test_page, get_inline_notification_variants
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page, get_intro_variants
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page, get_kit_banner_variants
from springfield.cms.fixtures.media_content_fixtures import (
    get_media_content_test_page,
    get_section_with_media_content_variants,
)
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_snippet
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page, get_subscription_variants
from springfield.cms.models import ArticleDetailPage, SpringfieldImage
from springfield.cms.templatetags.cms_tags import add_utm_parameters
from springfield.firefox.firefox_details import firefox_desktop
from springfield.firefox.templatetags.misc import fxa_button

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture
def placeholder_images():
    return get_placeholder_images()


@pytest.fixture
def index_page(minimal_site):
    return get_test_index_page()


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
        checkbox_label = button_element.find_previous_sibling("label", class_="default-browser-label hidden")
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
    corners = tag_data["value"]["corners"]
    color = tag_data["value"]["color"]

    assert title in tag_element.get_text()
    if color:
        assert f"fl-tag-{color}" in tag_element["class"]
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
    widths: str = "width-{200,400,600,800,1000,1200,1400}",
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
):
    headline_text = BeautifulSoup(card_data["value"]["headline"], "html.parser").get_text()
    content_text = BeautifulSoup(card_data["value"]["content"], "html.parser").get_text()

    headline = card_element.find(class_="fl-heading")
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
        content_text = BeautifulSoup(media_content["value"]["content"], "html.parser").get_text()

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

        # Tags
        tags = media_content["value"]["tags"]
        tag_elements = div.find("div", class_="fl-mediacontent-tags").find_all("span", class_="fl-tag")
        assert len(tag_elements) == len(tags)
        for index, tag in enumerate(tags):
            tag_element = tag_elements[index]
            assert_tag_attributes(tag_element, tag)


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
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
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
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
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
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
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
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-cards_list.card-{card_index + 1}.button-1",
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
            assert_card_attributes(
                card_element=card_element,
                card_data=card,
                context=context,
                cta_position=f"block-{list_index + 1}-section.item-1-step_cards.card-{card_index + 1}.button-1",
            )
            superheading = card_element.find("p", class_="fl-superheading")
            assert superheading and superheading.get_text().strip() == f"Step {(card_index + 1):>02}"
            images_element = card_element.find("div", class_="image-variants-display")
            assert images_element

            spec = "width-{200,400,600,800,1000,1200,1400}"
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

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    main = soup.find("main", class_="fl-main")
    button_elements = main.find_all("a", class_="fl-button")
    blocks = get_button_blocks()
    tested_buttons = []
    for block in blocks:
        tested_buttons.extend(block["value"]["buttons"])

    for index, button_element in enumerate(button_elements):
        button_data = tested_buttons[index]
        if button_data["type"] == "button":
            assert_button_attributes(
                button_element=button_element,
                button_data=button_data,
                context=context,
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
                    "data-cta-text": "Mozilla Account Button - Log in to Mozilla Account",
                    "data-cta-position": "block-4-intro.button-1",
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
    context = test_page.get_context(request)
    soup = BeautifulSoup(content, "html.parser")

    pre_footer_cta = get_pre_footer_cta_snippet()

    cta_element = soup.find("div", class_="fl-pre-footer-cta")
    assert cta_element

    link_element = cta_element.find("a", class_="fl-pre-footer-cta-button")
    assert link_element

    assert link_element.get_text().strip() == pre_footer_cta.label.strip()
    assert link_element["href"] == add_utm_parameters(context, pre_footer_cta.link)
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
            "width-{200,400,600,800,1000,1200,1400}",
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
            "width-{200,400,600,800,1000,1200,1400}",
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

        image_id = overrides.get("image") or article.sticker.id
        img = image_ids[image_id]
        rendered_icon = image(img, "width-400").img_tag()
        sticker_element = card_element.find("img")
        assert sticker_element.prettify() == BeautifulSoup(rendered_icon, "html.parser").find("img").prettify()


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
        "width-{200,400,600,800,1000,1200,1400}",
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
    article = articles[3]
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
