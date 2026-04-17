# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.conf import settings

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.smart_window_page_fixtures import (
    get_smart_window_illustration_cards,
    get_smart_window_line_cards,
    get_smart_window_sliding_carousel,
    get_smart_window_test_page,
    get_smart_window_testimonial_cards,
)


@pytest.fixture
def smart_window_page(index_page, placeholder_images):
    return get_smart_window_test_page()


@pytest.mark.django_db
def test_smart_window_page_not_firefox(smart_window_page, rf):
    """Not-Firefox branch (in supported geo): shows download button, copy link, and post-download instructions."""
    page = smart_window_page
    page.show_smart_window_button = "all"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Hero: heading and featured image
    assert soup.find("h1", class_="fl-heading")
    assert soup.find("div", class_="fl-smart-window-intro-featured-image")

    # Download Firefox button
    download_btn = soup.find("a", {"data-cta-position": "intro-download"})
    assert download_btn
    assert download_btn.get_text(strip=True) == page.download_button_label
    assert download_btn["data-cta-uid"] == str(page.intro_download_button_uid)
    assert download_btn["data-cta-text"] == page.download_button_label

    # Copy-to-clipboard button
    copy_btns = soup.find_all("button", {"data-js": "fl-copy-to-clipboard"})
    assert len(copy_btns) >= 1
    copy_btn = copy_btns[0]
    assert copy_btn.find("span", class_="fl-copy-to-clipboard-label").get_text(strip=True) == page.copy_to_clipboard_label
    assert copy_btn["data-label-success"] == page.copy_success_label
    assert copy_btn["data-copy-value"]  # should be the page URL

    # Post-download instructions
    post_download_els = soup.find_all("p", class_="fl-post-download-instructions")
    assert len(post_download_els) >= 1
    post_download_text = BeautifulSoup(page.post_download_instructions, "html.parser").get_text()
    assert post_download_text in post_download_els[0].get_text()


@pytest.mark.django_db
def test_smart_window_page_firefox_old(smart_window_page, rf):
    """Firefox < 150 branch: shows update instructions, update button, copy link, and post-download instructions."""
    page = smart_window_page
    page.show_smart_window_button = "all"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Update container: rendered by <include:conditional-display max_version="149">
    # which produces a div.conditional-display.condition-fx-version with data-max-version
    update_container = soup.find("div", attrs={"data-max-version": True})
    assert update_container

    # Update instructions text
    update_instructions_el = update_container.find("p", class_="fl-update-instructions")
    assert update_instructions_el
    update_instructions_text = BeautifulSoup(page.update_instructions, "html.parser").get_text()
    assert update_instructions_text in update_instructions_el.get_text()

    # Update button
    update_btn = update_container.find("a", {"data-cta-position": "intro-update"})
    assert update_btn
    assert update_btn.get_text(strip=True) == page.update_button_label
    assert update_btn["href"] == page.update_link

    # Copy-to-clipboard in update branch
    update_copy_btn = update_container.find("button", {"data-js": "fl-copy-to-clipboard"})
    assert update_copy_btn
    assert update_copy_btn.find("span", class_="fl-copy-to-clipboard-label").get_text(strip=True) == page.copy_to_clipboard_label
    assert update_copy_btn["data-label-success"] == page.copy_success_label

    # Post-download instructions in update branch
    update_post_instructions_el = update_container.find("p", class_="fl-post-download-instructions")
    assert update_post_instructions_el
    post_download_text = BeautifulSoup(page.post_download_instructions, "html.parser").get_text()
    assert post_download_text in update_post_instructions_el.get_text()


@pytest.mark.django_db
def test_smart_window_page_firefox_new(smart_window_page, rf):
    """Firefox >= 150 branch: shows UITour buttons (nav + intro), no form."""
    page = smart_window_page
    page.show_smart_window_button = "all"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # No newsletter form in this state
    assert not soup.find("form", {"data-testid": "newsletter-form"})

    uitour_buttons = soup.find_all("button", attrs={"data-cta-uid": True})
    uitour_by_id = {btn["data-cta-uid"]: btn for btn in uitour_buttons}

    # Nav UITour button
    nav_btn = uitour_by_id.get(str(page.nav_button_uid))
    assert nav_btn
    assert nav_btn["data-cta-position"] == "nav"
    assert nav_btn.get_text(strip=True) == page.waitlist_button_label

    # Intro UITour button
    intro_btn = uitour_by_id.get(str(page.intro_button_uid))
    assert intro_btn
    assert intro_btn["data-cta-position"] == "intro-smart-window"
    assert intro_btn.get_text(strip=True) == page.waitlist_button_label


@pytest.mark.django_db
def test_smart_window_page_waitlist_form(smart_window_page, rf):
    """Waitlist form branch (show_smart_window_button="never"): form fields and feedback elements."""
    page = smart_window_page
    page.show_smart_window_button = "never"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    form = soup.find("form", {"data-testid": "newsletter-form"})
    assert form
    assert form["id"] == "newsletter-form"
    assert settings.BASKET_SUBSCRIBE_URL in form["action"]

    # Newsletter id hidden checkbox
    newsletter_checkbox = form.find("input", {"name": "newsletters", "type": "checkbox"})
    assert newsletter_checkbox
    assert newsletter_checkbox["value"] == "smart-window-waitlist"

    # Language hidden input
    lang_input = form.find("input", {"id": "id_lang", "name": "lang"})
    assert lang_input
    assert lang_input["value"] == "en"

    # Email input
    email_input = form.find("input", {"data-testid": "newsletter-email-input"})
    assert email_input
    assert email_input["name"] == "email"
    assert email_input["type"] == "email"

    # Thanks message (hidden by default)
    thanks = soup.find(attrs={"data-testid": "newsletter-thanks-message"})
    assert thanks
    assert "hidden" in thanks.get("class", [])

    # Error message (hidden by default)
    error = soup.find(attrs={"data-testid": "newsletter-error-message"})
    assert error
    assert "hidden" in error.get("class", [])


