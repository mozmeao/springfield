# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import hashlib
import hmac
import re
from collections import OrderedDict
from urllib.parse import urlparse

from django.conf import settings
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect, JsonResponse
from django.utils.cache import patch_response_headers
from django.utils.encoding import force_str
from django.views.decorators.http import require_safe
from django.views.decorators.vary import vary_on_headers

import querystringsafe_base64
from product_details import product_details

from lib import l10n_utils
from lib.l10n_utils import L10nTemplateView
from lib.l10n_utils.fluent import ftl, ftl_file_is_active
from springfield.base import waffle
from springfield.base.urlresolvers import reverse
from springfield.firefox.firefox_details import (
    firefox_android,
    firefox_desktop,
    firefox_ios,
)
from springfield.newsletter.forms import NewsletterFooterForm
from springfield.releasenotes import version_re

UA_REGEXP = re.compile(r"Firefox/(%s)" % version_re)

INSTALLER_CHANNElS = [
    "release",
    "beta",
    "alpha",
    "nightly",
    "aurora",  # deprecated name for dev edition
]
SEND_TO_DEVICE_MESSAGE_SETS = settings.SEND_TO_DEVICE_MESSAGE_SETS

STUB_VALUE_NAMES = [
    # name, default value
    ("utm_source", "(not set)"),
    ("utm_medium", "(direct)"),
    ("utm_campaign", "(not set)"),
    ("utm_content", "(not set)"),
    ("experiment", "(not set)"),
    ("variation", "(not set)"),
    ("ua", "(not set)"),
    ("client_id_ga4", "(not set)"),
    ("session_id", "(not set)"),
    ("dlsource", "fxdotcom"),
]
STUB_VALUE_RE = re.compile(r"^[a-z0-9-.%():_]+$", flags=re.IGNORECASE)


