# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

from springfield.firefox import all_form

# ---------------------------------------------------------------------------
# get_store_url — iOS
# ---------------------------------------------------------------------------


class TestGetStoreUrlIos:
    """iOS store links must be country-less; campaign params must be preserved.

    The /{country}/ segment controls App Store territory, not display language.
    Language is determined by the user's device settings regardless of the URL.
    Mapping our UI locale to a country code would frequently guess the wrong
    territory and could interfere with Apple's own IP-based geolocation on web.
    """

    CAMPAIGN_PARAMS = "mz_pr=firefox_mobile&pt=373246&ct=firefox-all&mt=8"

    def test_no_country_in_url(self):
        url = all_form.get_store_url("ios", "firefox-latest-ssl")
        assert "/{country}/" not in url
        assert "{country}" not in url
        # No two-letter segment after the hostname — e.g. apps.apple.com/us/ must not appear.
        assert not re.search(r"apps\.apple\.com/[a-z]{2}/", url)

    def test_campaign_params_present(self):
        url = all_form.get_store_url("ios", "firefox-latest-ssl")
        assert self.CAMPAIGN_PARAMS in url

    def test_base_url_structure(self):
        url = all_form.get_store_url("ios", "firefox-latest-ssl")
        assert url.startswith("https://apps.apple.com/app/apple-store/id989804926")


# ---------------------------------------------------------------------------
# get_store_url — Android
# ---------------------------------------------------------------------------


class TestGetStoreUrlAndroid:
    def test_no_hl_param_in_url(self):
        # Language detection is left to Play Store via the browser's Accept-Language header.
        url = all_form.get_store_url("android", "firefox-latest-ssl")
        assert "hl=" not in url

    def test_esr_returns_none(self):
        # ESR has no Android channel; there is no store link to offer.
        assert all_form.get_store_url("android", "firefox-esr-latest-ssl") is None


# ---------------------------------------------------------------------------
# get_store_url — non-store slugs
# ---------------------------------------------------------------------------


class TestGetStoreUrlDesktop:
    def test_returns_none_for_linux(self):
        assert all_form.get_store_url("linux64", "firefox-latest-ssl") is None

    def test_returns_none_for_osx(self):
        assert all_form.get_store_url("osx", "firefox-latest-ssl") is None
