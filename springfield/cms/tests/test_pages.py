# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.conf import settings

import pytest
from bs4 import BeautifulSoup

from springfield.cms.blocks import UI_TOUR_CLASSES, UITOUR_BUTTON_SMART_WINDOW
from springfield.cms.fixtures.smart_window_page_fixtures import (
    get_smart_window_illustration_cards,
    get_smart_window_line_cards,
    get_smart_window_sliding_carousel,
    get_smart_window_test_page,
    get_smart_window_testimonial_cards,
)
from springfield.cms.models import FreeFormPage2026, SmartWindowExplainerPage, SmartWindowPage


@pytest.fixture
def smart_window_page(index_page, placeholder_images) -> SmartWindowPage:
    return get_smart_window_test_page()


@pytest.fixture
def free_form_2026_page(minimal_site) -> FreeFormPage2026:
    root_page = minimal_site.root_page
    page = FreeFormPage2026(slug="test-stub-attribution", title="Test Stub Attribution Page")
    root_page.add_child(instance=page)
    page.save_revision().publish()
    return page


# FreeFormPage2026 Navigation Options


@pytest.mark.django_db
@pytest.mark.parametrize("show_navigation", [True, False])
def test_show_navigation(free_form_2026_page: FreeFormPage2026, rf, show_navigation):
    page = free_form_2026_page
    page.show_navigation = show_navigation

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    header = soup.find("header", class_="fl-header")
    assert header

    assert ("fl-header-no-menu" in header.get("class", [])) == (not show_navigation)
    assert bool(soup.find("nav", class_="fl-nav")) == show_navigation


@pytest.mark.django_db
@pytest.mark.parametrize("show_nav_cta", [True, False])
def test_show_nav_cta(free_form_2026_page: FreeFormPage2026, rf, show_nav_cta):
    page = free_form_2026_page
    page.show_nav_cta = show_nav_cta

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    nav_cta_wraps = soup.find_all("div", class_="nav-cta-wrap")
    assert nav_cta_wraps

    for nav_cta_wrap in nav_cta_wraps:
        assert ("hide-cta-on-desktop" in nav_cta_wrap.get("class", [])) == (not show_nav_cta)


# Stub Attribution Campaign


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mode,value,expected_attr",
    [
        ("default", "my-campaign", "data-stub-attribution-campaign"),
        ("override", "my-campaign", "data-stub-attribution-campaign-override"),
        ("force", "my-campaign", "data-stub-attribution-campaign-force"),
    ],
)
def test_stub_attribution_html_attribute(free_form_2026_page: FreeFormPage2026, rf, mode, value, expected_attr):
    """Each mode renders exactly one data-stub-attribution-* attribute on <html>."""
    page = free_form_2026_page
    page.stub_attr_utm_campaign_mode = mode
    page.stub_attr_utm_campaign_value = value

    response = page.serve(rf.get(page.get_full_url()))
    assert response.status_code == 200

    html_el = BeautifulSoup(response.content, "html.parser").find("html")
    all_attrs = {
        "data-stub-attribution-campaign",
        "data-stub-attribution-campaign-override",
        "data-stub-attribution-campaign-force",
    }
    assert html_el.get(expected_attr) == value
    for other in all_attrs - {expected_attr}:
        assert html_el.get(other) is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mode,value",
    [
        ("override", ""),  # value missing
        ("", "my-campaign"),  # mode missing
        ("", ""),  # neither set
    ],
)
def test_stub_attribution_not_rendered_when_incomplete(free_form_2026_page: FreeFormPage2026, rf, mode, value):
    """No stub-attribution attribute is added unless both mode and value are present."""
    page = free_form_2026_page
    page.stub_attr_utm_campaign_mode = mode
    page.stub_attr_utm_campaign_value = value

    response = page.serve(rf.get(page.get_full_url()))
    html_el = BeautifulSoup(response.content, "html.parser").find("html")
    assert html_el.get("data-stub-attribution-campaign") is None
    assert html_el.get("data-stub-attribution-campaign-override") is None
    assert html_el.get("data-stub-attribution-campaign-force") is None


@pytest.mark.django_db
def test_get_utm_campaign_uses_stub_value(free_form_2026_page: FreeFormPage2026):
    page = free_form_2026_page
    page.stub_attr_utm_campaign_mode = "override"
    page.stub_attr_utm_campaign_value = "my-campaign"
    assert page.get_utm_campaign() == "my-campaign"


@pytest.mark.django_db
def test_get_utm_campaign_falls_back_to_slug(free_form_2026_page: FreeFormPage2026):
    page = free_form_2026_page
    assert page.get_utm_campaign() == page.slug


# Smart Window Page


