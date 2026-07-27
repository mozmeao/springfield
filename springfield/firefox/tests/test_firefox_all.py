# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from unittest.mock import patch

from django.conf import settings

import pytest
from pyquery import PyQuery as pq

from springfield.base.urlresolvers import reverse
from springfield.firefox.firefox_details import firefox_desktop

# All tests require the database
pytestmark = pytest.mark.django_db

OS_LANG_PAIRS = [
    # windows
    ("win64", "en-US"),
    ("win64-msi", "en-US"),
    ("win64-aarch64", "en-US"),
    ("win", "en-US"),
    ("win-msi", "en-US"),
    ("win64", "de"),
    ("win64-msi", "fr"),
    ("win64-aarch64", "hi-IN"),
    ("win", "ja"),
    ("win-msi", "es-ES"),
    # macos
    ("osx", "en-US"),
    ("osx", "de"),
    ("osx", "fr"),
    ("osx", "hi-IN"),
    # linux
    ("linux64", "en-US"),
    ("linux", "en-US"),
    ("linux64", "de"),
    ("linux", "fr"),
    ("linux64", "hi-IN"),
    ("linux", "ja"),
]


def test_all_step_1(client):
    resp = client.get(reverse("firefox.all"))
    doc = pq(resp.content)

    # Step 1 is active, steps 2,3,4 are disabled.
    assert len(doc(".t-step-disabled")) == 3
    # 5 desktop products, 4 mobile products.
    assert len(doc(".c-product-list > li")) == 9
    assert len(doc(".qa-desktop-list > li")) == 5
    assert len(doc(".qa-mobile-list > li")) == 4


@pytest.mark.parametrize(
    "product_slug, name, count",
    (
        ("desktop-release", "Firefox", 10),
        ("desktop-esr", "Firefox Extended Support Release", 9),
        ("desktop-beta", "Firefox Beta", 10),
        ("desktop-developer", "Firefox Developer Edition", 9),
        ("desktop-nightly", "Firefox Nightly", 9),
    ),
)
def test_all_step_2(client, product_slug, name, count):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": product_slug}))
    doc = pq(resp.content)

    # Step 1 is done, step 2 is active, steps 3,4 are disabled.
    assert name in doc("#all-product-selection").text()
    assert len(doc(".t-step-disabled")) == 2
    # platforms for desktop-release, including Windows Store
    assert len(doc(".c-platform-list > li")) == count


def test_all_step_3(client):
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": "desktop-release", "platform": "win64"}))
    doc = pq(resp.content)

    # Step 1,2 is done, step 3 is active, step 4 is disabled.
    assert len(doc(".t-step-disabled")) == 1
    # completed steps show their selected values
    assert "Firefox" in doc("#all-product-selection").text()
    assert "Windows 64-bit" in doc("#all-platform-selection").text()
    # first locale matches request.locale
    assert doc(".c-lang-list > li").eq(0).text() == "English (US) - English (US)"
    # number of locales equals the number of builds
    assert len(doc(".c-lang-list > li")) == len(firefox_desktop.get_filtered_full_builds("release"))


def test_all_step_4(client):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-release", "platform": "win64", "locale": "en-US"}))
    doc = pq(resp.content)

    # Steps 1,2,3 are done, step 4 is active, no more steps.
    assert len(doc(".t-step-disabled")) == 0
    # completed steps show their selected values
    assert "Firefox" in doc("#all-product-selection").text()
    assert "Windows 64-bit" in doc("#all-platform-selection").text()
    assert "English (US)" in doc("#all-lang-selection").text()
    # The download button should be present and correct.
    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    assert (
        link.attr("href")
        == list(filter(lambda b: b["locale"] == "en-US", firefox_desktop.get_filtered_full_builds("release")))[0]["platforms"]["win64"][
            "download_url"
        ]
    )


def test_edit_buttons(client):
    """Each completed step shows an Edit button linking back to re-select that step."""
    # Step 2: product chosen → 1 Edit button back to step 1
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "desktop-release"}))
    doc = pq(resp.content)
    product_edit = doc("a[aria-labelledby='all-product all-product-selection']")
    assert len(product_edit) == 1
    assert product_edit.attr("href") == reverse("firefox.all")

    # Step 3: product + platform chosen → Edit buttons for both
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": "desktop-release", "platform": "win64"}))
    doc = pq(resp.content)
    assert len(doc("a[aria-labelledby='all-product all-product-selection']")) == 1
    platform_edit = doc("a[aria-labelledby='all-platform all-platform-selection']")
    assert len(platform_edit) == 1
    assert platform_edit.attr("href") == reverse("firefox.all.platforms", kwargs={"product_slug": "desktop-release"})

    # Step 4: all chosen → Edit buttons for all three
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-release", "platform": "win64", "locale": "en-US"}))
    doc = pq(resp.content)
    assert len(doc("a[aria-labelledby='all-product all-product-selection']")) == 1
    assert len(doc("a[aria-labelledby='all-platform all-platform-selection']")) == 1
    lang_edit = doc("a[aria-labelledby='all-lang all-lang-selection']")
    assert len(lang_edit) == 1
    assert lang_edit.attr("href") == reverse("firefox.all.locales", kwargs={"product_slug": "desktop-release", "platform": "win64"})


