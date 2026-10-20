# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.cache import caches

import pytest
from bs4 import BeautifulSoup
from markus.testing import MetricsMock

from springfield.cms.models import PartnerRepack

pytestmark = [pytest.mark.django_db]

ACME_PRODUCT = "partner-firefox-release-acme-acme-001-latest"


def make_partner(**fields):
    partner = PartnerRepack(**{"name": "Acme", "slug": "acme", "live": True, **fields})
    partner.save()
    return partner


def partner_link(link_os):
    return f"https://download.mozilla.org/?product={ACME_PRODUCT}&os={link_os}"


WINDOWS_DE = {"windows64_url": partner_link("win64"), "windows32_url": partner_link("win"), "windows_languages": "de"}
MAC_DE = {"mac_url": partner_link("osx"), "mac_languages": "de"}
LINUX_DE = {"linux_url": partner_link("linux64"), "linux_languages": "de"}


def render_page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return BeautifulSoup(response.content, "html.parser")


def partner_urls(soup):
    """Map each `os` with a partner download link anywhere on the page to its URL."""
    return {link["href"].split("os=")[1].split("&")[0]: link["href"] for link in soup.select(f'a[href*="{ACME_PRODUCT}"]')}


def heading(soup, state):
    return soup.select_one(f"section.state-{state} h1").get_text(strip=True)


@pytest.fixture
def acme():
    return make_partner(windows64_url=partner_link("win64"), windows_languages="en-US")


def test_published_partner_gets_a_noindex_partner_page(client, acme):
    response = client.get("/en-US/get/?p=acme")

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find("meta", attrs={"name": "robots"})["content"] == "noindex,follow"
    assert soup.find("main", class_="c-partner-download")["data-partner"] == "acme"


@pytest.mark.parametrize(
    "path, expected_location",
    [
        ("/en-US/get/", "/en-US/thanks/"),
        ("/de/get/?p=", "/de/thanks/"),
        ("/de/get/?p=%20", "/de/thanks/"),
        ("/fr/get/?p=nobody&utm_source=x&utm_campaign=y", "/fr/thanks/?utm_source=x&utm_campaign=y"),
        ("/fr/get/?utm_source=x&p=nobody&utm_campaign=y", "/fr/thanks/?utm_source=x&utm_campaign=y"),
    ],
)
def test_no_usable_partner_forwards_to_thanks(client, path, expected_location):
    response = client.get(path)

    assert response.status_code == 302
    assert response["Location"] == expected_location


def test_unpublished_partner_forwards_to_thanks(client, acme):
    acme.live = False
    acme.save()

    response = client.get("/en-US/get/?p=acme")

    assert response.status_code == 302
    assert response["Location"] == "/en-US/thanks/"


@pytest.mark.parametrize("p", ["ACME", "acme%20"])
def test_partner_link_name_ignores_case_and_spaces(client, acme, p):
    response = client.get(f"/en-US/get/?p={p}")

    assert response.status_code == 200
    assert response.context["partner"] == acme


@pytest.mark.parametrize(
    "p, reason",
    [("", "missing"), ("nobody", "unknown"), ("acme", "inactive")],
)
def test_forwarding_counts_the_reason_without_the_link_name(client, acme, p, reason):
    acme.live = False
    acme.save()

    with MetricsMock() as metrics_mock:
        client.get(f"/en-US/get/?p={p}")

    metrics_mock.assert_incr_once("springfield.partner_download.unknown", tags=[f"reason:{reason}"])


@pytest.mark.parametrize("path", ["/en-US/get/?p=acme", "/en-US/get/?p=nobody"])
def test_page_and_forward_use_the_default_cache_time(client, acme, path):
    response = client.get(path)

    assert response["Cache-Control"] == "max-age=600"


def test_unprefixed_link_goes_to_the_visitors_language(client, acme):
    response = client.get("/get/?p=acme", HTTP_ACCEPT_LANGUAGE="de")

    assert response.status_code == 302
    assert response["Location"] == "/de/get/?p=acme"


