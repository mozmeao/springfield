# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Backend for the /firefox/download/all-form/ download picker.

The vocabulary here (OS values, release values, and the unsupported-platform
matrix) is authoritative and mirrors media/js/firefox/all-form/all-form.js.
Neither side may change without the other. The eventual plan is for the JS to
read `get_unsupported_platforms_json()` out of the page instead of keeping its
own copy.

Nothing in this module is cached. Label strings will become `ftl()` calls, which
makes per-process caching locale-poisoning, and everything version-derived would
otherwise be frozen to whatever product details said when the worker booted.
The underlying product-details lookups are already cached.
"""

import json
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from django.conf import settings

from product_details import product_details

from springfield.base.urlresolvers import reverse
from springfield.firefox.firefox_details import firefox_android, firefox_desktop, firefox_ios

# The release the form falls back to, matching the first <option> the browser
# selects when no release was submitted.
DEFAULT_RELEASE = "stable"

# Every OS option, in display order. Keys are bouncer platform slugs, except
# `ios`/`android` (store apps).
OS_VALUES = (
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

# The three options firefox_desktop.platform_labels has no entry for: the two
# store apps, and the macOS PKG build, which bouncer serves but product details
# does not list.
_EXTRA_OS_LABELS = {
    "ios": "iOS",
    "android": "Android",
    "osx-pkg": "macOS - PKG",
}

# Labels come from firefox_desktop wherever it has one, so the wording cannot
# drift from the rest of the site. Safe to build at import: platform_labels is a
# class attribute, not live product-details data, so there is nothing to go stale
# — unlike the version lookups further down, which are deliberately per-request.
OS_LABELS = {os_value: _EXTRA_OS_LABELS.get(os_value) or firefox_desktop.platform_labels[os_value] for os_value in OS_VALUES}

# How the OS options are grouped in the form, kept here rather than in the
# template so the grouping cannot drift from OS_LABELS.
OS_GROUPS = (
    ("Apple", ("ios", "osx", "osx-pkg")),
    ("Google", ("android",)),
    ("Microsoft", ("win", "win-msi", "win64", "win64-msi", "win64-aarch64")),
    ("Linux", ("linux", "linux64", "linux64-aarch64")),
)

# Mobile apps: installed from a store, multi-locale, so the chosen language is
# ignored for these.
MOBILE_OS = frozenset({"ios", "android"})
LINUX_OS = frozenset({"linux", "linux64", "linux64-aarch64"})
# Windows options with a Microsoft Store listing — never the MSI variants.
MS_STORE_OS = frozenset({"win", "win64", "win64-aarch64"})

# Selectable release types, in display order.
#
# Not taken from firefox_desktop.channel_labels: that map is keyed by
# product-details channel rather than by the values this form submits, and two of
# its strings are wrong for a download picker — it calls ESR "Firefox Extended
# Support Release" and Developer Edition "Developer Edition" without the brand.
RELEASE_LABELS = {
    "stable": "Firefox",
    "esr": "Firefox ESR",
    "beta": "Firefox Beta",
    "dev": "Firefox Developer Edition",
    "nightly": "Firefox Nightly",
}

# Releases that are never selectable: they are offered as extra download links
# alongside `esr`.
SECONDARY_RELEASES = ("esr-next", "esr-115")

# Which OS options each release has no build for. This is the source of truth for
# availability and is serialized into the form page for the JS.
#
# It is deliberately hardcoded rather than derived from firefox_desktop.platforms(),
# which only knows about the "32-bit Linux ends with v145" rule (firefox_details.py:90).
# That rule is why `linux` is absent from the `esr` row below and present in every
# other one; `linux` must be added to `esr` by hand once ESR moves past 145.
# test_all_form.py has a drift alarm for exactly that.
UNSUPPORTED_PLATFORMS_BY_RELEASE = {
    "stable": ("linux",),
    "esr": ("ios", "android"),
    "esr-next": ("ios", "android", "linux"),
    "esr-115": ("ios", "android", "win64-aarch64", "linux", "linux64-aarch64"),
    "beta": ("linux",),
    "dev": ("ios", "android", "linux", "osx-pkg"),
    "nightly": ("ios", "linux"),
}

# Fixed URL for the Linux APT installation help article (same for all Linux variants/channels).
LINUX_APT_URL = "https://support.mozilla.org/en-US/kb/install-firefox-linux#w_install-firefox-deb-package-for-debian-based-distributions"

# Android and iOS share one system requirements article.
MOBILE_SYSREQ_URL = "https://support.mozilla.org/kb/will-firefox-work-my-mobile-device"

PRIVACY_URL = "https://www.mozilla.org/privacy/firefox/"

# ESR 115 has no builds for these locales (mozilla/bedrock#15437).
ESR_115_UNAVAILABLE_LOCALES = frozenset({"sat", "skr"})

_FENIX_FTP_BASE = "https://ftp.mozilla.org/pub/fenix/releases"

# Release value -> the channel segment of the bouncer product name.
_RELEASE_TO_BOUNCER_CHANNEL = {
    "stable": "",
    "beta": "beta",
    "nightly": "nightly",
    "dev": "devedition",
    "esr": "esr",
    "esr-next": "esr-next",
    "esr-115": "esr115",
}

# Release value -> firefox_desktop channel name, for version lookups.
# `esr-115` has no product-details channel at all (FirefoxDesktop.version_map has
# no esr115 key), so it is absent here and has no version string.
_RELEASE_TO_DESKTOP_CHANNEL = {
    "stable": "release",
    "beta": "beta",
    "dev": "devedition",
    "nightly": "nightly",
    "esr": "esr",
    "esr-next": "esr_next",
}

# Release value -> mobile channel, per OS. ESR and Developer Edition have no
# mobile equivalent, and iOS ships release and beta only.
_RELEASE_TO_MOBILE_CHANNEL = {
    "android": {"stable": "release", "beta": "beta", "nightly": "nightly"},
    "ios": {"stable": "release", "beta": "beta"},
}

# Settings key for each Android channel's Play Store URL (different package IDs per channel).
_ANDROID_PLAY_STORE_SETTING = {
    "release": "GOOGLE_PLAY_FIREFOX_LINK",
    "beta": "GOOGLE_PLAY_FIREFOX_BETA_LINK",
    "nightly": "GOOGLE_PLAY_FIREFOX_NIGHTLY_LINK",
}

# Releases with a Microsoft Store listing, and the settings key for each.
_RELEASE_TO_MS_STORE_SETTING = {
    "stable": "MICROSOFT_WINDOWS_STORE_FIREFOX_WEB_LINK",
    "beta": "MICROSOFT_WINDOWS_STORE_FIREFOX_BETA_WEB_LINK",
}

# `channel` kwarg for the firefox.notes / firefox.sysreq URLs (urls.py:73,79).
# `stable` takes no kwarg, and all three ESR flavours share the organizations pages.
_RELEASE_TO_NOTES_CHANNEL = {
    "beta": "beta",
    "dev": "developer",
    "nightly": "nightly",
    "esr": "organizations",
    "esr-next": "organizations",
    "esr-115": "organizations",
}

RELEASE_UNAVAILABLE_ERROR = "Chosen release type is not available for this platform."

# ---------------------------------------------------------------------------
# Copy
#
# Every user-visible string the picker renders, on the server or in the browser.
# The JS reads these out of get_client_data() rather than holding its own copies,
# so this is the only place any of them are written. They become `ftl()` calls
# later; keeping them together is what makes that a contained change.
# ---------------------------------------------------------------------------

MESSAGES = {
    "releaseUnavailable": RELEASE_UNAVAILABLE_ERROR,
    # The word between two download options that are alternatives to each other.
    # Not keyed "or": Jinja cannot reach that as an attribute, it is a keyword.
    "divider": "or",
    # Shown under the language select once it has been disabled for a store app.
    "languageIgnored": "Language can be configured after installation.",
    # The whole results pane, when the two choices cannot go together.
    "conflict": "There are no downloads for this combination. Pick a different release type, or a different operating system.",
    # The submit button, which is the results pane until a platform is known.
    "fallback": "See download options",
}

SUPPORT_LINK_LABELS = {
    "release-notes": "Release Notes",
    "system-requirements": "System Requirements",
    "privacy": "Privacy Policy",
}

# ESR 115 is offered to people whose operating system newer Firefox has dropped,
# so the reason to pick it differs per platform family.
ESR_115_RECOMMENDATIONS = {
    "windows": "Recommended for Windows 7/8/8.1",
    "macos": "Recommended for macOS 10.12–10.14",
    "linux": "Recommended for older operating systems",
}

# ---------------------------------------------------------------------------
# Download option vocabulary
#
# Duplicated in all-form.js, which switches on these keys. Nothing else is.
# ---------------------------------------------------------------------------

# All four logos are rendered on the form page so the visible one can change
# without a network fetch mid-interaction. Which one shows is decided entirely in
# CSS, from which release option is `:checked` — so it follows the select whether
# or not the script is running.
LOGOS = (
    {"key": "firefox", "file": "img/logos/firefox/firefox-logo.svg", "alt": "Firefox"},
    {"key": "firefox-beta", "file": "img/logos/firefox/firefox-logo-beta.svg", "alt": "Firefox Beta"},
    {"key": "firefox-developer", "file": "img/logos/firefox/firefox-logo-developer.svg", "alt": "Firefox Developer Edition"},
    {"key": "firefox-nightly", "file": "img/logos/firefox/firefox-logo-nightly.svg", "alt": "Firefox Nightly"},
)

# Which logo a release shows. ESR ships under the standard logo. The form page
# does not use this — its CSS keys off the select instead — but the result page
# has no controls, so one logo is rendered and this picks it.
RELEASE_LOGOS = {
    "stable": "firefox",
    "esr": "firefox",
    "beta": "firefox-beta",
    "dev": "firefox-developer",
    "nightly": "firefox-nightly",
}

OPTION_FALLBACK = "fallback"
OPTION_APT = "apt"
OPTION_ESR_NEXT = "esr-next"
OPTION_PRIMARY = "primary"
OPTION_ESR_115 = "esr-115"
OPTION_APK = "apk"
OPTION_MICROSOFT_STORE = "microsoft-store"

# `or` dividers go between adjacent DOWNLOAD options, which are alternative ways
# to get the same thing. An ASIDE sits alongside the whole set and never gets one.
GROUP_DOWNLOAD = "download"
GROUP_ASIDE = "aside"

_OPTION_GROUPS = {
    OPTION_FALLBACK: GROUP_ASIDE,
    OPTION_APT: GROUP_ASIDE,
    OPTION_ESR_NEXT: GROUP_DOWNLOAD,
    OPTION_PRIMARY: GROUP_DOWNLOAD,
    OPTION_ESR_115: GROUP_DOWNLOAD,
    OPTION_APK: GROUP_DOWNLOAD,
    OPTION_MICROSOFT_STORE: GROUP_DOWNLOAD,
}


# ---------------------------------------------------------------------------
# Availability and choices
# ---------------------------------------------------------------------------


def is_supported(os_value, release):
    """Whether the given OS option has a build for the given release."""
    return os_value not in UNSUPPORTED_PLATFORMS_BY_RELEASE[release]


def get_os_values():
    """OS values supported by at least one release, in display order."""
    return tuple(os_value for os_value in OS_LABELS if any(is_supported(os_value, release) for release in UNSUPPORTED_PLATFORMS_BY_RELEASE))


def get_os_groups():
    """(group label, [(value, label), ...]) pairs for the OS field's optgroups."""
    available = get_os_values()
    groups = []
    for group_label, os_values in OS_GROUPS:
        choices = [(os_value, OS_LABELS[os_value]) for os_value in os_values if os_value in available]
        if choices:
            groups.append((group_label, choices))
    return groups


