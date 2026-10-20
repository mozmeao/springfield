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


@pytest.fixture
def acme():
    partner = PartnerRepack(
        name="Acme",
        slug="acme",
        windows64_url=f"https://download.mozilla.org/?product={ACME_PRODUCT}&os=win64",
        windows_languages="en-US",
        live=True,
    )
    partner.save()
    return partner


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
