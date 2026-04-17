# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.freeformpage_2026 import get_freeform_page_2026_with_qr_snippet
from springfield.cms.fixtures.snippet_fixtures import get_qr_code_snippet
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page
from springfield.cms.fixtures.whats_new_page_fixtures import (
    get_whats_new_page_2026_with_qr_snippet,
    get_whats_new_page_with_qr_snippet,
)

pytestmark = [pytest.mark.django_db]


def _get_qr_snippet_aside(soup):
    return soup.find("aside", class_="fl-qr-code-snippet")


def test_thanks_page_renders_qr_code_snippet(minimal_site, rf):
    page = get_thanks_page()
    page.qr_code_floating_button = None

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet <aside> should be rendered"
    assert aside.find("div", class_="fl-qr-code-snippet-kit"), "QR code SVG wrapper should be rendered"
    assert "Get Firefox on your phone" in aside.get_text()
    assert aside.find("button", class_="fl-qr-code-snippet-close"), "Close button should be rendered when closable=True"


def test_thanks_page_does_not_render_qr_code_snippet_when_flag_off(minimal_site, rf):
    page = get_thanks_page()
    page.qr_code_floating_button = None
    page.show_qr_code_snippet = False
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_qr_snippet_aside(soup), "QR code snippet should not render when show_qr_code_snippet=False"


def test_freeform_page_2026_renders_qr_code_snippet(minimal_site, rf):
    page = get_freeform_page_2026_with_qr_snippet()
    page.qr_code_floating_button = None

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet <aside> should be rendered"
    assert aside.find("div", class_="fl-qr-code-snippet-kit"), "QR code SVG wrapper should be rendered"
    assert "Get Firefox on your phone" in aside.get_text()
    assert aside.find("button", class_="fl-qr-code-snippet-close"), "Close button should be rendered when closable=True"


def test_freeform_page_2026_does_not_render_qr_code_snippet_when_flag_off(minimal_site, rf):
    from springfield.cms.fixtures.freeformpage_2026 import get_freeform_page_2026_test_page

    get_qr_code_snippet()
    page = get_freeform_page_2026_test_page()
    page.show_qr_code_snippet = False
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_qr_snippet_aside(soup), "QR code snippet should not render when show_qr_code_snippet=False"


def test_whats_new_page_renders_qr_code_snippet(minimal_site, rf):
    page = get_whats_new_page_with_qr_snippet()
    page.qr_code_floating_button = None

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet <aside> should be rendered"
    assert aside.find("div", class_="fl-qr-code-snippet-kit"), "QR code SVG wrapper should be rendered"
    assert "Get Firefox on your phone" in aside.get_text()


def test_whats_new_page_does_not_render_qr_code_snippet_when_flag_off(minimal_site, rf):
    page = get_whats_new_page_with_qr_snippet()
    page.qr_code_floating_button = None
    page.show_qr_code_snippet = False
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_qr_snippet_aside(soup), "QR code snippet should not render when show_qr_code_snippet=False"


def test_whats_new_page_2026_renders_qr_code_snippet(minimal_site, rf):
    page = get_whats_new_page_2026_with_qr_snippet()
    page.qr_code_floating_button = None

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet <aside> should be rendered"
    assert aside.find("div", class_="fl-qr-code-snippet-kit"), "QR code SVG wrapper should be rendered"
    assert "Get Firefox on your phone" in aside.get_text()


def test_whats_new_page_2026_does_not_render_qr_code_snippet_when_flag_off(minimal_site, rf):
    page = get_whats_new_page_2026_with_qr_snippet()
    page.qr_code_floating_button = None
    page.show_qr_code_snippet = False
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_qr_snippet_aside(soup), "QR code snippet should not render when show_qr_code_snippet=False"


def test_qr_code_snippet_not_closable(minimal_site, rf):
    page = get_freeform_page_2026_with_qr_snippet()
    page.qr_code_floating_button = None
    snippet = get_qr_code_snippet()
    snippet.closable = False
    snippet.save()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    aside = _get_qr_snippet_aside(soup)
    assert aside, "QR code snippet should still render"
    assert not aside.find("button", class_="fl-qr-code-snippet-close"), "Close button should not render when closable=False"
    assert "fl-qr-code-snippet-closable" not in aside.get("class", []), "Closable class should not be applied"