def get_release_choices():
    """(value, label) pairs for the release field."""
    return list(RELEASE_LABELS.items())


def is_offered_language(language):
    """
    Whether the language field offers this locale.

    `ja-JP-mac` is excluded: it shares its labels with `ja`, so it would render as
    a second, indistinguishable "Japanese" option, and it is only ever correct for
    macOS — where get_download_url() derives it from `ja` anyway.
    """
    return language != "ja-JP-mac" and language in product_details.languages


def get_language_choices():
    """(locale, "English - Native") pairs for the language field, sorted by label."""
    return sorted(
        ((locale, f"{names['English']} - {names['native']}") for locale, names in product_details.languages.items() if is_offered_language(locale)),
        key=lambda item: item[1],
    )


def get_language_label(language):
    names = product_details.languages.get(language)
    return f"{names['English']} - {names['native']}" if names else language


def get_unsupported_platforms_json():
    """
    The availability matrix, for the JS to read out of the form page.

    Every release key is always present, including ones that are not selectable:
    the JS indexes this map directly, so a missing key is a TypeError.
    """
    return json.dumps({release: list(os_values) for release, os_values in UNSUPPORTED_PLATFORMS_BY_RELEASE.items()})


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def get_version(os_value, release):
    """The latest version string for an OS + release, or None if there isn't one."""
    if os_value in MOBILE_OS:
        channel = _RELEASE_TO_MOBILE_CHANNEL[os_value].get(release)
        if not channel:
            return None
        product = firefox_android if os_value == "android" else firefox_ios
        return product.latest_version(channel)
    if release == "esr":
        return get_esr_version()
    if release == "esr-next":
        return get_esr_next_version()
    channel = _RELEASE_TO_DESKTOP_CHANNEL.get(release)
    return firefox_desktop.latest_version(channel) if channel else None


