# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from unittest.mock import patch

from django.conf import settings

import pytest
from waffle.testutils import override_switch

from springfield.base.urlresolvers import reverse
from springfield.firefox import all_form
from springfield.firefox.firefox_details import firefox_desktop

# ---------------------------------------------------------------------------
# Vocabulary invariants
#
# These duplicate the vocabulary from media/js/firefox/all-form/all-form.js on
# purpose: the two copies have to stay identical, and a literal here is what
# tells us when one side moved.
# ---------------------------------------------------------------------------

JS_OS_VALUES = (
    "ios",
    "osx",
    "osx-pkg",
    "android",
    "win",
    "win-msi",
    "win64",
    "win64-msi",
    "win64-aarch64",
    "linux",
    "linux64",
    "linux64-aarch64",
)

JS_RELEASE_VALUES = ("stable", "beta", "dev", "nightly", "esr", "esr-next", "esr-115")

JS_UNSUPPORTED_PLATFORMS_BY_RELEASE = {
    "stable": ["linux"],
    "esr-next": ["ios", "android", "linux"],
    "esr": ["ios", "android"],
    "esr-115": ["ios", "android", "win64-aarch64", "linux", "linux64-aarch64"],
    "beta": ["linux"],
    "dev": ["ios", "android", "linux", "osx-pkg"],
    "nightly": ["ios", "linux"],
}


class TestVocabulary:
    def test_os_values_match_the_js(self):
        assert tuple(all_form.OS_LABELS) == JS_OS_VALUES

    def test_release_values_match_the_js(self):
        assert set(all_form.RELEASE_LABELS) | set(all_form.SECONDARY_RELEASES) == set(JS_RELEASE_VALUES)

    def test_matrix_matches_the_js(self):
        assert {release: list(values) for release, values in all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE.items()} == JS_UNSUPPORTED_PLATFORMS_BY_RELEASE

    def test_matrix_covers_every_release(self):
        assert set(all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE) == set(all_form.RELEASE_LABELS) | set(all_form.SECONDARY_RELEASES)

    def test_matrix_only_names_known_os_values(self):
        for values in all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE.values():
            assert set(values) <= set(all_form.OS_LABELS)

    def test_groups_cover_every_os_exactly_once(self):
        grouped = [os_value for _, os_values in all_form.OS_GROUPS for os_value in os_values]
        assert sorted(grouped) == sorted(all_form.OS_LABELS)

    def test_matrix_round_trips(self):
        assert all_form.get_unsupported_platforms() == JS_UNSUPPORTED_PLATFORMS_BY_RELEASE

    def test_matrix_carries_unselectable_releases(self):
        # The JS indexes this map by release without guarding, so every key has to
        # be there even for releases the form does not offer.
        assert set(all_form.get_unsupported_platforms()) == set(JS_RELEASE_VALUES)

    def test_os_labels_come_from_product_details(self):
        # Every desktop option product details knows about takes its label from
        # there, so the wording cannot drift from the rest of the site.
        for os_value, label in firefox_desktop.platform_labels.items():
            assert all_form.OS_LABELS[os_value] == label

    def test_only_store_apps_and_the_pkg_are_labelled_locally(self):
        assert set(all_form._EXTRA_OS_LABELS) == {"ios", "android", "osx-pkg"}
        assert not set(all_form._EXTRA_OS_LABELS) & set(firefox_desktop.platform_labels)


# ---------------------------------------------------------------------------
# Client data
#
# The payload all-form.js reads instead of hardcoding anything. The literals here
# are the keys the JS indexes; a rename on either side has to show up as a
# failure, because a missing key there is a silent `undefined`.
# ---------------------------------------------------------------------------

JS_OPTION_KEYS = ("fallback", "apt", "esr-next", "primary", "esr-115", "apk", "microsoft-store")

JS_SUPPORT_LINK_KEYS = ("release-notes", "system-requirements", "privacy")

JS_MESSAGE_KEYS = ("releaseUnavailable", "divider", "languageIgnored", "conflict", "fallback")


