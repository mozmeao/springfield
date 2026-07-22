# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import functools
from urllib.parse import quote, urlencode

from django.conf import settings

from product_details import product_details

from springfield.firefox.firefox_details import firefox_android, firefox_desktop

_FENIX_FTP_BASE = "https://ftp.mozilla.org/pub/fenix/releases"

# Fixed URL for the Linux APT installation help article (same for all Linux variants/channels).
LINUX_APT_URL = "https://support.mozilla.org/en-US/kb/install-firefox-linux#w_install-firefox-deb-package-for-debian-based-distributions"

# Maps our form channel keys to the channel names used by firefox_desktop.platforms().
_CHANNEL_DESKTOP_MAP = {
    "release": "release",
    "esr": "esr",
    "esr_next": "esr_next",
    "beta": "beta",
    "dev": "alpha",
    "nightly": "nightly",
}

# Slugs not in firefox_desktop.platform_labels (osx-pkg, win-msi, win64-msi) inherit
# their channel availability from their parent slug.
_SLUG_AVAILABILITY_PARENT = {
    "osx-pkg": "osx",
    "win-msi": "win",
    "win64-msi": "win64",
}

# Actions available for each desktop slug when it IS present for a given channel.
_DESKTOP_WHEN_AVAILABLE = {
    "linux": {
        "release": "download apt",
        "esr": "download apt",
        "esr_next": "download apt",
        "beta": "download apt",
        "dev": "download apt",
        "nightly": "download apt",
    },
    "linux64": {
        "release": "download apt",
        "esr": "download apt",
        "esr_next": "download apt",
        "beta": "download apt",
        "dev": "download apt",
        "nightly": "download apt",
    },
    "linux64-aarch64": {
        "release": "download apt",
        "esr": "download apt",
        "esr_next": "download apt",
        "beta": "download apt",
        "dev": "download apt",
        "nightly": "download apt",
    },
    "osx": {"release": "download", "esr": "download", "esr_next": "download", "beta": "download", "dev": "download", "nightly": "download"},
    "osx-pkg": {"release": "download", "esr": "download", "esr_next": "download", "beta": "download", "dev": "download", "nightly": "download"},
    "win": {
        "release": "download store",
        "esr": "download",
        "esr_next": "download",
        "beta": "download store",
        "dev": "download",
        "nightly": "download",
    },
    "win-msi": {"release": "download", "esr": "download", "esr_next": "download", "beta": "download", "dev": "download", "nightly": "download"},
    "win64": {
        "release": "download store",
        "esr": "download",
        "esr_next": "download",
        "beta": "download store",
        "dev": "download",
        "nightly": "download",
    },
    "win64-msi": {"release": "download", "esr": "download", "esr_next": "download", "beta": "download", "dev": "download", "nightly": "download"},
    "win64-aarch64": {
        "release": "download store",
        "esr": "download",
        "esr_next": "download",
        "beta": "download store",
        "dev": "download",
        "nightly": "download",
    },
}


# Inverse of _CHANNEL_DESKTOP_MAP: firefox_desktop channel name → form channel key (e.g. "alpha" → "dev").
_DESKTOP_CHANNEL_MAP = {v: k for k, v in _CHANNEL_DESKTOP_MAP.items()}


@functools.cache
def get_installer_channel_actions():
    """
    Build per-channel action strings for each OS option.

    Desktop platform availability is derived from firefox_desktop.platforms() per channel,
    so changes in product details (e.g. linux32 dropped after v145, firefox_details.py:90)
    are reflected automatically without any changes here.
    """
    available = {
        channel: {slug for slug, _ in firefox_desktop.platforms(desktop_channel)} for channel, desktop_channel in _CHANNEL_DESKTOP_MAP.items()
    }
    result = {
        "android": {"release": "apk store", "esr": "", "esr_next": "", "beta": "apk store", "dev": "", "nightly": "store"},
        "ios": {"release": "store", "esr": "", "esr_next": "", "beta": "", "dev": "", "nightly": ""},
    }
    for slug, when_available in _DESKTOP_WHEN_AVAILABLE.items():
        parent = _SLUG_AVAILABILITY_PARENT.get(slug, slug)
        result[slug] = {channel: (when_available[channel] if parent in available[channel] else "") for channel in _CHANNEL_DESKTOP_MAP}
    return result