def get_esr_version():
    """Current ESR version without the "esr" suffix, e.g. "140.12.0"."""
    versions = firefox_desktop.esr_minor_versions
    return versions[0] if versions else None


def get_esr_next_version():
    """Next ESR version without the "esr" suffix, or None when there isn't one yet."""
    versions = firefox_desktop.esr_minor_versions
    return versions[1] if len(versions) >= 2 else None


# ---------------------------------------------------------------------------
# Download URLs
# ---------------------------------------------------------------------------


def get_download_url(os_value, release, language):
    """
    Build a download.mozilla.org URL, or None for mobile (store installs).

    This is a port of the FirefoxDownloadURL class in
    media/js/firefox/all-form/all-form.js and deliberately not
    FirefoxDesktop.get_download_url, which emits stub installers, routes through
    the /thanks/ transition page, and knows nothing about osx-pkg or esr115.
    """
    if os_value in MOBILE_OS:
        return None

    bouncer_os = os_value[:-4] if os_value.endswith(("-msi", "-pkg")) else os_value

    name = ["firefox", _RELEASE_TO_BOUNCER_CHANNEL[release]]
    if os_value.endswith("-pkg"):
        name.append("pkg")
    if os_value.endswith("-msi"):
        name.append("msi")
    name.append("latest")
    if release == "nightly" and language != "en-US":
        # Nightly uses a different product name for localized builds.
        name.append("l10n")
    name.append("ssl")
    product = "-".join(part for part in name if part)

    # The macOS build for Japanese has its own locale code.
    lang = "ja-JP-mac" if bouncer_os == "osx" and language == "ja" else language

    # Order matters: bouncer needs lang last.
    return settings.BOUNCER_URL + "?" + urlencode([("os", bouncer_os), ("product", product), ("lang", lang)])