class TestClientData:
    def test_top_level_shape(self):
        data = all_form.get_client_data()
        assert set(data) == {
            "osValues",
            "unsupportedPlatformsByRelease",
            "mobileOS",
            "microsoftStoreOS",
            "esr115UnavailableLocales",
            "bouncerUrl",
            "bouncerChannels",
            "options",
            "storeUrls",
            "supportLinks",
            "messages",
        }

    def test_json_round_trips(self):
        import json

        assert json.loads(all_form.get_client_data_json()) == all_form.get_client_data()

    def test_os_values_match_the_js(self):
        assert tuple(all_form.get_client_data()["osValues"]) == JS_OS_VALUES

    def test_option_keys_match_the_js(self):
        keys = (
            all_form.OPTION_FALLBACK,
            all_form.OPTION_APT,
            all_form.OPTION_ESR_NEXT,
            all_form.OPTION_PRIMARY,
            all_form.OPTION_ESR_115,
            all_form.OPTION_APK,
            all_form.OPTION_MICROSOFT_STORE,
        )
        assert keys == JS_OPTION_KEYS

    def test_message_keys_match_the_js(self):
        assert set(all_form.get_client_data()["messages"]) == set(JS_MESSAGE_KEYS)

    def test_support_link_keys_match_the_js(self):
        assert tuple(link["key"] for link in all_form.get_support_links("win64", "stable")) == JS_SUPPORT_LINK_KEYS

    def test_primary_actions_cover_every_family_and_release(self):
        # The JS indexes this table directly, so a gap is a TypeError rather than
        # a missing button.
        primary = all_form.get_client_data()["options"]["primary"]
        assert set(primary) == {"desktop", "ios", "android"}
        for actions in primary.values():
            assert set(actions) == set(all_form.RELEASE_LABELS)
            for action in actions.values():
                assert action["label"]
                assert action["icon"]

    def test_url_tables_cover_every_selectable_release(self):
        data = all_form.get_client_data()
        tables = (
            data["options"]["apk"]["hrefs"],
            data["options"]["microsoftStore"]["hrefs"],
            data["storeUrls"]["ios"],
            data["storeUrls"]["android"],
            *data["supportLinks"]["releaseNotes"]["urls"].values(),
            *data["supportLinks"]["systemRequirements"]["urls"].values(),
        )
        for table in tables:
            assert set(table) == set(all_form.RELEASE_LABELS)

    def test_link_families_are_the_ones_the_js_derives(self):
        data = all_form.get_client_data()
        assert set(data["supportLinks"]["releaseNotes"]["urls"]) == set(all_form.LINK_FAMILIES)
        assert all_form.get_link_family("win64") == "desktop"
        assert all_form.get_link_family("osx-pkg") == "desktop"
        assert all_form.get_link_family("android") == "android"

    def test_esr_115_recommendations_are_desktop_only(self):
        recommendations = all_form.get_client_data()["options"]["esr115"]["recommendations"]
        assert set(recommendations) == {"windows", "macos", "linux"}

    def test_bouncer_pieces_rebuild_a_download_url(self):
        # The JS builds this one URL itself because the language reaches it, so
        # the pieces it needs have to be there and have to agree with ours.
        data = all_form.get_client_data()
        assert data["bouncerUrl"] == settings.BOUNCER_URL
        assert set(data["bouncerChannels"]) == set(JS_RELEASE_VALUES)
        assert all_form.get_download_url("win64", "beta", "de").startswith(data["bouncerUrl"])

    def test_esr_next_availability_matches_the_server(self):
        # The JS cannot see product details, so the payload has to tell it
        # whether a second ESR exists. Both sides gate the option on that.
        data = all_form.get_client_data()
        available = data["options"]["esrNext"]["available"]
        assert available is bool(all_form.get_esr_next_version())
        offered = all_form.get_esr_next_download_url("win64", "esr", "en-US") is not None
        assert offered is available

    def test_no_copy_is_left_hardcoded_in_the_js(self):
        # A cheap guard against a string creeping back into the frontend: the
        # copy the JS renders is exactly what this table carries.
        messages = all_form.get_client_data()["messages"]
        assert messages["releaseUnavailable"] == all_form.RELEASE_UNAVAILABLE_ERROR
        assert all(messages.values())


class TestLinux32Drift:
    """
    The matrix is hardcoded, so 32-bit Linux availability can go stale.

    Product details drops the `linux` platform once a channel reaches v145
    (firefox_details.py:90). Today only ESR is still below that, which is why
    `linux` is missing from the `esr` row and present in every other one. When ESR
    rolls past 145, product details stops shipping 32-bit Linux for it and this
    test fails until `linux` is added to the `esr` row.

    Runs against the live product-details singleton on purpose — the point is to
    notice real data moving. The assertion is deliberately one-directional: it
    fails when we offer something with no build, but not when we have stopped
    offering something a stale local snapshot still lists (a dev checkout can be
    many versions behind).
    """

    RELEASE_CHANNELS = {
        "stable": "release",
        "beta": "beta",
        "dev": "devedition",
        "nightly": "nightly",
        "esr": "esr",
        "esr-next": "esr_next",
    }

    @pytest.mark.parametrize("release,channel", sorted(RELEASE_CHANNELS.items()))
    def test_linux32_is_not_offered_without_a_build(self, release, channel):
        if release == "esr-next" and len(firefox_desktop.esr_major_versions) < 2:
            pytest.skip("no ESR Next in product details yet")
        ships_linux32 = "linux" in {slug for slug, _ in firefox_desktop.platforms(channel)}
        if not ships_linux32:
            assert not all_form.is_supported("linux", release)

    def test_esr_115_is_excluded_from_the_check(self):
        # ESR 115 is below v145 yet dropped 32-bit Linux out of band (bug 2040496),
        # so the product-details rule above does not describe it.
        assert not all_form.is_supported("linux", "esr-115")


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------


class TestChoices:
    def test_os_values_include_linux32_because_of_esr(self):
        assert "linux" in all_form.get_os_values()

    def test_os_values_drop_an_os_no_release_supports(self):
        matrix = {release: values + ("linux64",) for release, values in all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE.items()}
        with patch.object(all_form, "UNSUPPORTED_PLATFORMS_BY_RELEASE", matrix):
            assert "linux64" not in all_form.get_os_values()
            grouped = {os_value for _, choices in all_form.get_os_groups() for os_value, _ in choices}
            assert "linux64" not in grouped

    def test_os_values_are_in_display_order(self):
        assert list(all_form.get_os_values()) == list(all_form.OS_LABELS)

    def test_os_groups_are_labelled_and_ordered(self):
        assert [label for label, _ in all_form.get_os_groups()] == ["Apple", "Google", "Microsoft", "Linux"]

    def test_release_choices_are_the_selectable_releases(self):
        assert [value for value, _ in all_form.get_release_choices()] == list(all_form.RELEASE_LABELS)

    def test_secondary_releases_are_not_selectable(self):
        selectable = dict(all_form.get_release_choices())
        for release in all_form.SECONDARY_RELEASES:
            assert release not in selectable

    def test_language_choices_exclude_ja_jp_mac(self):
        # It shares its labels with `ja` and is derived for macOS anyway.
        assert "ja-JP-mac" not in dict(all_form.get_language_choices())
        assert "ja" in dict(all_form.get_language_choices())

    def test_language_choices_are_sorted_by_label(self):
        labels = [label for _, label in all_form.get_language_choices()]
        assert labels == sorted(labels)

    def test_choices_are_not_cached(self):
        # Caching these would freeze version-derived data for the life of the
        # worker and, once the labels are translated, freeze the locale too.
        before = all_form.get_release_choices()
        with patch.dict(all_form.RELEASE_LABELS, {"stable": "Firefox Changed"}):
            assert dict(all_form.get_release_choices())["stable"] == "Firefox Changed"
        assert all_form.get_release_choices() == before