@pytest.mark.parametrize("os, lang", OS_LANG_PAIRS)
def test_firefox_release(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-release", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    download_url = link.attr("href")
    if "msi" in os:
        product = "firefox-msi-latest-ssl"
        os = os.replace("-msi", "")
    else:
        product = "firefox-latest-ssl"
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


def test_firefox_microsoft_store_release(client):
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": "desktop-release", "platform": "win-store"}))
    doc = pq(resp.content)

    assert len(doc("#msStoreLink")) == 1
    assert settings.MICROSOFT_WINDOWS_STORE_FIREFOX_WEB_LINK in doc("#msStoreLink").attr("href")


@pytest.mark.parametrize("os, lang", OS_LANG_PAIRS)
def test_firefox_beta(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-beta", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    download_url = link.attr("href")
    if "msi" in os:
        product = "firefox-beta-msi-latest-ssl"
        os = os.replace("-msi", "")
    else:
        product = "firefox-beta-latest-ssl"
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


def test_firefox_microsoft_store_beta(client):
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": "desktop-beta", "platform": "win-store"}))
    doc = pq(resp.content)

    assert len(doc("#msStoreLink")) == 1
    assert settings.MICROSOFT_WINDOWS_STORE_FIREFOX_BETA_WEB_LINK in doc("#msStoreLink").attr("href")


@pytest.mark.parametrize("os, lang", OS_LANG_PAIRS)
def test_firefox_developer(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-developer", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    download_url = link.attr("href")
    if "msi" in os:
        product = "firefox-devedition-msi-latest-ssl"
        os = os.replace("-msi", "")
    else:
        product = "firefox-devedition-latest-ssl"
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


@pytest.mark.parametrize("os, lang", OS_LANG_PAIRS)
def test_firefox_nightly(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-nightly", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    download_url = link.attr("href")
    if "msi" in os:
        product = "firefox-nightly-msi-latest-l10n-ssl"
        os = os.replace("-msi", "")
    else:
        product = "firefox-nightly-latest-l10n-ssl"
    if lang == "en-US":
        # en-us downloads don't get the l10n releases
        product = product.replace("-l10n", "")
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


@pytest.mark.parametrize("os, lang", [("linux64-aarch64", "es-ES"), ("linux64-aarch64", "pt-BR")])
def test_firefox_linux_nightly_aarch(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-nightly", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 1
    download_url = link.attr("href")
    product = "firefox-nightly-latest-l10n-ssl"
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    linux_link = doc(".c-linux-debian a")
    assert len(linux_link) == 1
    assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


@pytest.mark.parametrize("os, lang", OS_LANG_PAIRS)
def test_firefox_esr(client, os, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-esr", "platform": os, "locale": lang}))
    doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    expected_links = 1 if os in ["linux", "linux64-aarch64", "win64-aarch64"] else 2
    assert len(link) == expected_links
    download_url = link.attr("href")
    if "msi" in os:
        product = "firefox-esr-msi-latest-ssl"
        os = os.replace("-msi", "")
    else:
        product = "firefox-esr-latest-ssl"
    assert all(substr in download_url for substr in [f"product={product}", f"os={os}", f"lang={lang}"])
    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


@pytest.mark.parametrize("os, lang", [("win64", "en-US"), ("win64", "de"), ("osx", "en-US"), ("linux64", "en-US")])
def test_firefox_esr_next(client, os, lang):
    # Note: Only testing a few os/lang pairs to avoid mocking too much. We're mostly checking that all button and link types show up.
    # Set an esr_next version.
    orig_latest_version = firefox_desktop.latest_version
    orig_get_filtered_full_builds = firefox_desktop.get_filtered_full_builds

    def mock_latest_version(channel="release"):
        if channel == "esr_next":
            return "128.0"
        else:
            return orig_latest_version(channel)

    def mock_get_filtered_full_builds(channel, query=None):
        if channel == "esr_next":
            return [
                {
                    "locale": "en-US",
                    "platforms": {
                        "win64": {
                            "download_url": "https://download.mozilla.org/?product=firefox-esr-next-latest-ssl&os=win64&lang=en-US",
                        },
                        "linux64": {
                            "download_url": "https://download.mozilla.org/?product=firefox-esr-next-latest-ssl&os=linux64&lang=en-US",
                        },
                        "osx": {
                            "download_url": "https://download.mozilla.org/?product=firefox-esr-next-latest-ssl&os=osx&lang=en-US",
                        },
                    },
                },
                {
                    "locale": "de",
                    "platforms": {
                        "win64": {
                            "download_url": "https://download.mozilla.org/?product=firefox-esr-next-latest-ssl&os=win64&lang=de",
                        },
                    },
                },
            ]
        else:
            return orig_get_filtered_full_builds(channel, query)

    with patch("springfield.firefox.views.firefox_desktop.latest_version", side_effect=mock_latest_version):
        with patch("springfield.firefox.views.firefox_desktop.get_filtered_full_builds", side_effect=mock_get_filtered_full_builds):
            resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-esr", "platform": os, "locale": lang}))
            doc = pq(resp.content)

    link = doc(".download-link[data-cta-text='Download Now']")
    assert len(link) == 3  # We show both the current ESR and the next ESR download buttons, as well as ESR 115.

    download_esr_next_url = link.eq(0).attr("href")
    download_esr_url = link.eq(1).attr("href")

    assert all(substr in download_esr_next_url for substr in ["product=firefox-esr-next-latest-ssl", f"os={os}", f"lang={lang}"])
    assert all(substr in download_esr_url for substr in ["product=firefox-esr-latest-ssl", f"os={os}", f"lang={lang}"])

    if os.startswith("linux"):
        linux_link = doc(".c-linux-debian a")
        assert len(linux_link) == 1
        assert "https://support.mozilla.org/kb/install-firefox-linux" in linux_link.attr("href")


def test_firefox_mobile_release(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "mobile-release"}))
    doc = pq(resp.content)

    assert len(doc("#playStoreLink")) == 1
    assert len(doc("#appStoreLink")) == 1


def test_firefox_android_release(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "android-release"}))
    doc = pq(resp.content)

    assert len(doc("#playStoreLink")) == 1
    assert len(doc("#appStoreLink")) == 0


def test_firefox_android_beta(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "android-beta"}))
    doc = pq(resp.content)

    assert len(doc("#playStoreLink")) == 1
    assert len(doc("#appStoreLink")) == 0