def get_esr_115_download_url(os_value, release, language):
    """ESR 115 download URL, offered as a secondary option alongside ESR."""
    if release != "esr" or not is_supported(os_value, "esr-115") or language in ESR_115_UNAVAILABLE_LOCALES:
        return None
    return get_download_url(os_value, "esr-115", language)


def get_esr_next_download_url(os_value, release, language):
    """Next-ESR download URL, offered as a secondary option alongside ESR."""
    if release != "esr" or not is_supported(os_value, "esr-next") or not get_esr_next_version():
        return None
    return get_download_url(os_value, "esr-next", language)


def get_apk_url(os_value, release):
    """The ftp.mozilla.org universal APK URL, or None if not applicable."""
    if os_value != "android":
        return None
    channel = _RELEASE_TO_MOBILE_CHANNEL["android"].get(release)
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


def get_apt_url(os_value):
    """The APT help article URL for Linux options, else None."""
    return LINUX_APT_URL if os_value in LINUX_OS else None


def get_store_url(os_value, release):
    """The store URL with attribution for this OS + release, or None."""
    if os_value == "android":
        channel = _RELEASE_TO_MOBILE_CHANNEL["android"].get(release)
        if not channel:
            return None
        base_url = getattr(settings, _ANDROID_PLAY_STORE_SETTING[channel])
        referrer = quote("utm_source=www.firefox.com&utm_medium=referral&utm_campaign=firefox-all")
        # No hl= param: Play Store detects language from the browser's Accept-Language header.
        return f"{base_url}&referrer={referrer}"
    if os_value == "ios":
        if release == "beta":
            # iOS betas are distributed through TestFlight, which we explain first.
            return reverse("firefox.ios.testflight")
        if release != "stable":
            return None
        # Country-less App Store URL: Apple routes by the user's Apple Account region
        base_url = settings.APPLE_APPSTORE_FIREFOX_LINK.replace("/{country}/", "/")
        return f"{base_url}?mz_pr=firefox_mobile&pt=373246&ct=firefox-all&mt=8"
    if os_value in MS_STORE_OS:
        setting = _RELEASE_TO_MS_STORE_SETTING.get(release)
        if setting:
            base_url = getattr(settings, setting)
            return f"{base_url}?{urlencode({'mode': 'mini', 'cid': 'firefox-all', 'mz_cn': release_to_ms_store_channel(release)})}"
    return None