def test_unknown_url_locale_keeps_the_usual_redirect(client, acme):
    response = client.get("/xx/get/?p=acme", HTTP_ACCEPT_LANGUAGE="de")

    assert response.status_code == 302
    assert response["Location"] == "/de/xx/get/?p=acme"


def test_footer_languages_leave_out_the_mac_japanese_code(client, acme):
    response = client.get("/en-US/get/?p=acme")

    assert "ja" in response.context["translations"]
    assert "ja-JP-mac" not in response.context["translations"]


@pytest.fixture
def production_locales(tmp_path, settings):
    """Run with production locale rules and a French translation of only the shared download strings."""
    french_download_dir = tmp_path / "fr" / "firefox" / "download"
    french_download_dir.mkdir(parents=True)
    (french_download_dir / "desktop.ftl").write_text("firefox-desktop-download-meta-title-v2 = Télécharger pour ordinateur\n")
    settings.DEV = False
    settings.FLUENT_PATHS = [tmp_path, settings.FLUENT_LOCAL_PATH]
    caches["fluent"].clear()
    yield
    caches["fluent"].clear()


@pytest.mark.parametrize("locale", ["en-CA", "en-GB", "es-AR", "pt-PT"])
def test_alias_locale_is_kept_for_the_partner_build(client, acme, production_locales, locale):
    response = client.get(f"/{locale}/get/?p=acme")

    assert response.status_code == 200
    assert response.context["partner_lang"] == locale
    assert response.context["options"]["windows"] == {"state": "language", "urls": {}}


def test_untranslated_partner_strings_show_in_english(client, acme, production_locales):
    response = client.get("/fr/get/?p=acme")

    assert response.status_code == 200
    assert BeautifulSoup(response.content, "html.parser").title.get_text(strip=True) == "Télécharger pour ordinateur"
    assert response.context["fluent_l10n"].format_value("partner-download-continue") == "Continue to firefox.com"


def test_locale_without_any_translations_shows_english(client, acme, production_locales):
    # `production_locales` only translates French, so German has no Fluent files at all.
    response = client.get("/de/get/?p=acme")

    assert response.status_code == 200
    assert response.context["partner_lang"] == "de"
    assert BeautifulSoup(response.content, "html.parser").title.get_text(strip=True) == "Download Firefox for Desktop — from Mozilla"
    assert response.context["fluent_l10n"].format_value("partner-download-continue") == "Continue to firefox.com"


def test_alias_locale_without_its_build_offers_regular_firefox(client):
    make_partner(windows64_url=partner_link("win64"), windows_languages="en-US")

    soup = render_page(client, "/en-CA/get/?p=acme")

    assert soup.find("main")["data-windows"] == "language"
    assert soup.select_one("section.state-5")
    assert partner_urls(soup) == {}


@pytest.mark.parametrize("fields", [WINDOWS_DE, MAC_DE, LINUX_DE])
def test_no_partner_url_for_a_language_the_build_lacks(client, fields):
    make_partner(**fields)

    assert partner_urls(render_page(client, "/fr/get/?p=acme")) == {}


@pytest.mark.parametrize(
    "fields, expected_os",
    [(WINDOWS_DE, {"win64", "win"}), (MAC_DE, {"osx"}), (LINUX_DE, {"linux64"})],
)
def test_only_systems_with_a_build_get_partner_urls(client, fields, expected_os):
    make_partner(**fields)

    assert set(partner_urls(render_page(client, "/de/get/?p=acme"))) == expected_os


