# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.template.loader import render_to_string

import pytest
from bs4 import BeautifulSoup
from wagtail.documents.models import Document
from wagtail.images.jinja2tags import srcset_image
from wagtail.models import Page

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_button_variants, get_buttons_test_page
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
)
from springfield.cms.fixtures.inline_notification_fixtures import get_inline_notification_test_page, get_inline_notification_variants
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page, get_intro_variants
from springfield.cms.fixtures.media_content_fixtures import (
    get_media_content_test_page,
    get_section_with_media_content_variants,
)
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page, get_subscription_variants
from springfield.cms.models import SpringfieldImage
from springfield.cms.templatetags.cms_tags import add_utm_parameters
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
        superheading = section_element.find("span", class_="fl-superheading")
        assert superheading and superheading_text in superheading.get_text()

    if subheading_text:
        subheading = section_element.find("p", class_="fl-subheading")
        assert subheading and subheading_text in subheading.get_text()


def assert_light_dark_image_attributes(
    images_element: BeautifulSoup,
    image: SpringfieldImage,
    is_dark: bool = False,
):
    """
    Compares the rendered image element with the expected image data.
    The is_dark flag indicates if the image is a dark mode image.
    """
    class_name = "display-dark" if is_dark else "display-light"
    assert images_element
    img_tag = images_element.find("img", class_=class_name)
    assert img_tag

    rendered_image = srcset_image(
        image,
        "width-{200,400,600,800,1000,1200,1400}",
        **{
            "sizes": "(min-width: 768px) 50vw, (min-width: 1440px) 680px, 100vw",
            "width": image.width,
            "loading": "lazy",
            "class": class_name,
        },
    )
    image_soup = BeautifulSoup(str(rendered_image), "html.parser").find("img")
    assert img_tag["alt"] == image_soup["alt"]
    assert img_tag["class"] == image_soup["class"]
    assert img_tag["loading"] == image_soup["loading"]
    assert img_tag["width"] == image_soup["width"]
    assert img_tag["src"] == image_soup["src"]


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

    image, dark_image = placeholder_images

    for index, intro in enumerate(intros):
        div = intro_divs[index]

        # Heading
        heading_block = intro["value"]["heading"]
        assert_section_heading_attributes(section_element=div, heading_data=heading_block, index=index)

        heading_text = BeautifulSoup(heading_block["heading_text"], "html.parser").get_text()

        # Buttons
        button = intro["value"]["buttons"][0]
        button_element = div.find("a", class_="fl-button")
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
        if intro["value"]["image"]:
            images_element = div.find("div", class_="fl-intro-media")
            assert_light_dark_image_attributes(images_element=images_element, image=image, is_dark=False)

        if intro["value"]["dark_image"]:
            images_element = div.find("div", class_="fl-intro-media")
            assert_light_dark_image_attributes(images_element=images_element, image=dark_image, is_dark=True)


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

        superheading = section.find("span", class_="fl-superheading")
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

    image, dark_image = placeholder_images

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

        assert_light_dark_image_attributes(images_element=media_element, image=image, is_dark=False)
        assert_light_dark_image_attributes(images_element=media_element, image=dark_image, is_dark=True)
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
        card_list_div = section_element.find("div", class_="fl-grid")
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
        card_list_div = section_element.find("div", class_="fl-grid")
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

    image, dark_image = placeholder_images

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
        card_list_div = section_element.find("div", class_="fl-grid")
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
            images_element = card_element.find("div", class_="light-dark-display")
            assert_light_dark_image_attributes(
                images_element=images_element,
                image=image,
                is_dark=False,
            )
            assert_light_dark_image_attributes(
                images_element=images_element,
                image=dark_image,
                is_dark=True,
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

    image, dark_image = placeholder_images

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
        card_list_div = section_element.find("div", class_="fl-grid")
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
            superheading = card_element.find("span", class_="fl-superheading")
            assert superheading and superheading.get_text().strip() == f"Step {(card_index + 1):>02}"
            images_element = card_element.find("div", class_="light-dark-display")
            assert_light_dark_image_attributes(
                images_element=images_element,
                image=image,
                is_dark=False,
            )
            assert_light_dark_image_attributes(
                images_element=images_element,
                image=dark_image,
                is_dark=True,
            )


def test_buttons(index_page, rf):
    test_page = get_buttons_test_page()
    button_variants = get_button_variants(full=True)

    # Page renders
    request = rf.get(test_page.get_full_url())
    response = test_page.serve(request)
    assert response.status_code == 200

    context = test_page.get_context(request)
    content = response.content
    soup = BeautifulSoup(content, "html.parser")

    main = soup.find("main", class_="fl-main")
    button_elements = main.find_all("a", class_="fl-button")
    tested_buttons = [
        button_variants["external_mozilla"],
        button_variants["external_mozilla_new_tab"],
        button_variants["external_other"],
        button_variants["external_other_new_tab"],
        button_variants["page"],
        button_variants["page_new_tab"],
        button_variants["fxa"],
        button_variants["document"],
        button_variants["email"],
        button_variants["phone"],
    ]

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