def release_to_ms_store_channel(release):
    """The `mz_cn` value the Microsoft Store listing expects."""
    return "release" if release == "stable" else release


def get_store_kind(os_value, release):
    """Which store `get_store_url` points at, so templates need not match on URLs."""
    if os_value == "android":
        return "google-play" if release in _RELEASE_TO_MOBILE_CHANNEL["android"] else None
    if os_value == "ios":
        if release == "beta":
            return "testflight"
        return "apple-app-store" if release == "stable" else None
    if os_value in MS_STORE_OS and release in _RELEASE_TO_MS_STORE_SETTING:
        return "microsoft-store"
    return None


# ---------------------------------------------------------------------------
# Supporting links
# ---------------------------------------------------------------------------


def get_release_notes_url(os_value, release):
    """Release notes URL for this OS + release, or None if there are none."""
    if os_value in MOBILE_OS:
        channel = _RELEASE_TO_MOBILE_CHANNEL[os_value].get(release)
        if not channel:
            return None
        kwargs = {"platform": os_value}
        if channel != "release":
            kwargs["channel"] = channel
        return reverse("firefox.notes", kwargs=kwargs)
    channel = _RELEASE_TO_NOTES_CHANNEL.get(release)
    return reverse("firefox.notes", kwargs={"channel": channel} if channel else None)


def get_system_requirements_url(os_value, release):
    """System requirements URL for this OS + release."""
    if os_value in MOBILE_OS:
        return MOBILE_SYSREQ_URL
    channel = _RELEASE_TO_NOTES_CHANNEL.get(release)
    return reverse("firefox.sysreq", kwargs={"channel": channel} if channel else None)


def get_platform_family(os_value):
    """Coarse platform grouping, for copy that applies to a whole family."""
    if os_value in MOBILE_OS:
        return os_value
    if os_value.startswith("win"):
        return "windows"
    if os_value.startswith("osx"):
        return "macos"
    return "linux"


# ---------------------------------------------------------------------------
# Download options
#
# One ordered list of options per selection, built here so the labels, icons,
# ordering and grouping live in one place. The result page renders it; the form
# page never does, because that is where the selection can still change.
# ---------------------------------------------------------------------------