# ---------------------------------------------------------------------------
# get_download_url — a port of FirefoxDownloadURL in the JS
# ---------------------------------------------------------------------------

BOUNCER = settings.BOUNCER_URL


class TestGetDownloadUrl:
    @pytest.mark.parametrize(
        "os_value,release,language,expected",
        [
            ("win64", "stable", "en-US", f"{BOUNCER}?os=win64&product=firefox-latest-ssl&lang=en-US"),
            ("linux64", "stable", "de", f"{BOUNCER}?os=linux64&product=firefox-latest-ssl&lang=de"),
            ("osx", "stable", "fr", f"{BOUNCER}?os=osx&product=firefox-latest-ssl&lang=fr"),
            # MSI and PKG move out of the os param and into the product name.
            ("win64-msi", "stable", "de", f"{BOUNCER}?os=win64&product=firefox-msi-latest-ssl&lang=de"),
            ("win-msi", "stable", "de", f"{BOUNCER}?os=win&product=firefox-msi-latest-ssl&lang=de"),
            ("osx-pkg", "stable", "fr", f"{BOUNCER}?os=osx&product=firefox-pkg-latest-ssl&lang=fr"),
            # Channel segment of the product name.
            ("win64", "beta", "en-US", f"{BOUNCER}?os=win64&product=firefox-beta-latest-ssl&lang=en-US"),
            ("win64", "dev", "en-US", f"{BOUNCER}?os=win64&product=firefox-devedition-latest-ssl&lang=en-US"),
            ("win64", "esr", "en-US", f"{BOUNCER}?os=win64&product=firefox-esr-latest-ssl&lang=en-US"),
            ("win64-msi", "esr", "en-US", f"{BOUNCER}?os=win64&product=firefox-esr-msi-latest-ssl&lang=en-US"),
            ("win64", "esr-next", "en-US", f"{BOUNCER}?os=win64&product=firefox-esr-next-latest-ssl&lang=en-US"),
            ("win64", "esr-115", "en-US", f"{BOUNCER}?os=win64&product=firefox-esr115-latest-ssl&lang=en-US"),
            # Nightly is the only channel with a separate localized product name.
            ("win64", "nightly", "en-US", f"{BOUNCER}?os=win64&product=firefox-nightly-latest-ssl&lang=en-US"),
            ("win64", "nightly", "de", f"{BOUNCER}?os=win64&product=firefox-nightly-latest-l10n-ssl&lang=de"),
            ("win64-msi", "nightly", "de", f"{BOUNCER}?os=win64&product=firefox-nightly-msi-latest-l10n-ssl&lang=de"),
            # Japanese has a dedicated macOS locale code.
            ("osx", "stable", "ja", f"{BOUNCER}?os=osx&product=firefox-latest-ssl&lang=ja-JP-mac"),
            ("osx-pkg", "stable", "ja", f"{BOUNCER}?os=osx&product=firefox-pkg-latest-ssl&lang=ja-JP-mac"),
            ("win64", "stable", "ja", f"{BOUNCER}?os=win64&product=firefox-latest-ssl&lang=ja"),
        ],
    )
    def test_url(self, os_value, release, language, expected):
        assert all_form.get_download_url(os_value, release, language) == expected

    @pytest.mark.parametrize("os_value", sorted(all_form.MOBILE_OS))
    def test_mobile_has_no_bouncer_url(self, os_value):
        assert all_form.get_download_url(os_value, "stable", "en-US") is None

    @pytest.mark.parametrize("release", sorted(all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE))
    @pytest.mark.parametrize("os_value", sorted(set(all_form.OS_LABELS) - all_form.MOBILE_OS))
    def test_url_shape(self, os_value, release):
        if not all_form.is_supported(os_value, release):
            pytest.skip("combination has no build")
        url = all_form.get_download_url(os_value, release, "de")
        assert url.startswith(BOUNCER)
        # Unlike FirefoxDesktop.get_download_url, this never uses the stub
        # installer or the /thanks/ transition page.
        assert "stub" not in url
        assert "/thanks/" not in url
        assert re.fullmatch(r"os=[^&]+&product=[^&]+&lang=[^&]+", url[len(BOUNCER) + 1 :])