# Display order for installers
_ALL_INSTALLERS = [
    ("android", "Android"),  # no platform slug in product-details, we made this up
    ("ios", "iOS"),  # no platform slug in product-details, we made this up
    ("linux", "Linux 32-bit"),
    ("linux64", "Linux 64-bit"),
    ("linux64-aarch64", "Linux ARM64/AArch64"),
    ("osx", "macOS"),
    ("osx-pkg", "macOS - PKG"),  # no platform slug in product-details, we made this up
    ("win", "Windows 32-bit"),
    ("win-msi", "Windows 32-bit MSI"),
    ("win64", "Windows 64-bit"),
    ("win64-msi", "Windows 64-bit MSI"),
    ("win64-aarch64", "Windows ARM64/AArch64"),
]

# Slugs with no firefox_desktop.platform_labels entry — always shown.
_ALWAYS_SHOWN = frozenset({"android", "ios"})


@functools.cache
def get_installers():
    """
    Return installer (slug, label) pairs available in at least one release channel.

    Desktop slug availability is derived from firefox_desktop.platforms() per channel,
    so options that drop out of product details (e.g. linux32 after v145) disappear
    from the form automatically.
    """
    available_any = set()
    for desktop_channel in _CHANNEL_DESKTOP_MAP.values():
        available_any.update(slug for slug, _ in firefox_desktop.platforms(desktop_channel))
    return [(slug, label) for slug, label in _ALL_INSTALLERS if slug in _ALWAYS_SHOWN or _SLUG_AVAILABILITY_PARENT.get(slug, slug) in available_any]


@functools.cache
def get_release_types():
    """
    Return release type (value, label) pairs for the form dropdown.

    Values match bouncer product slugs (firefox_details.py:264-284).
    ESR Next is inserted after ESR when available. When both ESR versions are present,
    major version numbers are included in the labels to disambiguate.
    """
    esr_major = firefox_desktop.esr_major_versions  # e.g. [128] or [128, 140]
    if len(esr_major) >= 2:
        esr_label = f"Firefox ESR {esr_major[0]}"
        esr_next_entry = [("firefox-esr-next-latest-ssl", f"Firefox ESR {esr_major[1]}")]
    else:
        esr_label = "Firefox ESR"
        esr_next_entry = []
    return [
        ("firefox-latest-ssl", "Firefox"),
        ("firefox-esr-latest-ssl", esr_label),
        *esr_next_entry,
        ("firefox-beta-latest-ssl", "Firefox Beta"),
        ("firefox-devedition-latest-ssl", "Firefox Developer Edition"),
        ("firefox-nightly-latest-ssl", "Firefox Nightly"),
    ]


# Maps form release slugs (bouncer product names) to firefox_desktop channel names.
# Used for language validation via get_filtered_full_builds().
_RELEASE_CHANNEL_MAP = {
    "firefox-latest-ssl": "release",
    "firefox-esr-latest-ssl": "esr",
    "firefox-esr-next-latest-ssl": "esr_next",
    "firefox-beta-latest-ssl": "beta",
    "firefox-devedition-latest-ssl": "alpha",
    "firefox-nightly-latest-ssl": "nightly",
}

# Maps form release slugs to Firefox Android channels. ESR and Developer Edition
# have no Android equivalent.
_ANDROID_CHANNEL_MAP = {
    "firefox-latest-ssl": "release",
    "firefox-beta-latest-ssl": "beta",
    "firefox-nightly-latest-ssl": "nightly",
}

# iOS Firefox is release-only on the App Store.
_IOS_CHANNEL_MAP = {
    "firefox-latest-ssl": "release",
}

# Settings key for each Android channel's Play Store URL (different package IDs per channel).
_ANDROID_PLAY_STORE_SETTING = {
    "release": "GOOGLE_PLAY_FIREFOX_LINK",
    "beta": "GOOGLE_PLAY_FIREFOX_BETA_LINK",
    "nightly": "GOOGLE_PLAY_FIREFOX_NIGHTLY_LINK",
}

# Windows slugs that have a Microsoft Store listing (MSI variants do not).
_WINDOWS_MS_STORE_SLUGS = frozenset({"win", "win64", "win64-aarch64"})