def test_firefox_android_nightly(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "android-nightly"}))
    doc = pq(resp.content)

    assert len(doc("#playStoreLink")) == 1
    assert len(doc("#appStoreLink")) == 0


def test_firefox_ios_beta(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "ios-beta"}))
    doc = pq(resp.content)

    assert len(doc("#playStoreLink")) == 0
    assert len(doc("#appStoreLink")) == 0
    assert doc(".c-step-download a").attr("href") == reverse("firefox.ios.testflight")


def test_product_404(client):
    resp = client.get(reverse("firefox.all.platforms", kwargs={"product_slug": "xxx"}))
    assert resp.status_code == 404


def test_platform_404(client):
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": "desktop-release", "platform": "xxx"}))
    assert resp.status_code == 404


def test_locale_404(client):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": "desktop-release", "platform": "win64", "locale": "xxx"}))
    assert resp.status_code == 404


@pytest.mark.parametrize("product_slug", [("desktop-release"), ("desktop-esr"), ("desktop-beta"), ("desktop-developer")])
@pytest.mark.parametrize("lang", [("ckb"), ("ltg"), ("hye"), ("wo"), ("lo"), ("scn"), ("brx"), ("meh"), ("bo")])
def test_nightly_locales_only_on_nightly(client, product_slug, lang):
    resp = client.get(reverse("firefox.all.download", kwargs={"product_slug": product_slug, "platform": "win64", "locale": lang}))
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "product_slug",
    [
        ("desktop-developer"),
        ("desktop-nightly"),
        ("desktop-esr"),
        ("android-release"),
        ("android-beta"),
        ("android-nightly"),
        ("ios-release"),
        ("ios-beta"),
        ("mobile-release"),
    ],
)
def test_win_store_only_on_release_and_beta(client, product_slug):
    resp = client.get(reverse("firefox.all.locales", kwargs={"product_slug": product_slug, "platform": "win-store"}))
    assert resp.status_code == 404