class TestSecondaryEsrUrls:
    SUPPORTED = ["win", "win-msi", "win64", "win64-msi", "osx", "osx-pkg", "linux64"]
    UNSUPPORTED = ["linux", "win64-aarch64", "linux64-aarch64"]

    @pytest.mark.parametrize("os_value", SUPPORTED)
    def test_esr_115_offered(self, os_value):
        # MSI and PKG variants keep their own suffix in the product name.
        url = all_form.get_esr_115_download_url(os_value, "esr", "de")
        assert url == all_form.get_download_url(os_value, "esr-115", "de")
        assert "product=firefox-esr115-" in url

    @pytest.mark.parametrize("os_value", UNSUPPORTED)
    def test_esr_115_not_offered_for_unsupported_os(self, os_value):
        assert all_form.get_esr_115_download_url(os_value, "esr", "de") is None

    @pytest.mark.parametrize("release", ["stable", "beta", "dev", "nightly"])
    def test_esr_115_only_alongside_esr(self, release):
        assert all_form.get_esr_115_download_url("win64", release, "de") is None

    @pytest.mark.parametrize("language", sorted(all_form.ESR_115_UNAVAILABLE_LOCALES))
    def test_esr_115_not_offered_for_missing_locales(self, language):
        assert all_form.get_esr_115_download_url("win64", "esr", language) is None

    def test_esr_next_offered_when_a_second_esr_exists(self):
        with patch.object(all_form, "get_esr_next_version", return_value="140.0"):
            url = all_form.get_esr_next_download_url("win64", "esr", "de")
        assert "product=firefox-esr-next-latest-ssl" in url

    def test_esr_next_not_offered_without_a_second_esr(self):
        with patch.object(all_form, "get_esr_next_version", return_value=None):
            assert all_form.get_esr_next_download_url("win64", "esr", "de") is None

    def test_esr_next_not_offered_for_unsupported_os(self):
        with patch.object(all_form, "get_esr_next_version", return_value="140.0"):
            assert all_form.get_esr_next_download_url("linux", "esr", "de") is None


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
        url = all_form.get_store_url("ios", "stable")
        assert "/{country}/" not in url
        assert "{country}" not in url
        # No two-letter segment after the hostname — e.g. apps.apple.com/us/ must not appear.
        assert not re.search(r"apps\.apple\.com/[a-z]{2}/", url)

    def test_campaign_params_present(self):
        url = all_form.get_store_url("ios", "stable")
        assert self.CAMPAIGN_PARAMS in url

    def test_base_url_structure(self):
        url = all_form.get_store_url("ios", "stable")
        assert url.startswith("https://apps.apple.com/app/apple-store/id989804926")

    def test_beta_goes_to_testflight(self):
        assert all_form.get_store_url("ios", "beta") == reverse("firefox.ios.testflight")
        assert all_form.get_store_kind("ios", "beta") == "testflight"

    @pytest.mark.parametrize("release", ["esr", "dev", "nightly"])
    def test_unavailable_releases_return_none(self, release):
        assert all_form.get_store_url("ios", release) is None
        assert all_form.get_store_kind("ios", release) is None


# ---------------------------------------------------------------------------
# get_store_url — Android
# ---------------------------------------------------------------------------


class TestGetStoreUrlAndroid:
    def test_no_hl_param_in_url(self):
        # Language detection is left to Play Store via the browser's Accept-Language header.
        url = all_form.get_store_url("android", "stable")
        assert "hl=" not in url

    @pytest.mark.parametrize(
        "release,setting_name",
        [
            ("stable", "GOOGLE_PLAY_FIREFOX_LINK"),
            ("beta", "GOOGLE_PLAY_FIREFOX_BETA_LINK"),
            ("nightly", "GOOGLE_PLAY_FIREFOX_NIGHTLY_LINK"),
        ],
    )
    def test_each_channel_uses_its_own_listing(self, release, setting_name):
        url = all_form.get_store_url("android", release)
        assert url.startswith(getattr(settings, setting_name))
        assert "referrer=utm_source%3Dwww.firefox.com" in url
        assert "utm_campaign%3Dfirefox-all" in url
        assert all_form.get_store_kind("android", release) == "google-play"

    @pytest.mark.parametrize("release", ["esr", "dev"])
    def test_unavailable_releases_return_none(self, release):
        # Neither ESR nor Developer Edition has an Android channel.
        assert all_form.get_store_url("android", release) is None
        assert all_form.get_store_kind("android", release) is None


# ---------------------------------------------------------------------------
# get_store_url — Microsoft Store
# ---------------------------------------------------------------------------


class TestGetStoreUrlWindows:
    @pytest.mark.parametrize("os_value", sorted(all_form.MS_STORE_OS))
    @pytest.mark.parametrize("release,mz_cn", [("stable", "release"), ("beta", "beta")])
    def test_listed_combinations(self, os_value, release, mz_cn):
        url = all_form.get_store_url(os_value, release)
        assert "mode=mini" in url
        assert "cid=firefox-all" in url
        assert f"mz_cn={mz_cn}" in url
        assert all_form.get_store_kind(os_value, release) == "microsoft-store"

    @pytest.mark.parametrize("os_value", ["win-msi", "win64-msi"])
    def test_msi_has_no_store_listing(self, os_value):
        assert all_form.get_store_url(os_value, "stable") is None
        assert all_form.get_store_kind(os_value, "stable") is None

    @pytest.mark.parametrize("release", ["esr", "dev", "nightly"])
    def test_unlisted_releases_return_none(self, release):
        assert all_form.get_store_url("win64", release) is None


class TestGetStoreUrlDesktop:
    def test_returns_none_for_linux(self):
        assert all_form.get_store_url("linux64", "stable") is None

    def test_returns_none_for_osx(self):
        assert all_form.get_store_url("osx", "stable") is None


# ---------------------------------------------------------------------------
# APK and APT
# ---------------------------------------------------------------------------


class TestApkUrl:
    @pytest.mark.parametrize("release", ["stable", "beta"])
    def test_apk_url_contains_the_version(self, release):
        with patch.object(all_form.firefox_android, "latest_version", return_value="150.0"):
            url = all_form.get_apk_url("android", release)
        assert url == "https://ftp.mozilla.org/pub/fenix/releases/150.0/android/fenix-150.0-android/fenix-150.0.multi.android-universal.apk"

    def test_nightly_has_no_constructible_apk_url(self):
        # Nightly paths carry a build timestamp product details does not expose (bug 1756697).
        assert all_form.get_apk_url("android", "nightly") is None

    @pytest.mark.parametrize("release", ["esr", "dev"])
    def test_unavailable_releases_return_none(self, release):
        assert all_form.get_apk_url("android", release) is None

    def test_non_android_returns_none(self):
        assert all_form.get_apk_url("win64", "stable") is None

    def test_missing_version_returns_none(self):
        with patch.object(all_form.firefox_android, "latest_version", return_value=None):
            assert all_form.get_apk_url("android", "stable") is None