def _option(key, label, href, icon, classes, recommendation=""):
    return {
        "key": key,
        "group": _OPTION_GROUPS[key],
        "label": label,
        "href": href,
        "icon": icon,
        # Applied on top of `fl-button`.
        "classes": classes,
        # An optional line of copy under the button.
        "recommendation": recommendation,
    }


def get_primary_action(family, release):
    """
    The main download button's label and icon, which never depend on the chosen
    language — only the href does. Keyed on the platform family rather than the
    OS so the JS can be handed one small table instead of a 12-row one.
    """
    if family == "ios":
        if release == "beta":
            # iOS betas go through TestFlight, so this leads to an explainer
            # rather than straight to a download.
            return {"label": "Sign up for TestFlight", "icon": "forward"}
        return {"label": "Download from the App Store", "icon": "downloads"}
    if family == "android":
        return {"label": "Download from the Play Store", "icon": "downloads"}
    version = get_version("win64", release)
    label = f"Download {RELEASE_LABELS[release]} {version}" if version else f"Download {RELEASE_LABELS[release]}"
    return {"label": label, "icon": "downloads"}


def get_esr_next_label():
    version = get_esr_next_version()
    return f"Download {RELEASE_LABELS['esr']} {version}" if version else f"Download {RELEASE_LABELS['esr']} Next"


def get_download_option_list(os_value, release, language):
    """
    Every download option for a selection, in render order.

    Returns an empty list when the pair has no builds; the caller shows the
    conflict message instead. Order is fixed here rather than emerging from the
    order the options happen to be created in.
    """
    if not os_value or not is_supported(os_value, release):
        return []

    options = []

    apt_url = get_apt_url(os_value)
    if apt_url:
        options.append(_option(OPTION_APT, "Set up the APT repository", apt_url, "external-link", ["button-secondary"]))

    esr_next_url = get_esr_next_download_url(os_value, release, language)
    if esr_next_url:
        options.append(_option(OPTION_ESR_NEXT, get_esr_next_label(), esr_next_url, "downloads", ["button-primary"]))

    family = get_platform_family(os_value)
    primary = get_primary_action(family, release)
    primary_href = get_store_url(os_value, release) if os_value in MOBILE_OS else get_download_url(os_value, release, language)
    options.append(_option(OPTION_PRIMARY, primary["label"], primary_href, primary["icon"], ["button-primary"]))

    esr_115_url = get_esr_115_download_url(os_value, release, language)
    if esr_115_url:
        options.append(
            _option(
                OPTION_ESR_115,
                f"Download {RELEASE_LABELS['esr']} 115",
                esr_115_url,
                "downloads",
                ["button-primary", "fl-button-small"],
                recommendation=ESR_115_RECOMMENDATIONS.get(family, ""),
            )
        )

    apk_url = get_apk_url(os_value, release)
    if apk_url:
        options.append(_option(OPTION_APK, "Download the APK directly", apk_url, "downloads", ["button-secondary", "fl-button-small"]))

    if get_store_kind(os_value, release) == "microsoft-store":
        options.append(
            _option(
                OPTION_MICROSOFT_STORE,
                "Download from the Microsoft Store",
                get_store_url(os_value, release),
                "external-link",
                ["button-secondary", "fl-button-small"],
            )
        )

    return options


def get_logo(release):
    """The one logo the result page shows."""
    key = RELEASE_LOGOS[release]
    return next(logo for logo in LOGOS if logo["key"] == key)


def get_support_links(os_value, release):
    """
    The row of links under the download options, for the result page.

    The form page does not render these: like the options themselves they only
    describe one selection, and there is nothing to correct them if a visitor
    with no JS then changes a select. The JS builds its own from the label and URL
    tables in get_client_data().
    """
    return [
        {"key": "release-notes", "label": SUPPORT_LINK_LABELS["release-notes"], "href": get_release_notes_url(os_value, release)},
        {
            "key": "system-requirements",
            "label": SUPPORT_LINK_LABELS["system-requirements"],
            "href": get_system_requirements_url(os_value, release),
        },
        {"key": "privacy", "label": SUPPORT_LINK_LABELS["privacy"], "href": PRIVACY_URL},
    ]


