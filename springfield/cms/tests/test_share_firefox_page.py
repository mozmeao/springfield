# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.http import Http404, HttpResponseNotFound

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.blocks import KitIntroBlock
from springfield.cms.fixtures.kit_intro_fixtures import IMAGE_VARIANTS
from springfield.cms.middleware import CMSLocaleFallbackMiddleware
from springfield.cms.tests.factories import LocaleFactory, ShareFirefoxPageFactory
from springfield.sitemaps.utils import get_wagtail_urls

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def share_pages(placeholder_images):
    """An en-US Share Firefox page with a Kit Intro, published in fr and de."""
    site = Site.objects.get(is_default_site=True)
    en_us_page = ShareFirefoxPageFactory(parent=site.root_page)
    en_us_page.upper_content = [
        {
            "type": "intro",
            "id": "aa000000-0000-0000-0000-000000000001",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="b">Get Firefox</p>',
                    "subheading_text": '<p data-block-key="c">Shared by a friend</p>',
                },
                "media_above_buttons": [
                    {"type": "image", "id": "cc000000-0000-0000-0000-000000000001", "value": IMAGE_VARIANTS},
                ],
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
    en_us_page.save()

    pages = {"en-US": en_us_page}
    for language_code in ("fr", "de"):
        locale = LocaleFactory(language_code=language_code)
        translated_root_page = site.root_page.copy_for_translation(locale)
        translated_root_page.save_revision().publish()
        translated_page = en_us_page.copy_for_translation(locale)
        translated_page.save_revision().publish()
        pages[language_code] = translated_page
    return pages


@pytest.mark.parametrize("language_code", ["fr", "de"])
def test_share_firefox_page_renders_media_between_heading_and_buttons(client, share_pages, language_code):
    response = client.get(f"/{language_code}/share/")

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


@pytest.mark.parametrize("language_code", ["en-US", "es-ES"])
def test_share_firefox_page_is_not_found_outside_fr_and_de(rf, share_pages, language_code):
    """A 404 in an unserved locale is not redirected to the fr or de translation."""
    if language_code == "en-US":
        page = share_pages["en-US"]
    else:
        locale = LocaleFactory(language_code=language_code)
        Site.objects.get(is_default_site=True).root_page.copy_for_translation(locale)
        page = share_pages["en-US"].copy_for_translation(locale)
        page.save_revision().publish()

    def get_response(request):
        try:
            return page.serve(request)
        except Http404:
            return HttpResponseNotFound("not found")

    request = rf.get(f"/{language_code}/share/", HTTP_ACCEPT_LANGUAGE="fr")
    response = CMSLocaleFallbackMiddleware(get_response)(request)

    assert response.status_code == 404
    assert "Location" not in response


def test_share_firefox_page_sitemap_lists_only_fr_and_de(share_pages):
    assert sorted(get_wagtail_urls()["/share/"]) == ["de", "fr"]


@pytest.mark.parametrize(("allow_media_above_buttons", "has_field"), [(True, True), (False, False)])
def test_kit_intro_block_media_above_buttons_field(allow_media_above_buttons, has_field):
    block = KitIntroBlock(allow_media_above_buttons=allow_media_above_buttons)

    assert ("media_above_buttons" in block.child_blocks) is has_field