class TestAptUrl:
    @pytest.mark.parametrize("os_value", sorted(all_form.LINUX_OS))
    def test_linux_gets_the_apt_article(self, os_value):
        assert all_form.get_apt_url(os_value) == all_form.LINUX_APT_URL

    @pytest.mark.parametrize("os_value", ["win64", "osx", "android", "ios"])
    def test_everything_else_returns_none(self, os_value):
        assert all_form.get_apt_url(os_value) is None


# ---------------------------------------------------------------------------
# Supporting links
# ---------------------------------------------------------------------------


class TestSupportingLinks:
    @pytest.mark.parametrize(
        "release,kwargs",
        [
            ("stable", None),
            ("beta", {"channel": "beta"}),
            ("dev", {"channel": "developer"}),
            ("nightly", {"channel": "nightly"}),
            ("esr", {"channel": "organizations"}),
        ],
    )
    def test_desktop_links(self, release, kwargs):
        assert all_form.get_release_notes_url("win64", release) == reverse("firefox.notes", kwargs=kwargs)
        assert all_form.get_system_requirements_url("win64", release) == reverse("firefox.sysreq", kwargs=kwargs)

    @pytest.mark.parametrize(
        "os_value,release,kwargs",
        [
            ("android", "stable", {"platform": "android"}),
            ("android", "beta", {"platform": "android", "channel": "beta"}),
            ("android", "nightly", {"platform": "android", "channel": "nightly"}),
            ("ios", "stable", {"platform": "ios"}),
            ("ios", "beta", {"platform": "ios", "channel": "beta"}),
        ],
    )
    def test_mobile_release_notes(self, os_value, release, kwargs):
        assert all_form.get_release_notes_url(os_value, release) == reverse("firefox.notes", kwargs=kwargs)

    @pytest.mark.parametrize("os_value", sorted(all_form.MOBILE_OS))
    def test_mobile_shares_one_system_requirements_article(self, os_value):
        assert all_form.get_system_requirements_url(os_value, "stable") == all_form.MOBILE_SYSREQ_URL

    @pytest.mark.parametrize("release", ["esr", "dev"])
    def test_mobile_releases_without_notes(self, release):
        assert all_form.get_release_notes_url("android", release) is None

    @pytest.mark.parametrize("release", sorted(all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE))
    @pytest.mark.parametrize("os_value", sorted(all_form.OS_LABELS))
    def test_no_lookup_errors_for_any_combination(self, os_value, release):
        all_form.get_release_notes_url(os_value, release)
        all_form.get_system_requirements_url(os_value, release)

    @pytest.mark.parametrize(
        "os_value,expected",
        [
            ("win64-msi", "windows"),
            ("osx-pkg", "macos"),
            ("linux64-aarch64", "linux"),
            ("android", "android"),
            ("ios", "ios"),
        ],
    )
    def test_platform_family(self, os_value, expected):
        assert all_form.get_platform_family(os_value) == expected


# ---------------------------------------------------------------------------
# Selection parsing
# ---------------------------------------------------------------------------


class TestParseSelection:
    def test_recognised_values_pass_through(self):
        selection = all_form.parse_selection({"os": "win64", "release": "beta", "language": "de"})
        assert selection == all_form.Selection(os="win64", release="beta", language="de")
        assert selection.is_valid

    def test_unknown_os_is_dropped(self):
        assert all_form.parse_selection({"os": "lolwut"}).os is None

    def test_unknown_release_is_dropped(self):
        assert all_form.parse_selection({"release": "lolwut"}).release is None

    def test_unknown_language_falls_back_to_the_default(self):
        assert all_form.parse_selection({"language": "lolwut"}, "fr").language == "fr"

    def test_ja_jp_mac_is_not_an_accepted_language(self):
        assert all_form.parse_selection({"language": "ja-JP-mac"}, "en-US").language == "en-US"

    def test_empty_query_string(self):
        selection = all_form.parse_selection({})
        assert selection.os is None
        assert selection.release is None
        assert not selection.is_complete
        assert not selection.has_conflict
        assert not selection.is_valid

    def test_absent_release_falls_back_to_the_rendered_default(self):
        # The release select has no empty option, so the browser shows the first one.
        assert all_form.parse_selection({"os": "win64"}).effective_release == "stable"

    def test_partial_prefill_is_not_a_valid_submission(self):
        assert not all_form.parse_selection({"os": "win64"}).is_valid

    def test_garbage_release_is_not_valid_even_when_the_fallback_would_be(self):
        selection = all_form.parse_selection({"os": "win64", "release": "lolwut", "language": "de"})
        assert not selection.has_conflict  # the fallback, stable, is fine for win64
        assert not selection.is_valid  # but we will not guess on the user's behalf

    def test_conflict_is_reported_against_the_fallback_release(self):
        # 32-bit Linux only ships for ESR, so a bare ?os=linux is already wrong.
        assert all_form.parse_selection({"os": "linux"}).has_conflict

    @pytest.mark.parametrize(
        "os_value,release",
        sorted((os_value, release) for release, os_values in all_form.UNSUPPORTED_PLATFORMS_BY_RELEASE.items() for os_value in os_values),
    )
    def test_every_unsupported_pair_conflicts(self, os_value, release):
        if release in all_form.SECONDARY_RELEASES:
            pytest.skip("not selectable in the form")
        selection = all_form.parse_selection({"os": os_value, "release": release})
        assert selection.has_conflict
        assert not selection.is_valid

    @pytest.mark.parametrize("release", sorted(all_form.RELEASE_LABELS))
    @pytest.mark.parametrize("os_value", sorted(all_form.OS_LABELS))
    def test_every_supported_pair_validates(self, os_value, release):
        if not all_form.is_supported(os_value, release):
            pytest.skip("combination has no build")
        assert all_form.parse_selection({"os": os_value, "release": release, "language": "de"}).is_valid

    @pytest.mark.parametrize("os_value", sorted(all_form.MOBILE_OS))
    def test_mobile_ignores_the_submitted_language(self, os_value):
        # The select cannot be disabled without JS, so a language always arrives.
        selection = all_form.parse_selection({"os": os_value, "release": "stable", "language": "de"})
        assert selection.language == "de"  # still echoed back to the form
        assert selection.effective_language == ""  # but not used for the download

    def test_default_language_prefers_the_request_locale(self):
        assert all_form.default_language("de") == "de"

    def test_default_language_falls_back_to_en_us(self):
        assert all_form.default_language("zz") == "en-US"


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