class InstallerHelpView(L10nTemplateView):
    template_name = "firefox/installer-help.html"
    ftl_files = ["firefox/installer-help"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        installer_lang = self.request.GET.get("installer_lang", None)
        installer_channel = self.request.GET.get("channel", None)
        ctx["installer_lang"] = None
        ctx["installer_channel"] = None

        if installer_lang and installer_lang in firefox_desktop.languages:
            ctx["installer_lang"] = installer_lang

        if installer_channel and installer_channel in INSTALLER_CHANNElS:
            if installer_channel == "aurora":
                ctx["installer_channel"] = "alpha"
            else:
                ctx["installer_channel"] = installer_channel

        return ctx


@require_safe
def stub_attribution_code(request):
    """Return a JSON response containing the HMAC signed stub attribution value"""
    if not request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Resource only available via XHR"}, status=400)

    response = None
    if not settings.STUB_ATTRIBUTION_RATE:
        # return as though it was rate limited, since it was
        response = JsonResponse({"error": "rate limited"}, status=429)
    elif not settings.STUB_ATTRIBUTION_HMAC_KEY:
        response = JsonResponse({"error": "service not configured"}, status=403)

    if response:
        patch_response_headers(response, 300)  # 5 min
        return response

    data = request.GET
    codes = OrderedDict()
    has_value = False
    for name, default_value in STUB_VALUE_NAMES:
        val = data.get(name, "")
        # remove utm_
        if name.startswith("utm_"):
            name = name[4:]

        if val and STUB_VALUE_RE.match(val):
            codes[name] = val
            has_value = True
        else:
            codes[name] = default_value

    if codes["source"] == "(not set)" and "referrer" in data:
        try:
            domain = urlparse(data["referrer"]).netloc
            if domain and STUB_VALUE_RE.match(domain):
                codes["source"] = domain
                codes["medium"] = "referral"
                has_value = True
        except Exception:
            # any problems and we should just ignore it
            pass

    if not has_value:
        codes["source"] = "www.firefox.com"
        codes["medium"] = "(none)"

    code_data = sign_attribution_codes(codes)
    if code_data:
        response = JsonResponse(code_data)
    else:
        response = JsonResponse({"error": "Invalid code"}, status=400)

    patch_response_headers(response, 300)  # 5 min
    return response


def get_attrribution_code(codes):
    """
    Take the attribution codes and return the URL encoded string
    respecting max length.
    """
    code = "&".join("=".join(attr) for attr in codes.items())
    if len(codes["campaign"]) > 5 and len(code) > settings.STUB_ATTRIBUTION_MAX_LEN:
        # remove 5 char at a time
        codes["campaign"] = codes["campaign"][:-5] + "_"
        code = get_attrribution_code(codes)

    return code


def sign_attribution_codes(codes):
    """
    Take the attribution codes and return the base64 encoded string
    respecting max length and HMAC signature.
    """
    key = settings.STUB_ATTRIBUTION_HMAC_KEY
    code = get_attrribution_code(codes)
    if len(code) > settings.STUB_ATTRIBUTION_MAX_LEN:
        return None

    code = querystringsafe_base64.encode(code.encode())
    sig = hmac.new(key.encode(), code, hashlib.sha256).hexdigest()
    return {"attribution_code": code.decode(), "attribution_sig": sig}


@require_safe
def firefox_ai_waitlist_page(request):
    template_name = "firefox/ai/waitlist.html"
    newsletter_id = "smart-window-waitlist"
    ctx = {"newsletter_id": newsletter_id}

    return l10n_utils.render(request, template_name, ctx)


@require_safe
def firefox_all(request, product_slug=None, platform=None, locale=None):
    ftl_files = "firefox/all"

    # A product object for android OR ios.
    class MobileRelease:
        slug = "mobile-release"

    mobile_release = MobileRelease()

    product_map = {
        "desktop-release": {
            "slug": "desktop-release",
            "product": firefox_desktop,
            "channel": "release",
            "name": ftl("firefox-all-product-firefox", ftl_files=ftl_files),
        },
        "desktop-beta": {
            "slug": "desktop-beta",
            "product": firefox_desktop,
            "channel": "beta",
            "name": ftl("firefox-all-product-firefox-beta", ftl_files=ftl_files),
        },
        "desktop-developer": {
            "slug": "desktop-developer",
            "product": firefox_desktop,
            "channel": "devedition",
            "name": ftl("firefox-all-product-firefox-developer", ftl_files=ftl_files),
        },
        "desktop-nightly": {
            "slug": "desktop-nightly",
            "product": firefox_desktop,
            "channel": "nightly",
            "name": ftl("firefox-all-product-firefox-nightly", ftl_files=ftl_files),
        },
        "desktop-esr": {
            "slug": "desktop-esr",
            "product": firefox_desktop,
            "channel": "esr",
            "name": ftl("firefox-all-product-firefox-esr", ftl_files=ftl_files),
        },
        "android-release": {
            "slug": "android-release",
            "product": firefox_android,
            "channel": "release",
            "name": ftl("firefox-all-product-firefox-android", ftl_files=ftl_files),
        },
        "android-beta": {
            "slug": "android-beta",
            "product": firefox_android,
            "channel": "beta",
            "name": ftl("firefox-all-product-firefox-android-beta", ftl_files=ftl_files),
        },
        "android-nightly": {
            "slug": "android-nightly",
            "product": firefox_android,
            "channel": "nightly",
            "name": ftl("firefox-all-product-firefox-android-nightly", ftl_files=ftl_files),
        },
        "ios-release": {
            "slug": "ios-release",
            "product": firefox_ios,
            "channel": "release",
            "name": ftl("firefox-all-product-firefox-ios", ftl_files=ftl_files),
        },
        "ios-beta": {
            "slug": "ios-beta",
            "product": firefox_ios,
            "channel": "beta",
            "name": ftl("firefox-all-product-firefox-ios", ftl_files=ftl_files),
        },
        # mobile-release is a special case for both android and ios.
        "mobile-release": {
            "slug": "mobile-release",
            "product": mobile_release,
            "channel": "release",
            "name": ftl("firefox-all-product-firefox", ftl_files=ftl_files),
        },
    }

    platform_map = {
        "win64": "Windows 64-bit",
        "win64-msi": "Windows 64-bit MSI",
        "win64-aarch64": "Windows ARM64/AArch64",
        "win": "Windows 32-bit",
        "win-msi": "Windows 32-bit MSI",
        "win-store": "Microsoft Store",
        "osx": "macOS",
        "linux64": "Linux 64-bit",
        "linux": "Linux 32-bit",
        "linux64-aarch64": "Linux ARM64/AArch64",
    }

    # 404 checks.
    if product_slug and product_slug not in product_map.keys():
        raise Http404()
    if platform and platform not in platform_map.keys():
        raise Http404()
    if locale and locale not in product_details.languages.keys():
        raise Http404()
    # 404 if win-store and not desktop-release.
    if platform == "win-store" and product_slug not in ["desktop-release", "desktop-beta"]:
        raise Http404()

    product = product_map.get(product_slug)
    platform_name = None
    locale_name = None
    download_url = None

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if waffle.switch("FLARE26_ENABLED"):
            template_name = "firefox/all/includes/main-flare26.html"
        else:
            template_name = "firefox/all/includes/main.html"
    elif waffle.switch("FLARE26_ENABLED"):
        template_name = "firefox/all/base-flare26.html"
    else:
        template_name = "firefox/all/base.html"

    lang_multi = ftl("firefox-all-lang-multi", ftl_files=ftl_files)

    if product:
        if product_slug.startswith(("mobile", "android", "ios")):
            locale = "en-US"
            locale_name = lang_multi
            download_url = True  # Set to True to avoid trying to generate this later below.
        if product_slug.startswith("mobile"):
            platform = "mobile"
            platform_name = ftl("firefox-all-plat-mobile", ftl_files=ftl_files)
        elif product_slug.startswith("android"):
            platform = "android"
            platform_name = "Android"
        elif product_slug.startswith("ios"):
            platform = "ios"
            platform_name = "iOS"
        elif product_slug in ("desktop-release", "desktop-beta") and platform == "win-store":
            platform_name = "Microsoft Store"
            locale = "en-US"
            locale_name = lang_multi
            download_url = {
                "desktop-release": settings.MICROSOFT_WINDOWS_STORE_FIREFOX_WEB_LINK,
                "desktop-beta": settings.MICROSOFT_WINDOWS_STORE_FIREFOX_BETA_WEB_LINK,
            }.get(product_slug)
        else:
            platform_name = platform and platform_map[platform]
            locale_name = None
            if locale:
                try:
                    build = list(filter(lambda b: b["locale"] == locale, product["product"].get_filtered_full_builds(product["channel"])))[0]
                except IndexError:
                    raise Http404()
                locale_name = f"{build['name_en']} - {build['name_native']}"

    context = {
        "product": product,
        "platform": platform,
        "platform_name": platform_name,
        "locale": locale,
        "locale_name": locale_name,
    }

    # `firefox_desktop.esr_minor_versions` could have 0, 1, or 2 elements. This adds defaults so we always have 2 to unpack.
    esr_latest_version, esr_next_version = (firefox_desktop.esr_minor_versions + [None, None])[:2]
    if esr_next_version:
        context.update(
            desktop_esr_latest_version=esr_latest_version,
            desktop_esr_next_version=esr_next_version,
        )

    # Show download link
    if locale:
        if not download_url:
            download_url = list(filter(lambda b: b["locale"] == locale, product["product"].get_filtered_full_builds(product["channel"])))[0][
                "platforms"
            ][platform]["download_url"]
        context.update(
            download_url=download_url,
        )
        try:
            if product_slug == "desktop-esr":
                download_esr_115_url = list(filter(lambda b: b["locale"] == locale, firefox_desktop.get_filtered_full_builds("esr115")))[0][
                    "platforms"
                ][platform]["download_url"]
                # ESR115 builds do not exist for "sat" and "skr" languages (issue: mozilla/bedrock#15437)
                if locale in ["sat", "skr"]:
                    download_esr_115_url = None
                # ESR115 builds do not exist for "linux64-aarch64" platform (see issue #467)
                if platform == "linux64-aarch64":
                    download_esr_115_url = None
                context.update(
                    download_esr_115_url=download_esr_115_url,
                )
        except IndexError:
            pass
        if product_slug == "desktop-esr" and esr_next_version:
            try:
                download_esr_next_url = list(filter(lambda b: b["locale"] == locale, firefox_desktop.get_filtered_full_builds("esr_next")))[0][
                    "platforms"
                ][platform]["download_url"]
                context.update(
                    download_esr_next_url=download_esr_next_url,
                )
            except IndexError:
                # If the ESR next version is not available for the locale, remove the context variables.
                context.pop("desktop_esr_latest_version", None)
                context.pop("desktop_esr_next_version", None)

    # Show platforms with download links
    elif platform:
        locales = []
        for b in product["product"].get_filtered_full_builds(product["channel"]):
            locale_name = f"{b['name_en']} - {b['name_native']}"
            if b["locale"] == request.locale:
                # If locale matches request's locale, put it at the top.
                locales.insert(0, (b["locale"], locale_name))
            else:
                locales.append((b["locale"], locale_name))

        context.update(
            locales=locales,
        )

    # Show locales.
    elif product_slug:
        platforms = product["product"].platforms(product["channel"])
        if product_slug in ["desktop-release", "desktop-beta"]:
            idx = platforms.index(("osx", "macOS"))
            platforms.insert(idx, ("win-store", "Microsoft Store"))
        context.update(platforms=platforms)

    # Show products.
    else:
        context.update(
            products=[{"slug": k, "name": v["name"]} for k, v in product_map.items()],
        )

    return l10n_utils.render(request, template_name, context, ftl_files=ftl_files)


class DownloadThanksView(L10nTemplateView):
    ftl_files_map = {
        "firefox/download/basic/thanks.html": ["firefox/download/download"],
        "firefox/download/basic/thanks_direct.html": ["firefox/download/download"],
        "firefox/download/desktop/thanks.html": ["firefox/download/desktop"],
        "firefox/download/desktop/thanks_direct.html": ["firefox/download/desktop"],
    }
    activation_files = [
        "firefox/download/download",
        "firefox/download/desktop",
    ]

    # place expected ?v= values in this list
    variations = []

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        variation = self.request.GET.get("variation", None)

        # ensure variant matches pre-defined value
        if variation not in self.variations:
            variation = None

        ctx["variation"] = variation

        return ctx

    def get_template_names(self):
        experience = self.request.GET.get("xv", None)
        source = self.request.GET.get("s", None)

        if ftl_file_is_active("firefox/download/desktop") and experience != "basic":
            if source == "direct":
                template = "firefox/download/desktop/thanks_direct.html"
            else:
                template = "firefox/download/desktop/thanks.html"
        else:
            if source == "direct":
                template = "firefox/download/basic/thanks_direct.html"
            else:
                template = "firefox/download/basic/thanks.html"

        return [template]


# Platform detection patterns for /download/ redirect.
# Order matters: Android and ChromeOS UAs contain "Linux",
# and iOS UAs can contain "Mac OS X", so check mobile/specific
# platforms before generic desktop ones.
_DOWNLOAD_PLATFORM_PATTERNS = (
    (re.compile(r"\b(iPhone|iPad|iPod)\b", re.I), "ios"),
    (re.compile(r"\bAndroid\b", re.I), "android"),
    (re.compile(r"\bCrOS\b", re.I), "chromebook"),
    (re.compile(r"\bWindows\b", re.I), "windows"),
    (re.compile(r"\bMacintosh\b", re.I), "mac"),
    (re.compile(r"\bLinux\b", re.I), "linux"),
)


def detect_download_platform(user_agent):
    """Detect the download platform from a User-Agent string.

    Returns one of 'windows', 'mac', 'linux', 'android', 'ios',
    'chromebook', or None if the platform cannot be determined.
    """
    for pattern, platform in _DOWNLOAD_PLATFORM_PATTERNS:
        if pattern.search(user_agent):
            return platform
    return None


@vary_on_headers("User-Agent")
def download_redirect(request):
    """Redirect /download/ to the appropriate platform-specific download page.

    When the PLATFORM_DOWNLOAD_REDIRECTION switch is off, falls back to
    redirecting to the homepage (matching the legacy redirects.py behaviour).
    """
    if not waffle.switch("PLATFORM_DOWNLOAD_REDIRECTION"):
        return HttpResponseRedirect(reverse("firefox"))

    ua = request.headers.get("User-Agent", "")
    platform = detect_download_platform(ua)

    base = request.path
    if not base.endswith("/"):
        base += "/"

    if platform:
        redirect_url = f"{base}{platform}/"
    else:
        redirect_url = f"{base}all/"

    qs = request.META.get("QUERY_STRING", "")
    if qs:
        redirect_url = f"{redirect_url}?{qs}"

    return HttpResponseRedirect(redirect_url)


class DownloadView(L10nTemplateView):
    ftl_files_map = {
        "firefox/download/basic/base_download.html": ["firefox/download/download"],
        "firefox/download/desktop/download.html": ["firefox/download/desktop"],
        "firefox/download/home.html": ["firefox/download/desktop", "firefox/download/home"],
    }
    activation_files = [
        "firefox/download/download",
        "firefox/download/desktop",
    ]

    # place expected ?v= values in this list
    variations = []

    def get(self, *args, **kwargs):
        # Remove legacy query parameters (Bug 1236791)
        if self.request.GET.get("product", None) or self.request.GET.get("os", None):
            return HttpResponsePermanentRedirect(reverse("firefox"))

        scene = self.request.GET.get("scene", None)
        if scene == "2":
            # send to new permanent scene2 URL (bug 1438302)
            thanks_url = reverse("firefox.download.thanks")
            query_string = self.request.META.get("QUERY_STRING", "")
            if query_string:
                thanks_url = "?".join([thanks_url, force_str(query_string, errors="ignore")])
            return HttpResponsePermanentRedirect(thanks_url)

        return super().get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # note: variation and xv params only allow a-z, A-Z, 0-9, -, and _ characters
        variation = self.request.GET.get("variation", None)

        # ensure variant matches pre-defined value
        if variation not in self.variations:
            variation = None

        ctx["variation"] = variation

        reason = self.request.GET.get("reason", None)
        manual_update = True if reason == "manual-update" else False
        outdated = reason == "outdated"
        ctx["manual_update"] = manual_update
        ctx["outdated"] = outdated

        return ctx

    def get_template_names(self):
        variation = self.request.GET.get("variation", None)
        experience = self.request.GET.get("xv", None)

        # ensure variant matches pre-defined value
        if variation not in self.variations:
            variation = None

        if ftl_file_is_active("firefox/download/home") and experience not in ["basic", "legacy"]:
            template = "firefox/download/home.html"
        elif ftl_file_is_active("firefox/download/desktop") and experience != "basic":
            template = "firefox/download/desktop/download.html"
        else:
            template = "firefox/download/basic/base_download.html"

        return [template]


@require_safe
def ios_testflight(request):
    action = settings.BASKET_SUBSCRIBE_URL

    # no country field, so no need to send locale
    newsletter_form = NewsletterFooterForm("ios-beta-test-flight", "")
    ctx = {"action": action, "newsletter_form": newsletter_form}

    return l10n_utils.render(request, "firefox/testflight.html", ctx)


class FirefoxFeaturesIndex(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/index.html": [
            "firefox/features/index-2023",
            "firefox/features/shared",
        ],
    }

    def get_template_names(self):
        template_name = "firefox/features/index.html"
        return [template_name]