# Maps release slugs to (settings product key, channel label) for MS Store URLs.
# ESR, Developer Edition, and Nightly have no MS Store equivalent.
_RELEASE_TO_MS_STORE = {
    "firefox-latest-ssl": ("FIREFOX", "release"),
    "firefox-beta-latest-ssl": ("FIREFOX_BETA", "beta"),
}


def get_valid_language(os_slug, release, language):
    """
    Validate the language against product details for the given OS + release.

    Returns (validated_language, is_valid):
      True  — language confirmed available for this channel
      False — language unavailable; falls back to en-US
      None  — validation not possible (android, ios — universal/multi-locale builds)
    """
    if os_slug in ("android", "ios"):
        return language, None
    channel = _RELEASE_CHANNEL_MAP.get(release)
    if not channel:
        return language, None
    builds = firefox_desktop.get_filtered_full_builds(channel)
    if any(b["locale"] == language for b in builds):
        return language, True
    return language, False


def get_android_apk_url(release):
    """Return the ftp.mozilla.org universal APK URL for the given release slug, or None if not applicable."""
    channel = _ANDROID_CHANNEL_MAP.get(release)
    # Nightly URLs include a build timestamp in the directory name (e.g.
    # /pub/fenix/nightly/2026/07/2026-07-01-09-27-14-fenix-154.0a1-android/) which
    # is not available from product details, so nightly cannot be constructed here.
    # Bug #1756697
    if not channel or channel == "nightly":
        return None
    version = firefox_android.latest_version(channel)
    if not version:
        return None
    return f"{_FENIX_FTP_BASE}/{version}/android/fenix-{version}-android/fenix-{version}.multi.android-universal.apk"


def get_apt_url(os_slug, release):
    """Return the APT help article URL if this os+release supports apt, else None."""
    channel = _DESKTOP_CHANNEL_MAP.get(_RELEASE_CHANNEL_MAP.get(release, ""), "")
    actions = _DESKTOP_WHEN_AVAILABLE.get(os_slug, {}).get(channel, "")
    return LINUX_APT_URL if "apt" in actions else None


def get_store_url(os_slug, release):
    """Return the appropriate store URL with attribution, or None if not applicable."""
    if os_slug == "android":
        channel = _ANDROID_CHANNEL_MAP.get(release)
        if not channel:
            return None
        base_url = getattr(settings, _ANDROID_PLAY_STORE_SETTING[channel])
        referrer = quote("utm_source=www.firefox.com&utm_medium=referral&utm_campaign=firefox-all")
        # No hl= param: Play Store detects language from the browser's Accept-Language header.
        return f"{base_url}&referrer={referrer}"
    if os_slug == "ios":
        if not _IOS_CHANNEL_MAP.get(release):
            return None
        # Country-less App Store URL: Apple routes by the user's Apple Account region
        base_url = settings.APPLE_APPSTORE_FIREFOX_LINK.replace("/{country}/", "/")
        return f"{base_url}?mz_pr=firefox_mobile&pt=373246&ct=firefox-all&mt=8"
    if os_slug in _WINDOWS_MS_STORE_SLUGS:
        mapping = _RELEASE_TO_MS_STORE.get(release)
        if mapping:
            product_key, channel = mapping
            base_url = getattr(settings, f"MICROSOFT_WINDOWS_STORE_{product_key}_WEB_LINK")
            return f"{base_url}?{urlencode({'mode': 'mini', 'cid': 'firefox-all', 'mz_cn': channel})}"
    return None


def get_download_url(os_slug, release, language):
    if os_slug in ("android", "ios"):
        return None
    if os_slug == "osx-pkg":
        # PKG uses os=osx with -pkg- inserted into the product slug (order matters for bouncer).
        pkg_release = release.replace("-latest-ssl", "-pkg-latest-ssl")
        return settings.BOUNCER_URL + "?" + urlencode([("product", pkg_release), ("os", "osx"), ("lang", language)])
    return settings.BOUNCER_URL + "?" + urlencode([("product", release), ("os", os_slug), ("lang", language)])


@functools.cache
def get_languages():
    # Every language in product_details as sorted (locale, "English - Native") tuples.
    return sorted(
        ((locale, f"{names['English']} - {names['native']}") for locale, names in product_details.languages.items()),
        key=lambda item: item[1],
    )