class TestFormContext:
    def test_choices_and_selection(self):
        selection = all_form.parse_selection({"os": "win64", "release": "beta", "language": "de"})
        ctx = all_form.get_form_context(selection)
        assert ctx["selected_os"] == "win64"
        assert ctx["selected_release"] == "beta"
        assert ctx["selected_language"] == "de"
        assert ctx["release_error"] is None
        assert ctx["has_errors"] is False
        assert ctx["result_url"] == reverse("firefox.all_form.result")

    def test_conflict_produces_an_error_on_the_release_field(self):
        ctx = all_form.get_form_context(all_form.parse_selection({"os": "ios", "release": "esr"}))
        assert ctx["release_error"] == all_form.RELEASE_UNAVAILABLE_ERROR
        assert ctx["has_errors"] is True
        # Both values are still echoed, so the error sits next to what was chosen.
        assert ctx["selected_os"] == "ios"
        assert ctx["selected_release"] == "esr"

    def test_unknown_os_is_blanked_quietly(self):
        ctx = all_form.get_form_context(all_form.parse_selection({"os": "lolwut"}))
        assert ctx["selected_os"] == ""
        assert ctx["has_errors"] is False


def options_for(**data):
    """The download option list for a query string, keyed for easy assertions."""
    selection = all_form.parse_selection(data)
    ctx = all_form.get_download_options(selection)
    return {option["key"]: option for option in ctx["download_options"]}


class TestDownloadOptionList:
    """
    One ordered list per selection, shared by the form page, the result page and
    the JS. See all_form.get_download_option_list.
    """

    def test_order_is_fixed(self):
        # Every option at once: Linux gets APT, ESR gets both extra ESR builds.
        with patch.object(all_form, "get_esr_next_version", return_value="153.0"):
            keys = list(options_for(os="linux64", release="esr", language="de"))
        assert keys == ["apt", "esr-next", "primary", "esr-115"]

    def test_desktop_primary(self):
        options = options_for(os="win64", release="stable", language="de")
        assert options["primary"]["href"] == f"{BOUNCER}?os=win64&product=firefox-latest-ssl&lang=de"
        assert options["primary"]["label"].startswith("Download Firefox ")
        assert options["primary"]["icon"] == "downloads"
        assert options["primary"]["group"] == all_form.GROUP_DOWNLOAD

    def test_windows_offers_the_microsoft_store(self):
        options = options_for(os="win64", release="stable", language="de")
        assert "microsoft-store" in options
        assert "mz_cn=release" in options["microsoft-store"]["href"]

    def test_msi_has_no_store_option(self):
        options = options_for(os="win64-msi", release="stable", language="de")
        assert "microsoft-store" not in options
        assert options["primary"]["href"] == f"{BOUNCER}?os=win64&product=firefox-msi-latest-ssl&lang=de"

    def test_linux_offers_apt_as_an_aside(self):
        options = options_for(os="linux64", release="stable", language="de")
        assert options["apt"]["href"] == all_form.LINUX_APT_URL
        # An aside sits alongside the downloads and never gets an `or` before it.
        assert options["apt"]["group"] == all_form.GROUP_ASIDE

    def test_esr_offers_esr_115(self):
        options = options_for(os="osx", release="esr", language="de")
        assert "product=firefox-esr115-latest-ssl" in options["esr-115"]["href"]
        assert options["esr-115"]["recommendation"] == all_form.ESR_115_RECOMMENDATIONS["macos"]

    def test_esr_on_unsupported_os_has_no_esr_115(self):
        assert "esr-115" not in options_for(os="linux64-aarch64", release="esr", language="de")

    def test_esr_115_is_dropped_for_locales_with_no_build(self):
        # Straight to the list builder: parse_selection would drop `skr` first if
        # this product-details snapshot does not offer it.
        keys = [option["key"] for option in all_form.get_download_option_list("osx", "esr", "skr")]
        assert "esr-115" not in keys
        assert "primary" in keys

    def test_esr_next_when_a_second_esr_exists(self):
        with patch.object(all_form, "get_esr_next_version", return_value="153.0"):
            options = options_for(os="osx", release="esr", language="de")
        assert "product=firefox-esr-next-latest-ssl" in options["esr-next"]["href"]
        # The version comes from product details rather than being written out.
        assert options["esr-next"]["label"] == "Download Firefox ESR 153.0"

    def test_no_esr_next_with_a_single_esr(self):
        with patch.object(all_form, "get_esr_next_version", return_value=None):
            assert "esr-next" not in options_for(os="osx", release="esr", language="de")

    def test_japanese_on_macos(self):
        options = options_for(os="osx", release="esr", language="ja")
        assert options["primary"]["href"].endswith("lang=ja-JP-mac")

    def test_android_primary_is_the_play_store(self):
        options = options_for(os="android", release="nightly", language="de")
        assert options["primary"]["label"] == "Download from the Play Store"
        assert "play.google.com" in options["primary"]["href"]
        # bug 1756697: nightly APK URLs carry a build timestamp we cannot derive.
        assert "apk" not in options

    def test_android_offers_the_apk_where_one_can_be_built(self):
        options = options_for(os="android", release="stable", language="de")
        assert options["apk"]["href"].endswith(".multi.android-universal.apk")

    def test_ios_beta_goes_to_testflight(self):
        options = options_for(os="ios", release="beta", language="de")
        assert options["primary"]["label"] == "Sign up for TestFlight"
        assert options["primary"]["href"] == reverse("firefox.ios.testflight")
        assert options["primary"]["icon"] == "forward"

    def test_an_unusable_pair_has_no_options(self):
        assert all_form.get_download_option_list("ios", "esr", "de") == []

    def test_every_key_has_a_group(self):
        for os_value in all_form.get_os_values():
            for release in all_form.RELEASE_LABELS:
                for option in all_form.get_download_option_list(os_value, release, "de"):
                    assert option["group"] in (all_form.GROUP_DOWNLOAD, all_form.GROUP_ASIDE)