class FirefoxFeaturesCustomize(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/customize.html": ["firefox/features/customize-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/customize.html"
        return [template_name]


class FirefoxFeaturesAddons(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/add-ons.html": ["firefox/features/add-ons-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/add-ons.html"
        return [template_name]


class FirefoxFeaturesPinnedTabs(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/pinned-tabs.html": ["firefox/features/pinned-tabs-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/pinned-tabs.html"
        return [template_name]


class FirefoxFeaturesEyeDropper(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/eyedropper.html": ["firefox/features/eyedropper-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/eyedropper.html"
        return [template_name]


class FirefoxFeaturesBookmarks(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/bookmarks.html": ["firefox/features/bookmarks-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/bookmarks.html"
        return [template_name]


class FirefoxFeaturesBlockFingerprinting(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/fingerprinting.html": ["firefox/features/fingerprinting", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/fingerprinting.html"
        return [template_name]


class FirefoxFeaturesPasswordManager(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/password-manager.html": ["firefox/features/password-manager-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/password-manager.html"
        return [template_name]


class FirefoxFeaturesPrivate(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/private.html": ["firefox/features/private-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/private.html"
        return [template_name]


class FirefoxFeaturesPrivateBrowsing(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/private-browsing.html": ["firefox/features/private-browsing-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/private-browsing.html"
        return [template_name]


class FirefoxFeaturesSync(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/sync.html": ["firefox/features/sync-2023", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/sync.html"
        return [template_name]


class FirefoxFeaturesPictureInPicture(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/picture-in-picture.html": ["firefox/features/picture-in-picture", "firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/picture-in-picture.html"
        return [template_name]


class FirefoxFeaturesCompletePDF(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/pdf-complete-fr.html": ["firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/pdf-complete-fr.html"
        return [template_name]


class FirefoxFeaturesFreePDFEditor(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/pdf-free-fr.html": ["firefox/features/shared"],
    }

    def get_template_names(self):
        template_name = "firefox/features/pdf-free-fr.html"
        return [template_name]


@require_safe
def firefox_features_translate(request):
    translate_langs = [
        "ar",
        "az",
        "bg",
        "bn",
        "ca",
        "zh-CN",
        "hr",
        "cs",
        "da",
        "nl",
        "en-US",
        "et",
        "fa",
        "fi",
        "fr",
        "de",
        "el",
        "gu",
        "he",
        "hi",
        "hu",
        "id",
        "is",
        "it",
        "ja",
        "kn",
        "ko",
        "lv",
        "lt",
        "ml",
        "ms",
        "pl",
        "pt-PT",
        "ro",
        "ru",
        "sr",
        "sk",
        "sl",
        "sq",
        "es-ES",
        "sv-SE",
        "ta",
        "te",
        "tr",
        "uk",
        "vi",
    ]

    context = {"translate_langs": sorted(translate_langs), "lang_names": product_details.languages}

    template_name = "firefox/features/translate.html"

    return l10n_utils.render(
        request,
        template_name,
        context,
        ftl_files=["firefox/features/translate", "firefox/features/shared"],
    )


class FirefoxFeaturesFast(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/fast.html": [
            "firefox/features/fast-2023",
            "firefox/features/shared",
        ],
        "firefox/features/fast-2024.html": [
            "firefox/features/fast-2024",
            "firefox/features/shared",
        ],
    }

    def get_template_names(self):
        if ftl_file_is_active("firefox/features/fast-2024"):
            template_name = "firefox/features/fast-2024.html"
        else:
            template_name = "firefox/features/fast.html"

        return [template_name]


class FirefoxFeaturesPDF(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/pdf-editor.html": ["firefox/features/pdf-editor-2023", "firefox/features/shared"],
        "firefox/features/pdf-editor-fr.html": ["firefox/features/shared"],
    }

    def get_template_names(self):
        locale = l10n_utils.get_locale(self.request)
        if locale == "fr":
            template_name = "firefox/features/pdf-editor-fr.html"
        else:
            template_name = "firefox/features/pdf-editor.html"

        return [template_name]


class FirefoxFeaturesAdBlocker(L10nTemplateView):
    ftl_files_map = {
        "firefox/features/adblocker-2025.html": [
            "firefox/features/adblocker-2025",
            "firefox/features/shared",
        ],
        "firefox/features/adblocker.html": [
            "firefox/features/adblocker",
            "firefox/features/shared",
        ],
    }

    def get_template_names(self):
        if ftl_file_is_active("firefox/features/adblocker-2025"):
            template_name = "firefox/features/adblocker-2025.html"
        else:
            template_name = "firefox/features/adblocker.html"

        return [template_name]


class PlatformViewLinux(L10nTemplateView):
    # the base_platform template works with either platform.ftl or download.ftl active
    template_name = "firefox/browsers/desktop/linux.html"

    ftl_files_map = {
        "firefox/browsers/desktop/linux.html": [
            "firefox/download/platform",
            "firefox/download/download",
        ],
    }

    # all active locales, this will make the lang switcher work properly
    activation_files = ["firefox/download/download", "firefox/download/platform"]


class PlatformViewMac(L10nTemplateView):
    # the base_platform template works with either platform.ftl or download.ftl active
    template_name = "firefox/browsers/desktop/mac.html"

    ftl_files_map = {
        "firefox/browsers/desktop/mac.html": [
            "firefox/download/platform",
            "firefox/download/download",
        ],
    }

    # all active locales, this will make the lang switcher work properly
    activation_files = ["firefox/download/download", "firefox/download/platform"]


class PlatformViewWindows(L10nTemplateView):
    # the base_platform template works with either platform.ftl or download.ftl active
    template_name = "firefox/browsers/desktop/windows.html"

    ftl_files_map = {
        "firefox/browsers/desktop/windows.html": [
            "firefox/download/platform",
            "firefox/download/download",
        ],
    }

    # all active locales, this will make the lang switcher work properly
    activation_files = ["firefox/download/download", "firefox/download/platform"]


def detect_channel(version):
    match = re.match(r"\d{1,3}", version)
    if match:
        num_version = int(match.group(0))
        if num_version >= 35:
            if version.endswith("a1"):
                return "nightly"
            if version.endswith("a2"):
                return "developer"

    return "unknown"


class WhatsnewView(L10nTemplateView):
    ftl_files_map = {
        "firefox/whatsnew/nightly/evergreen.html": ["firefox/whatsnew/nightly/evergreen"],
        "firefox/whatsnew/developer/evergreen.html": ["firefox/whatsnew/developer/evergreen"],
        "firefox/whatsnew/evergreen.html": ["firefox/whatsnew/evergreen"],
    }

    # place expected ?v= values in this list
    variations = ["1", "2", "3", "4"]

    # Nimbus experiment variation expected values
    nimbus_variations = ["v1", "v2", "v3", "v4"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        version = self.kwargs.get("version") or ""
        pre_release_channels = ["nightly", "developer"]
        channel = detect_channel(version)

        # add version to context for use in templates
        match = re.match(r"\d{1,3}", version)
        num_version = int(match.group(0)) if match else ""
        ctx["version"] = version
        ctx["num_version"] = num_version

        # add analytics parameters to context for use in templates
        if channel not in pre_release_channels:
            channel = ""

        analytics_version = str(num_version) + channel
        entrypoint = "firefox.com-whatsnew" + analytics_version
        campaign = "whatsnew" + analytics_version
        ctx["analytics_version"] = analytics_version
        ctx["entrypoint"] = entrypoint
        ctx["campaign"] = campaign
        ctx["utm_params"] = f"utm_source={entrypoint}&utm_medium=referral&utm_campaign={campaign}&entrypoint={entrypoint}"

        variant = self.request.GET.get("v", None)
        nimbus_variant = self.request.GET.get("variant", None)

        # ensure variant matches pre-defined value
        if variant not in self.variations:
            variant = None

        # ensure nimbus_variant matches pre-defined value
        if nimbus_variant not in self.nimbus_variations:
            nimbus_variant = None

        ctx["variant"] = variant
        ctx["nimbus_variant"] = nimbus_variant

        return ctx

    def get_template_names(self):
        version = self.kwargs.get("version") or ""

        oldversion = self.request.GET.get("oldversion", "")
        # old versions of Firefox sent a prefixed version
        if oldversion.startswith("rv:"):
            oldversion = oldversion[3:]

        channel = detect_channel(version)

        if channel == "nightly":
            template = "firefox/whatsnew/nightly/evergreen.html"
        elif channel == "developer":
            template = "firefox/whatsnew/developer/evergreen.html"
        else:
            template = "firefox/whatsnew/evergreen.html"

        # return a list to conform with original intention
        return [template]
