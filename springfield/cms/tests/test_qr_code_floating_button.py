# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page

pytestmark = [pytest.mark.django_db]


def _get_qr_snippet_aside(soup):
    return soup.find("aside", class_="fl-qr-code-floating-snippet")


def test_page_renders_qr_code_snippet(minimal_site, rf):
    page = get_thanks_page()
    page.show_floating_qr_code_snippet = True

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet <aside> should be rendered"
    assert "Get Firefox on your phone" in aside.get_text()
    assert aside.find("div", class_="fl-qr-code-close"), "Close button should be rendered when closable=True"


def test_page_does_not_render_qr_code_snippet_when_flag_off(minimal_site, rf):
    page = get_thanks_page()
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_qr_snippet_aside(soup), "QR code snippet should not render when qr_code_floating_button=None"


# def test_generates_code_from_url(minimal_site, rf):
#     page = get_thanks_page()
#     page.show_floating_qr_code_snippet = True

#     request = rf.get(page.get_full_url())
#     response = page.serve(request)
#     assert response.status_code == 200

#     soup = BeautifulSoup(response.content, "html.parser")
#     aside = _get_qr_snippet_aside(soup)
#     assert aside, "QR code snippet <aside> should be rendered"
#     assert aside.find("svg"), "SVG should be rendered for URLs"


# def test_generates_code_from_image(minimal_site, rf):
#     page = get_thanks_page()
#     page.show_floating_qr_code_snippet = True

#     image, _, _, _ = get_placeholder_images()

#     request = rf.get(page.get_full_url())
#     response = page.serve(request)
#     assert response.status_code == 200

#     soup = BeautifulSoup(response.content, "html.parser")
#     aside = _get_qr_snippet_aside(soup)
#     assert aside, "QR code snippet <aside> should be rendered"
#     assert aside.find("img"), "img should be rendered for images"


# def test_image_takes_precedence(minimal_site, rf):
#     page = get_thanks_page()
#     image, _, _, _ = get_placeholder_images()

#     request = rf.get(page.get_full_url())
#     response = page.serve(request)
#     assert response.status_code == 200

#     soup = BeautifulSoup(response.content, "html.parser")
#     aside = _get_qr_snippet_aside(soup)
#     assert aside, "QR code snippet <aside> should be rendered"
#     assert aside.find("img"), "img should be rendered if both fields are populated"


# def test_url_override_takes_precedence(minimal_site, rf):
#     page = get_thanks_page()

#     snippet = page.qr_code_floating_button

#     page.override_url = "www.firefox.org"
#     snippet.url = "www.firefox.com"

#     result = resolve_qr_source(page, snippet)
#     assert result["value"] == "www.firefox.org"


# def test_image_override_takes_precedence(minimal_site, rf):
#     page = get_thanks_page()

#     image, override_image, _, _ = get_placeholder_images()

#     snippet = page.qr_code_floating_button

#     page.override_image = override_image
#     snippet.image = image

#     result = resolve_qr_source(page, snippet)
#     assert result["value"] == override_image.file.url


# def test_default_override_takes_precedence(minimal_site, rf):
#     page = get_thanks_page()

#     snippet = page.qr_code_floating_button

#     page.override_default_open = True
#     snippet.default_open = False

#     result = resolve_qr_source(page, snippet)
#     assert result["open"]