class TestSupportLinks:
    def test_always_three(self):
        assert [link["key"] for link in all_form.get_support_links("win64", "stable")] == [
            "release-notes",
            "system-requirements",
            "privacy",
        ]

    def test_labels_are_the_ones_the_js_gets(self):
        # One definition, read by the result page and serialized for the script.
        labels = {link["key"]: link["label"] for link in all_form.get_support_links("win64", "stable")}
        assert labels == all_form.SUPPORT_LINK_LABELS

    def test_urls_keep_the_locale_prefix(self):
        # The JS used to build these itself and dropped the prefix.
        links = {link["key"]: link["href"] for link in all_form.get_support_links("win64", "beta")}
        assert links["release-notes"].startswith("/en-US/")


class TestDownloadOptionsContext:
    def test_desktop(self):
        ctx = all_form.get_download_options(all_form.parse_selection({"os": "win64", "release": "stable", "language": "de"}))
        assert ctx["is_mobile"] is False
        assert ctx["os_label"] == "Windows 64-bit"
        assert ctx["release_label"] == "Firefox"
        assert ctx["language_label"].startswith("German")

    @pytest.mark.parametrize(
        "release,logo",
        [("stable", "firefox"), ("esr", "firefox"), ("beta", "firefox-beta"), ("dev", "firefox-developer"), ("nightly", "firefox-nightly")],
    )
    def test_one_logo_per_release(self, release, logo):
        # The result page has no controls, so it renders the single right logo
        # rather than all four and a CSS rule to pick between them.
        assert all_form.get_logo(release)["key"] == logo

    def test_esr_version_omits_the_esr_suffix(self):
        # latest_version("esr") returns e.g. "140.12.0esr", which is not a label.
        version = all_form.get_version("osx", "esr")
        assert version == firefox_desktop.esr_minor_versions[0]
        assert "esr" not in version

    def test_android_ignores_the_submitted_language(self):
        ctx = all_form.get_download_options(all_form.parse_selection({"os": "android", "release": "nightly", "language": "de"}))
        assert ctx["is_mobile"] is True
        assert ctx["language_label"] == ""

    def test_form_url_round_trips_the_choices(self):
        ctx = all_form.get_download_options(all_form.parse_selection({"os": "win64", "release": "beta", "language": "de"}))
        assert ctx["form_url"].startswith(reverse("firefox.all_form"))
        assert "os=win64" in ctx["form_url"]
        assert "release=beta" in ctx["form_url"]
        assert "language=de" in ctx["form_url"]


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

FORM_URL = reverse("firefox.all_form")
RESULT_URL = reverse("firefox.all_form.result")


