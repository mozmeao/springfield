# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup
from waffle.testutils import override_switch

from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.freeformpage import get_mobile_store_qr_code_test_page
from springfield.cms.fixtures.homepage_fixtures import get_kit_banner
from springfield.cms.models import SimpleRichTextPage
from springfield.cms.tests.factories import DownloadIndexPageFactory, DownloadPageFactory

pytestmark = [pytest.mark.django_db]

MI_STORE_LINK = "https://app.mi.com/details?id=org.mozilla.firefox"
V_APPSTORE_LINK = "https://app.vivo.com.cn/firefox"
APK_LINK = "https://github.com/mozilla/firefox/releases/latest"


@pytest.fixture
def home_page(site_homepage):
    buttons = get_button_variants()
    kit_banner = get_kit_banner()
    kit_banner["value"]["buttons"] = [buttons["download"], buttons["store_android"]]
    site_homepage.lower_content = [kit_banner]
    site_homepage.save_revision().publish()
    return site_homepage


@pytest.fixture
def android_download_page(minimal_site):
    root_page = SimpleRichTextPage.objects.first()
    download_index = DownloadIndexPageFactory(parent=root_page, slug="download")
    return DownloadPageFactory(parent=download_index, slug="android", platform="android")


@pytest.fixture
def china_download_links(settings):
    settings.MI_STORE_FIREFOX_LINK = MI_STORE_LINK
    settings.V_APPSTORE_FIREFOX_LINK = V_APPSTORE_LINK
    settings.FIREFOX_ANDROID_APK_LINK = APK_LINK


@pytest.fixture
def no_china_download_links(settings):
    settings.MI_STORE_FIREFOX_LINK = ""
    settings.V_APPSTORE_FIREFOX_LINK = ""
    settings.FIREFOX_ANDROID_APK_LINK = ""


def get_soup(client, path, country_code):
    response = client.get(path, HTTP_CF_IPCOUNTRY=country_code)
    assert response.status_code == 200
    return BeautifulSoup(response.content, "html.parser")


def find_official_google_play_badges(soup):
    return soup.find_all("img", alt="Get it on Google Play")


def assert_store_badge(link, href_prefix, logo, caption, store_name, cta_text):
    assert "fl-store-badge" in link["class"]
    assert link["href"].startswith(href_prefix)
    assert link["data-cta-text"] == cta_text
    logo_image = link.find("img", class_="fl-store-badge-logo")
    assert logo_image["src"].endswith(logo)
    assert logo_image["alt"] == ""
    label = link.find("span", class_="fl-store-badge-label")
    assert label.find(string=True, recursive=False).strip() == caption
    assert label.find("span").get_text() == store_name


def test_visitor_in_china_gets_google_play_then_china_download_options(home_page, china_download_links, client):
    intro = get_soup(client, home_page.url, "CN").find("div", class_="fl-home-intro")

    links = intro.find("div", class_="fl-china-download-options").find_all("a")
    assert len(links) == 4
    assert_store_badge(links[0], "https://play.google.com/", "logo-google-play.svg", "Download on", "Google Play", "Play Store")
    assert links[0]["id"] == "playStoreLink-primary"
    assert "ga-product-download" in links[0]["class"]
    assert "fl-store-button-android" in links[0]["class"]
    assert_store_badge(links[1], MI_STORE_LINK, "logo-mi-store.svg", "Download on the", "Mi Store", "Mi Store")
    assert_store_badge(links[2], V_APPSTORE_LINK, "logo-v-appstore.svg", "Download on the", "V-appstore", "V-appstore")
    assert links[3]["href"] == APK_LINK
    assert "fl-android-apk-link" in links[3]["class"]
    assert links[3].get_text(strip=True) == "APK via GitHub"
    assert links[3]["data-cta-uid"] == "android-apk"


