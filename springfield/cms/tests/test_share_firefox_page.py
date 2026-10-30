# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.blocks import KitIntroBlock
from springfield.cms.fixtures.base_fixtures import get_image_media
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_snippet
from springfield.cms.tests.factories import ShareFirefoxPageFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def share_page(placeholder_images):
    """A Share Firefox page with a Kit Intro."""
    site = Site.objects.get(is_default_site=True)
    page = ShareFirefoxPageFactory(parent=site.root_page)
    page.upper_content = [
        {
            "type": "intro",
            "id": "aa000000-0000-0000-0000-000000000001",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="b">Get Firefox</p>',
                    "subheading_text": '<p data-block-key="c">Shared by a friend</p>',
                },
                "media_above_buttons": get_image_media("cc000000-0000-0000-0000-000000000001"),
                "buttons": [
                    {
                        "type": "download_button",
                        "id": "bb000000-0000-0000-0000-000000000001",
                        "value": {
                            "pretranslated_label": None,
                            "custom_label": "Download Firefox",
                            "settings": {
                                "theme": "",
                                "icon": "",
                                "icon_position": "right",
                                "analytics_id": "",
                                "show_default_browser_checkbox": False,
                            },
                        },
                    },
                ],
            },
        }
    ]
    page.save()
    return page


def test_share_firefox_page_renders_media_between_heading_and_buttons(client, share_page):
    response = client.get("/en-US/share/")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")

    intro = soup.select_one(".fl-split-page-upper .fl-home-intro")
    heading = intro.find("h1", class_="fl-heading")
    media = intro.find("div", class_="fl-home-intro-media-above-buttons")
    buttons = intro.find("div", class_="fl-buttons")
    assert heading.get_text(strip=True) == "Get Firefox"
    assert media.find("img") is not None
    assert heading in media.find_all_previous("h1")
    assert buttons in media.find_all_next("div", class_="fl-buttons")
    assert buttons.find(class_="download-link") is not None

    script_sources = [script["src"] for script in soup.find_all("script", src=True)]
    assert not any("referral-attribution" in source for source in script_sources)


@pytest.mark.parametrize("show_pre_footer", [True, False])
def test_share_firefox_page_pre_footer_toggle(client, share_page, show_pre_footer):
    get_pre_footer_cta_snippet()
    share_page.show_pre_footer = show_pre_footer
    share_page.save_revision().publish()

    response = client.get("/en-US/share/")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    assert (soup.select_one(".fl-pre-footer-cta") is not None) is show_pre_footer


@pytest.mark.parametrize("show_nav_cta", [True, False])
def test_share_firefox_page_nav_download_button_toggle(client, share_page, show_nav_cta):
    share_page.show_nav_cta = show_nav_cta
    share_page.save_revision().publish()

    response = client.get("/en-US/share/")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    nav_cta = soup.select_one(".fl-header .nav-cta-wrap")
    assert nav_cta.find(class_="download-link") is not None
    assert ("hide-nav-download-on-desktop" in nav_cta["class"]) is not show_nav_cta


@pytest.mark.parametrize(("allow_media_above_buttons", "has_field"), [(True, True), (False, False)])
def test_kit_intro_block_media_above_buttons_field(allow_media_above_buttons, has_field):
    block = KitIntroBlock(allow_media_above_buttons=allow_media_above_buttons)

    assert ("media_above_buttons" in block.child_blocks) is has_field


def test_share_firefox_page_renders_intro_with_media_right(client, placeholder_images):
    site = Site.objects.get(is_default_site=True)
    page = ShareFirefoxPageFactory(parent=site.root_page)
    page.upper_content = [
        {
            "type": "side_intro",
            "id": "dd000000-0000-0000-0000-000000000001",
            "value": {
                "settings": {"layout": "right", "full_width": False, "slim": False, "anchor_id": ""},
                "media": get_image_media("dd000000-0000-0000-0000-000000000002"),
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="d">You’re invited</p>',
                    "subheading_text": "",
                },
                "content": [
                    {
                        "type": "buttons",
                        "id": "dd000000-0000-0000-0000-000000000003",
                        "value": [get_button_variants()["download"]],
                    }
                ],
            },
        }
    ]
    page.save_revision().publish()

    response = client.get("/en-US/share/")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    intro = soup.select_one(".fl-split-page-upper .fl-intro.fl-intro-media-right")
    assert intro.find("h1").get_text(strip=True) == "You’re invited"
    assert intro.select_one(".fl-intro-media img") is not None
    assert intro.find(class_="download-link") is not None