@pytest.mark.django_db
class TestFormView:
    def test_404_when_the_switch_is_off(self, client):
        with override_switch("ALL_FORM", active=False):
            assert client.get(FORM_URL).status_code == 404

    @override_switch("ALL_FORM", active=True)
    def test_bare_request(self, client):
        response = client.get(FORM_URL)
        assert response.status_code == 200
        assert response.context["selected_os"] == ""
        assert response.context["selected_release"] == "stable"
        assert response.context["selected_language"] == "en-US"
        assert response.context["has_errors"] is False

    @override_switch("ALL_FORM", active=True)
    def test_every_logo_is_rendered_for_css_to_choose_from(self, client):
        # All four ship on every request, so changing release costs no fetch.
        # Which one shows is decided in CSS, from the release select.
        response = client.get(FORM_URL)
        for logo in all_form.LOGOS:
            assert f'data-logo="{logo["key"]}"'.encode() in response.content

    @override_switch("ALL_FORM", active=True)
    def test_campaign_params_do_not_change_the_selection(self, client):
        response = client.get(FORM_URL, {"utm_source": "somewhere"})
        assert response.context["selected_os"] == ""
        assert response.context["has_errors"] is False

    @override_switch("ALL_FORM", active=True)
    def test_prefill(self, client):
        response = client.get(FORM_URL, {"os": "win64", "release": "beta", "language": "de"})
        assert response.status_code == 200
        assert response.context["selected_os"] == "win64"
        assert response.context["selected_release"] == "beta"
        assert response.context["selected_language"] == "de"
        assert response.context["has_errors"] is False

    @override_switch("ALL_FORM", active=True)
    def test_partial_prefill_is_quiet(self, client):
        response = client.get(FORM_URL, {"os": "win64"})
        assert response.status_code == 200
        assert response.context["has_errors"] is False

    @override_switch("ALL_FORM", active=True)
    def test_unknown_value_is_dropped_quietly(self, client):
        response = client.get(FORM_URL, {"os": "lolwut"})
        assert response.status_code == 200
        assert response.context["selected_os"] == ""
        assert response.context["has_errors"] is False

    @override_switch("ALL_FORM", active=True)
    def test_conflict_renders_inline(self, client):
        response = client.get(FORM_URL, {"os": "ios", "release": "esr", "language": "de"})
        assert response.status_code == 200
        assert response.context["release_error"] == all_form.RELEASE_UNAVAILABLE_ERROR

    @override_switch("ALL_FORM", active=True)
    def test_client_data_is_embedded_for_the_js(self, client):
        import json

        response = client.get(FORM_URL)
        data = json.loads(response.context["client_data_json"])
        assert set(data["unsupportedPlatformsByRelease"]) == set(JS_RELEASE_VALUES)
        assert b'id="allFormData"' in response.content

    @override_switch("ALL_FORM", active=True)
    @pytest.mark.parametrize(
        "query",
        [
            {},
            {"os": "win64", "release": "stable", "language": "de"},
            {"os": "linux64"},
            {"os": "android", "release": "stable"},
            {"os": "ios", "release": "esr"},
        ],
    )
    def test_the_results_pane_is_always_the_submit_button(self, client, query):
        # Never a rendered option list, however complete the prefill. The form
        # page is where the selection can still change, and nothing without JS
        # could correct a list rendered for the values the page loaded with.
        response = client.get(FORM_URL, query)
        assert response.status_code == 200
        assert b'data-download-option="fallback"' in response.content
        assert b">See download options<" in response.content
        for key in ("primary", "apt", "esr-115", "microsoft-store", "apk"):
            assert f'data-download-option="{key}"'.encode() not in response.content

    @override_switch("ALL_FORM", active=True)
    def test_no_selection_derived_content_in_the_results_pane(self, client):
        response = client.get(FORM_URL, {"os": "android", "release": "beta", "language": "de"})
        content = response.content
        # No support links row: it names one selection too. (Checking for the
        # container, not the labels — the site footer has its own links.)
        assert b'class="c-support-links"' not in content
        # The conflict verdict is the script's to make.
        assert b'class="c-incompatible-choices" hidden' in content
        # And the language note starts hidden even though this is a store app.
        assert b'class="c-language-message" hidden' in content

    @override_switch("ALL_FORM", active=True)
    def test_no_selection_state_on_the_host_element(self, client):
        # The script sets these once it runs. Server-set they would be one more
        # copy of the selection to go stale.
        response = client.get(FORM_URL, {"os": "win64", "release": "nightly"})
        assert b"<firefox-download-form>" in response.content

    @override_switch("ALL_FORM", active=True)
    def test_a_prefill_still_selects_the_options(self, client):
        # What a prefill does do: come back with the right values in the selects.
        response = client.get(FORM_URL, {"os": "win64", "release": "nightly", "language": "de"})
        assert response.context["selected_os"] == "win64"
        assert response.context["selected_release"] == "nightly"
        assert response.context["selected_language"] == "de"
        assert b'value="win64" selected' in response.content

    @override_switch("ALL_FORM", active=True)
    def test_a_partial_prefill_falls_back_to_the_rendered_release(self, client):
        response = client.get(FORM_URL, {"os": "linux64"})
        assert response.context["selected_release"] == all_form.DEFAULT_RELEASE


@pytest.mark.django_db
class TestResultView:
    def test_404_when_the_switch_is_off(self, client):
        with override_switch("ALL_FORM", active=False):
            assert client.get(RESULT_URL, {"os": "win64", "release": "stable", "language": "de"}).status_code == 404

    @override_switch("ALL_FORM", active=True)
    def test_valid_submission(self, client):
        response = client.get(RESULT_URL, {"os": "win64", "release": "stable", "language": "de"})
        assert response.status_code == 200
        options = {option["key"]: option for option in response.context["download_options"]}
        assert options["primary"]["href"] == f"{BOUNCER}?os=win64&product=firefox-latest-ssl&lang=de"
        assert b'data-download-option="primary"' in response.content
        # Unlike the form page, this one does render the support links: it has no
        # controls, so the row cannot fall out of step with anything.
        assert b'class="c-support-links"' in response.content
        assert all_form.SUPPORT_LINK_LABELS["privacy"].encode() in response.content

    @override_switch("ALL_FORM", active=True)
    def test_bare_request_bounces_to_the_form(self, client):
        response = client.get(RESULT_URL)
        assert response.status_code == 303
        assert response["Location"] == reverse("firefox.all_form")

    @override_switch("ALL_FORM", active=True)
    def test_conflict_bounces_with_the_query_string(self, client):
        response = client.get(RESULT_URL, {"os": "ios", "release": "esr", "language": "de", "utm_source": "somewhere"})
        assert response.status_code == 303
        location = response["Location"]
        assert location.startswith(reverse("firefox.all_form") + "?")
        for param in ("os=ios", "release=esr", "language=de", "utm_source=somewhere"):
            assert param in location

    @override_switch("ALL_FORM", active=True)
    def test_bounce_does_not_loop(self, client):
        response = client.get(RESULT_URL, {"os": "ios", "release": "esr"}, follow=True)
        assert response.status_code == 200
        assert len(response.redirect_chain) == 1
        assert response.context["release_error"] == all_form.RELEASE_UNAVAILABLE_ERROR

    @override_switch("ALL_FORM", active=True)
    def test_bounce_keeps_the_locale_prefix(self, client):
        response = client.get(RESULT_URL.replace("/en-US/", "/de/"), {"os": "ios", "release": "esr"})
        assert response.status_code == 303
        assert response["Location"].startswith(FORM_URL.replace("/en-US/", "/de/"))

    @override_switch("ALL_FORM", active=True)
    def test_post_is_rejected(self, client):
        response = client.post(RESULT_URL, {"os": "win64", "release": "stable", "language": "de"})
        assert response.status_code == 405
