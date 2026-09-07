# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.tests.factories import FlareDocsIndexPageFactory

pytestmark = [pytest.mark.django_db]


def get_page_soup(client, page):
    response = client.get(page.url)
    assert response.status_code == 200
    return BeautifulSoup(response.content.decode("utf-8"), "html.parser")


def get_header_cta_soup(client, page):
    # The desktop top-right CTA container in the flare header.
    return get_page_soup(client, page).find("div", class_="fl-header-main-download-button")


def test_flare_header_download_button_is_tagged_to_hide_for_firefox_desktop(client):
    # The existing download button must still render, but carry the hook the CSS
    # uses to hide it for Firefox desktop visitors (who get the QR dropdown).
    site = Site.objects.get(is_default_site=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-get-mobile-download")
    page.save_revision().publish()

    header_cta = get_header_cta_soup(client, page)
    assert header_cta is not None

    download_wrap = header_cta.find("div", class_="hide-from-firefox-desktop")
    assert download_wrap is not None
    assert download_wrap.find(class_="fl-download-firefox-button") is not None


def test_flare_header_renders_get_mobile_qr_gated_to_firefox_desktop(client):
    site = Site.objects.get(is_default_site=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-get-mobile-qr")
    page.save_revision().publish()

    header_cta = get_header_cta_soup(client, page)
    assert header_cta is not None

    # The QR dropdown wrap lives inside the conditional-display gates.
    dropdown = header_cta.find("div", class_="nav-get-mobile")
    assert dropdown is not None

    wrappers = dropdown.find_parents("div", class_="conditional-display")
    wrapper_classes = {cls for wrapper in wrappers for cls in wrapper.get("class", [])}
    # Firefox AND a desktop OS (nested wrappers => logical AND).
    assert "condition-is-firefox" in wrapper_classes
    for platform in ("condition-windows", "condition-osx", "condition-linux"):
        assert platform in wrapper_classes

    # The designed QR image is referenced from /media/ (matches flare convention).
    img = dropdown.find("img", class_="nav-get-mobile-qr-img")
    assert img is not None
    assert img["src"] == "/media/img/firefox/flare/fxcom-nav-mobile-qr.png"

    # Compact label on the button, descriptive caption in the panel.
    trigger = dropdown.find(class_="fl-dropdown-trigger")
    assert trigger is not None
    assert "for mobile" in trigger.get_text()

    # Caption is an accessible link to /mobile/.
    caption = dropdown.find(class_="nav-get-mobile-qr-caption")
    assert caption is not None
    assert caption.name == "a"
    assert "/mobile/" in caption["href"]
    assert "on your phone" in caption.get_text()

    # QR image carries real alt text (the trigger label) so screen-reader users
    # know it's there, distinct from the caption link's fuller text.
    assert img.get("alt") == trigger.get_text().strip()


def test_get_mobile_hidden_until_locale_is_translated(client):
    # When the active locale lacks the strings (ftl_has_messages is False), the QR
    # must not render AND the download button must NOT be hidden, so the locale
    # keeps a working CTA instead of an English-only one (or none at all).
    site = Site.objects.get(is_default_site=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-get-mobile-untranslated")
    page.save_revision().publish()

    with mock.patch("lib.l10n_utils.fluent.ftl_has_messages", return_value=False):
        soup = get_page_soup(client, page)

    header_cta = soup.find("div", class_="fl-header-main-download-button")
    assert header_cta is not None
    # No QR dropdown for an untranslated locale...
    assert header_cta.find("div", class_="nav-get-mobile") is None
    # ...and the download button is present and NOT hidden.
    assert header_cta.find("div", class_="hide-from-firefox-desktop") is None
    assert header_cta.find(class_="fl-download-firefox-button") is not None


def test_get_mobile_dropdown_id_is_not_duplicated(client):
    # The nav-cta include renders twice (mobile menu + desktop), but the QR
    # dropdown must only render once so its id/aria-controls stay unique.
    site = Site.objects.get(is_default_site=True)
    page = FlareDocsIndexPageFactory(parent=site.root_page, slug="flare-docs-get-mobile-dupe")
    page.save_revision().publish()

    soup = get_page_soup(client, page)
    assert len(soup.find_all(id="nav-get-mobile")) == 1
    assert len(soup.find_all(id="nav-get-mobile-panel")) == 1