@pytest.mark.django_db
def test_smart_window_page_content_blocks(smart_window_page, rf):
    """Page content blocks: sliding carousel, line cards, illustration cards, testimonial cards."""
    carousel_fixture = get_smart_window_sliding_carousel()
    line_cards_fixture = get_smart_window_line_cards()
    illustration_cards_fixture = get_smart_window_illustration_cards()
    testimonial_cards_fixture = get_smart_window_testimonial_cards()
    page = smart_window_page
    page.show_smart_window_button = "never"
    request = rf.get(page.get_full_url())
    response = page.serve(request)

    soup = BeautifulSoup(response.content, "html.parser")
    content_region = soup.find("div", class_="fl-split-page-lower")
    assert content_region

    # Sliding carousel: 3 slides
    carousel_el = content_region.find("div", class_="fl-sliding-carousel")
    assert carousel_el
    slides_data = carousel_fixture["value"]["slides"]
    controls = carousel_el.find_all("li", class_="fl-sliding-carousel-control")
    slide_panels = carousel_el.find_all("div", class_="fl-sliding-carousel-slide")
    assert len(controls) == len(slides_data) == 3
    assert len(slide_panels) == 3

    for i, slide in enumerate(slides_data):
        heading_text = BeautifulSoup(slide["value"]["heading"]["heading_text"], "html.parser").get_text()
        heading_el = controls[i].find(class_="fl-sliding-carousel-heading-text")
        assert heading_el and heading_text in heading_el.get_text()

    # Line cards: 2 cards, no buttons
    article_list = content_region.find("div", class_="fl-stacked-article-list")
    assert article_list
    card_els = article_list.find_all("article", class_="fl-article-item")
    line_cards_data = line_cards_fixture["value"]["cards"]
    assert len(card_els) == len(line_cards_data) == 2

    for i, card in enumerate(line_cards_data):
        headline_text = BeautifulSoup(card["value"]["headline"], "html.parser").get_text()
        assert headline_text in card_els[i].get_text()
        assert not card_els[i].find("a", class_="fl-button")

    # Illustration and testimonial cards render in fl-card-grid
    card_grids = content_region.find_all("div", class_="fl-card-grid")
    assert len(card_grids) == 2

    illustration_cards_data = illustration_cards_fixture["value"]["cards"]
    illustration_grid = card_grids[0]
    illustration_card_els = illustration_grid.find_all("article")
    assert len(illustration_card_els) == len(illustration_cards_data) == 3

    for i, card in enumerate(illustration_cards_data):
        headline_text = BeautifulSoup(card["value"]["headline"], "html.parser").get_text()
        assert headline_text in illustration_card_els[i].get_text()

    testimonial_cards_data = testimonial_cards_fixture["value"]["cards"]
    testimonial_grid = card_grids[1]
    assert "fl-card-grid-scroll" in testimonial_grid.get("class", [])
    testimonial_card_els = testimonial_grid.find_all("article", class_="fl-testimonial-card")
    assert len(testimonial_card_els) == len(testimonial_cards_data) == 6

    for i, card in enumerate(testimonial_cards_data):
        attribution_text = BeautifulSoup(card["value"]["attribution"], "html.parser").get_text()
        assert attribution_text in testimonial_card_els[i].get_text()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "show_button,country,expected",
    [
        ("all", "US", True),
        ("all", "DE", True),
        ("all", None, True),
        ("allowed_territories", "US", True),
        ("allowed_territories", "CA", True),
        ("allowed_territories", "DE", False),
        ("allowed_territories", None, False),
        ("never", "US", False),
        ("never", None, False),
    ],
)
def test_smart_window_show_try_smart_window(smart_window_page, rf, show_button, country, expected):
    page = smart_window_page
    page.show_smart_window_button = show_button

    with mock.patch("springfield.cms.models.pages.get_country_from_request", return_value=country):
        request = rf.get(page.get_full_url())
        response = page.serve(request)

    soup = BeautifulSoup(response.content, "html.parser")

    form = soup.find("form", {"data-testid": "newsletter-form"})
    nav_button = soup.find("button", {"data-cta-uid": str(page.nav_button_uid)})
    intro_button = soup.find("button", {"data-cta-uid": str(page.intro_button_uid)})

    if expected:
        assert nav_button, f"Expected nav UITour button for show_button={show_button!r}, country={country!r}"
        assert intro_button, f"Expected intro UITour button for show_button={show_button!r}, country={country!r}"
        assert not form, f"Expected no form for show_button={show_button!r}, country={country!r}"
    else:
        assert form, f"Expected form for show_button={show_button!r}, country={country!r}"
        assert not nav_button, f"Expected no nav UITour button for show_button={show_button!r}, country={country!r}"
        assert not intro_button, f"Expected no intro UITour button for show_button={show_button!r}, country={country!r}"