def test_visitor_in_china_only_gets_download_options_with_links(home_page, china_download_links, settings, client):
    settings.V_APPSTORE_FIREFOX_LINK = ""

    intro = get_soup(client, home_page.url, "CN").find("div", class_="fl-home-intro")

    hrefs = [link["href"] for link in intro.find("div", class_="fl-china-download-options").find_all("a")]
    assert len(hrefs) == 3
    assert hrefs[0].startswith("https://play.google.com/")
    assert hrefs[1:] == [MI_STORE_LINK, APK_LINK]


def test_visitor_in_china_gets_only_google_play_when_no_china_links_are_set(home_page, no_china_download_links, client):
    intro = get_soup(client, home_page.url, "CN").find("div", class_="fl-home-intro")

    links = intro.find("div", class_="fl-china-download-options").find_all("a")
    assert len(links) == 1
    assert_store_badge(links[0], "https://play.google.com/", "logo-google-play.svg", "Download on", "Google Play", "Play Store")


def test_visitor_outside_china_gets_official_google_play_badges(home_page, china_download_links, client):
    soup = get_soup(client, home_page.url, "US")

    assert soup.find("div", class_="fl-china-download-options") is None
    assert len(find_official_google_play_badges(soup)) == 3


def test_visitor_in_china_gets_download_options_for_every_google_play_badge_on_the_home_page(home_page, china_download_links, client):
    soup = get_soup(client, home_page.url, "CN")

    assert find_official_google_play_badges(soup) == []
    assert len(soup.find_all("div", class_="fl-china-download-options")) == 3


def test_visitor_in_china_gets_download_options_on_the_android_download_page(android_download_page, china_download_links, client):
    actions = get_soup(client, "/en-US/download/android/", "CN").find("div", class_="download-page-actions")

    links = actions.find("div", class_="fl-china-download-options").find_all("a")
    assert [link["href"] for link in links[1:]] == [MI_STORE_LINK, V_APPSTORE_LINK, APK_LINK]
    assert links[0]["id"] == "playStoreLink-primary"
    assert links[3]["data-cta-position"] == "download-intro"


def test_visitor_in_china_gets_download_options_on_the_android_download_page_without_a_cms_page(minimal_site, china_download_links, client):
    soup = get_soup(client, "/en-US/download/android/", "CN")

    assert find_official_google_play_badges(soup) == []
    groups = soup.find_all("div", class_="fl-china-download-options")
    assert [group.find("a")["id"] for group in groups] == ["playStoreLink-primary", "playStoreLink-footer"]


def test_visitor_in_china_gets_download_options_in_the_mobile_store_qr_code_block(index_page, placeholder_images, china_download_links, client):
    page = get_mobile_store_qr_code_test_page()

    soup = get_soup(client, page.url, "CN")

    assert find_official_google_play_badges(soup) == []
    for store_buttons in soup.find_all("div", class_="fl-mobile-store-buttons"):
        assert store_buttons.find("div", class_="fl-china-download-options") is not None


def test_visitor_in_china_gets_the_android_download_options_url(home_page, client):
    html = get_soup(client, home_page.url, "CN").find("html")

    assert html["data-android-download-options-url"] == "/en-US/download/android/"


def test_visitor_outside_china_does_not_get_the_android_download_options_url(home_page, client):
    html = get_soup(client, home_page.url, "US").find("html")

    assert not html.has_attr("data-android-download-options-url")


@override_switch("firefox-app-store-banner", active=True)
def test_visitor_in_china_gets_the_android_download_page_from_the_app_store_banner(minimal_site, client):
    banner = get_soup(client, "/en-US/browsers/desktop/", "CN").find("aside", id="firefox-app-store-banner")

    android_link = banner.find("a", class_="show-android")
    assert android_link["href"] == "/en-US/download/android/"
    assert "ga-product-download" not in android_link["class"]
    assert banner.find("p", class_="show-android") is None


@override_switch("firefox-app-store-banner", active=True)
def test_visitor_outside_china_gets_google_play_from_the_app_store_banner(minimal_site, client):
    banner = get_soup(client, "/en-US/browsers/desktop/", "US").find("aside", id="firefox-app-store-banner")

    assert banner.find("a", class_="show-android")["href"].startswith("https://play.google.com/")
    assert banner.find("p", class_="show-android") is not None