@pytest.mark.django_db
def test_smart_window_page_not_firefox_in_supported_geo(smart_window_page: SmartWindowPage, rf):
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

    # Intro Download Firefox button
    download_btn = soup.find("a", {"data-cta-position": "intro-download"})
    assert download_btn
    assert download_btn.get_text(strip=True) == page.download_button_label
    assert download_btn["data-cta-uid"] == str(page.intro_download_button_uid)
    assert download_btn["data-cta-text"] == page.download_button_label

    # Nav Download Firefox button
    download_btn = soup.find("a", {"data-cta-position": "nav"})
    assert download_btn
    assert download_btn.get_text(strip=True) == page.download_button_label
    assert download_btn["data-cta-uid"] == str(page.nav_download_button_uid)
    assert download_btn["data-cta-text"] == page.download_button_label

    # Copy-to-clipboard button
    copy_btns = soup.find_all("button", {"data-js": "fl-copy-to-clipboard"})
    assert len(copy_btns) >= 1
    copy_btn = copy_btns[0]
    assert copy_btn.find("span", class_="fl-copy-to-clipboard-label").get_text(strip=True) == page.copy_to_clipboard_label
    assert copy_btn["data-label-success"] == page.copy_success_label
    assert copy_btn["data-copy-value"] == page.get_full_url()

    # Post-download instructions
    post_download_els = soup.find_all("p", class_="fl-post-download-instructions")
    assert len(post_download_els) >= 1
    post_download_text = BeautifulSoup(page.post_download_instructions, "html.parser").get_text()
    assert post_download_text in post_download_els[0].get_text()


@pytest.mark.django_db
def test_smart_window_page_not_firefox_in_unsupported_geo(smart_window_page: SmartWindowPage, rf):
    """Not-Firefox branch (in unsupported geo): shows waitlist form."""
    page = smart_window_page
    page.show_smart_window_button = "never"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # Hero: heading and featured image
    assert soup.find("h1", class_="fl-heading")
    assert soup.find("div", class_="fl-smart-window-intro-featured-image")

    # Download Firefox button
    download_btn = soup.find("a", {"data-cta-position": "intro-download"})
    assert not download_btn

    # Copy-to-clipboard button
    copy_btns = soup.find_all("button", {"data-js": "fl-copy-to-clipboard"})
    assert not copy_btns

    # Post-download instructions
    post_download_els = soup.find_all("p", class_="fl-post-download-instructions")
    assert not post_download_els

    # Waitlist form
    form = soup.find("form", {"data-testid": "newsletter-form"})
    assert form
    assert form["action"] == settings.BASKET_SUBSCRIBE_URL
    newsletter_checkbox = form.find("input", {"name": "newsletters", "type": "checkbox"})
    assert newsletter_checkbox
    assert newsletter_checkbox["value"] == "smart-window-waitlist"


@pytest.mark.django_db
def test_smart_window_page_firefox_old(smart_window_page: SmartWindowPage, rf):
    """Firefox <= 149 branch: shows update instructions, update button, copy link, and post-download instructions."""
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
def test_smart_window_page_firefox_new(smart_window_page: SmartWindowPage, rf):
    """Firefox >= 150 branch: shows UITour buttons (nav + intro), no form."""
    page = smart_window_page
    page.show_smart_window_button = "all"
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")

    # No newsletter form in this state
    assert not soup.find("form", {"data-testid": "newsletter-form"})

    uitour_buttons = soup.find_all("button", class_=UI_TOUR_CLASSES[UITOUR_BUTTON_SMART_WINDOW])
    uitour_by_ids = {btn["data-cta-uid"]: btn for btn in uitour_buttons}

    # Nav UITour button
    nav_btn = uitour_by_ids.get(str(page.nav_button_uid))
    assert nav_btn
    assert nav_btn["data-cta-position"] == "nav"
    assert nav_btn.get_text(strip=True) == page.smart_window_button_label

    # Intro UITour button
    intro_btn = uitour_by_ids.get(str(page.intro_button_uid))
    assert intro_btn
    assert intro_btn["data-cta-position"] == "intro-smart-window"
    assert intro_btn.get_text(strip=True) == page.smart_window_button_label


@pytest.mark.django_db
def test_smart_window_page_waitlist_form(smart_window_page: SmartWindowPage, rf):
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
def test_smart_window_page_content_blocks(smart_window_page: SmartWindowPage, rf):
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
def test_smart_window_v_product_redirects_to_start(smart_window_page: SmartWindowPage, rf):
    """Visiting /smart-window/?v=product returns a 302 to /smart-window/start/."""
    page = smart_window_page
    explainer_page = SmartWindowExplainerPage(slug="start", title="Start")
    page.add_child(instance=explainer_page)
    explainer_page.save_revision().publish()
    request = rf.get(page.get_full_url(), {"v": "product"})
    response = page.serve(request)
    assert response.status_code == 302
    assert response["Location"] == explainer_page.get_url()


@pytest.mark.django_db
def test_smart_window_without_v_product_serves_normally(smart_window_page: SmartWindowPage, rf):
    """Visiting /smart-window/ without ?v=product serves the page normally."""
    page = smart_window_page
    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200
    request = rf.get(page.get_full_url() + "?v=other")
    response = page.serve(request)
    assert response.status_code == 200


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
def test_smart_window_show_try_smart_window(smart_window_page: SmartWindowPage, rf, show_button, country, expected):
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