def test_partner_url_adds_the_page_language_last(client):
    make_partner(windows64_url=f"{partner_link('win64')}&foo=1&lang=fr", windows_languages="de")

    soup = render_page(client, "/de/get/?p=acme")

    assert partner_urls(soup) == {"win64": f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64&lang=de"}


def test_japanese_partner_urls_use_the_mac_code_on_mac_only(client):
    make_partner(windows64_url=partner_link("win64"), windows_languages="ja", mac_url=partner_link("osx"), mac_languages="ja")

    urls = partner_urls(render_page(client, "/ja/get/?p=acme"))

    assert urls["osx"].endswith("&lang=ja-JP-mac")
    assert urls["win64"].endswith("&lang=ja")


def test_partner_urls_stay_on_the_production_server(client, settings):
    settings.BOUNCER_URL = "https://bouncer.stage.example/"
    make_partner(windows64_url=partner_link("win64"), windows_languages="de")

    soup = render_page(client, "/de/get/?p=acme")

    assert partner_urls(soup)["win64"].startswith("https://download.mozilla.org/?")
    linux_option = soup.select_one("section.state-9 a.os_linux64")
    assert linux_option["href"].startswith("https://bouncer.stage.example/")


def test_messages_name_the_partner(client):
    make_partner(windows64_url=partner_link("win64"), windows_languages="en-US", linux_url=partner_link("linux64"), linux_languages="en-US")
    language_soup = render_page(client, "/de/get/?p=acme")
    PartnerRepack.objects.all().delete()
    make_partner(mac_url=partner_link("osx"), mac_languages="de")
    device_soup = render_page(client, "/de/get/?p=acme")

    for soup, state in [(language_soup, 5), (language_soup, 8), (device_soup, 1), (device_soup, 6), (device_soup, 9), (device_soup, 10)]:
        assert "from Acme" in heading(soup, state)


def test_partner_name_is_escaped(client):
    make_partner(name="<b>Acme</b> & Co", windows64_url=partner_link("win64"), windows_languages="en-US")

    soup = render_page(client, "/de/get/?p=acme")

    language_heading = soup.select_one("section.state-5 h1")
    assert "from <b>Acme</b> & Co" in language_heading.get_text()
    assert language_heading.find("b") is None


@pytest.mark.parametrize("label, expected_text", [("visit", "Visit Acme"), ("learn_more", "Learn more")])
def test_link_for_current_firefox_users_uses_its_label(client, label, expected_text):
    make_partner(**WINDOWS_DE, firefox_user_link_url="https://acme.example/", firefox_user_link_label=label)

    links = render_page(client, "/de/get/?p=acme").select("section.state-2 a")

    assert [(link.get_text(strip=True), link["href"]) for link in links] == [
        ("Continue to firefox.com", "/de/"),
        (expected_text, "https://acme.example/"),
    ]


def test_current_firefox_users_only_continue_without_a_partner_link(client):
    make_partner(**WINDOWS_DE)

    links = render_page(client, "/de/get/?p=acme").select("section.state-2 a")

    assert [(link.get_text(strip=True), link["href"]) for link in links] == [("Continue to firefox.com", "/de/")]


def test_page_has_no_other_language_link(client):
    make_partner(**WINDOWS_DE)

    soup = render_page(client, "/en-US/get/?p=acme")

    assert "Download in another language" not in soup.get_text()


def test_markup_for_the_page_script(client):
    make_partner(**WINDOWS_DE, **MAC_DE, **LINUX_DE)

    soup = render_page(client, "/de/get/?p=acme")

    main = soup.find("main")
    assert (main["data-partner"], main["data-lang"]) == ("acme", "de")
    assert (main["data-windows"], main["data-mac"], main["data-linux"]) == ("available", "available", "available")
    repack_links = soup.select(".c-partner-download-links a")
    assert [(link["class"], link["data-download-version"]) for link in repack_links] == [
        (["download-link"], "win64"),
        (["download-link"], "win"),
        (["download-link"], "osx"),
    ]
    linux_link = soup.select_one(f'section.state-7 a[href*="{ACME_PRODUCT}"]')
    assert "download-link" not in linux_link["class"]
    assert not linux_link.has_attr("data-download-version")


def test_state_blocks_have_no_duplicate_ids(client):
    make_partner(windows64_url=partner_link("win64"), windows_languages="en-US", mac_url=partner_link("osx"), mac_languages="de")

    ids = [element["id"] for element in render_page(client, "/de/get/?p=acme").select("main [id]")]

    assert len(ids) == len(set(ids))