# ---------------------------------------------------------------------------
# Client data
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Selection:
    """
    A normalized os/release/language triple from a query string.

    Unrecognized values become None (or, for `language`, the default) rather than
    errors: the form page treats a query string as a prefill, so a stale or
    hand-edited link should quietly fall back instead of scolding the visitor.
    The one thing worth an error message is an OS and release that cannot go
    together, which is the only combination the form itself can produce.
    """

    os: str | None = None
    release: str | None = None
    language: str = "en-US"

    @property
    def effective_release(self):
        """
        The release the form is really offering.

        The release select has no empty option, so with nothing submitted the
        browser shows the first one. Falling back to it here means a link like
        ?os=linux reports the same conflict the JS would.
        """
        return self.release or DEFAULT_RELEASE

    @property
    def effective_language(self):
        """The language the download will use — mobile builds are multi-locale."""
        return "" if self.os in MOBILE_OS else self.language

    @property
    def is_complete(self):
        return self.os is not None and self.release is not None

    @property
    def has_conflict(self):
        return self.os is not None and not is_supported(self.os, self.effective_release)

    @property
    def is_valid(self):
        """Whether this is a submission we can show results for."""
        return self.is_complete and not self.has_conflict


def default_language(locale):
    """The language to preselect: the request's locale when we offer it, else en-US."""
    return locale if is_offered_language(locale) else "en-US"


def parse_selection(data, language=None):
    """Normalize a QueryDict (or plain dict) of form values into a Selection."""
    language = language or "en-US"
    os_value = data.get("os") or ""
    release = data.get("release") or ""
    submitted_language = data.get("language") or ""
    return Selection(
        os=os_value if os_value in get_os_values() else None,
        release=release if release in RELEASE_LABELS else None,
        language=submitted_language if is_offered_language(submitted_language) else language,
    )


# ---------------------------------------------------------------------------
# Template context
# ---------------------------------------------------------------------------


def form_url(data=None):
    """The form page URL, preserving a query string so choices survive a bounce."""
    url = reverse("firefox.all_form")
    query = data.urlencode() if hasattr(data, "urlencode") else urlencode(data or {})
    return f"{url}?{query}" if query else url


def get_form_context(selection):
    """
    Context for the form page.

    Note what is deliberately *not* here: no download options, no support links,
    no conflict verdict. All three describe one particular selection, and the form
    page is the one place the selection can still change — so without JS to keep
    them current they would sit there describing choices the visitor has since
    moved away from, with nothing able to correct them. The submit button is the
    only honest answer at that point, and the result page is where a selection
    gets turned into downloads.

    A prefill is still a prefill: the selects come back with the right values
    (`selected_*`), and a pair with no builds still gets its inline error, which
    is about the submission rather than about the current state of the controls.
    """
    release_error = RELEASE_UNAVAILABLE_ERROR if selection.has_conflict else None

    return {
        "os_groups": get_os_groups(),
        "release_choices": get_release_choices(),
        "language_choices": get_language_choices(),
        "selected_os": selection.os or "",
        "selected_release": selection.effective_release,
        "selected_language": selection.language,
        "release_error": release_error,
        "has_errors": bool(release_error),
        "result_url": reverse("firefox.all_form.result"),
        "unsupported_platforms_json": get_unsupported_platforms_json(),
        "logos": LOGOS,
    }


def get_download_options(selection):
    """
    Context for the result page: every download option for a valid selection.

    This page has no controls, so a selection-derived list is exactly right here —
    it describes the submission that produced the URL, and it cannot go stale
    without a new request.
    """
    os_value = selection.os
    release = selection.release
    language = selection.effective_language

    return {
        "is_mobile": os_value in MOBILE_OS,
        "os_label": OS_LABELS[os_value],
        "release_label": RELEASE_LABELS[release],
        "language_label": get_language_label(language) if language else "",
        "download_options": get_download_option_list(os_value, release, language),
        "support_links": get_support_links(os_value, release),
        "copy": MESSAGES,
        "logo": get_logo(release),
        "form_url": form_url({"os": os_value, "release": release, "language": selection.language}),
    }
