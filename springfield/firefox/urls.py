# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.urls import path, re_path

import springfield.releasenotes.views
from lib.l10n_utils import L10nTemplateView
from springfield.base.util import page
from springfield.cms.decorators import prefer_cms
from springfield.firefox import views
from springfield.releasenotes import version_re
from springfield.utils.views import VariationTemplateView

latest_re = r"^firefox(?:/(?P<version>%s))?/%s/$"
platform_re = "(?P<platform>android|ios)"
channel_re = "(?P<channel>beta|aurora|developer|nightly|organizations)"
releasenotes_re = latest_re % (version_re, r"(aurora|release)notes")
android_releasenotes_re = releasenotes_re.replace(r"firefox", "firefox/android")
ios_releasenotes_re = releasenotes_re.replace(r"firefox", "firefox/ios")
sysreq_re = latest_re % (version_re, "system-requirements")
android_sysreq_re = sysreq_re.replace(r"firefox", "firefox/android")
ios_sysreq_re = sysreq_re.replace(r"firefox", "firefox/ios")


urlpatterns = (
    path("", prefer_cms(views.DownloadView.as_view()), name="firefox"),
    path("download/", views.download_redirect, name="firefox.download"),
    path("download/all/", views.firefox_all, name="firefox.all"),
    path("download/all/<slug:product_slug>/", views.firefox_all, name="firefox.all.platforms"),
    path("download/all/<slug:product_slug>/<str:platform>/", views.firefox_all, name="firefox.all.locales"),
    path("download/all/<slug:product_slug>/<str:platform>/<str:locale>/", views.firefox_all, name="firefox.all.download"),
    page("channel/desktop/", "firefox/channel/desktop.html", ftl_files=["firefox/channel"]),
    page("channel/desktop/developer/", "firefox/developer/index.html", ftl_files=["firefox/developer"]),
    page("channel/android/", "firefox/channel/android.html", ftl_files=["firefox/channel"]),
    page("channel/ios/", "firefox/channel/ios.html", ftl_files=["firefox/channel"]),
    path("channel/ios/testflight/", views.ios_testflight, name="firefox.ios.testflight"),
    page("browsers/enterprise/", "firefox/enterprise/index.html", ftl_files=["firefox/enterprise"]),
    path("features/", prefer_cms(views.FirefoxFeaturesIndex.as_view()), name="firefox.features.index"),
    path("features/customize/", prefer_cms(views.FirefoxFeaturesCustomize.as_view()), name="firefox.features.customize"),
    path("features/add-ons/", prefer_cms(views.FirefoxFeaturesAddons.as_view()), name="firefox.features.add-ons"),
    path("features/pinned-tabs/", prefer_cms(views.FirefoxFeaturesPinnedTabs.as_view()), name="firefox.features.pinned-tabs"),
    path("features/eyedropper/", prefer_cms(views.FirefoxFeaturesEyeDropper.as_view()), name="firefox.features.eyedropper"),
    path("features/pdf-editor/", prefer_cms(views.FirefoxFeaturesPDF.as_view()), name="firefox.features.pdf-editor"),
    path("features/adblocker/", prefer_cms(views.FirefoxFeaturesAdBlocker.as_view()), name="firefox.features.adblocker"),
    path("features/bookmarks/", prefer_cms(views.FirefoxFeaturesBookmarks.as_view()), name="firefox.features.bookmarks"),
    path("features/fast/", prefer_cms(views.FirefoxFeaturesFast.as_view()), name="firefox.features.fast"),
    path("features/block-fingerprinting/", prefer_cms(views.FirefoxFeaturesBlockFingerprinting.as_view()), name="firefox.features.fingerprinting"),
    path("features/password-manager/", prefer_cms(views.FirefoxFeaturesPasswordManager.as_view()), name="firefox.features.password-manager"),
    path("features/private/", prefer_cms(views.FirefoxFeaturesPrivate.as_view()), name="firefox.features.private"),
    path("features/private-browsing/", prefer_cms(views.FirefoxFeaturesPrivateBrowsing.as_view()), name="firefox.features.private-browsing"),
    path("features/sync/", prefer_cms(views.FirefoxFeaturesSync.as_view()), name="firefox.features.sync"),
    path("features/translate/", prefer_cms(views.firefox_features_translate), name="firefox.features.translate"),
    path("features/picture-in-picture/", prefer_cms(views.FirefoxFeaturesPictureInPicture.as_view()), name="firefox.features.picture-in-picture"),
    # /features/tips/ is a unicorn in terms of design, so is not currently part of the CMS driven /feature article templates.
    path(
        "features/tips/",
        VariationTemplateView.as_view(
            template_name="firefox/features/tips/tips.html",
            template_context_variations=["picture-in-picture", "eyedropper", "forget"],
        ),
        name="firefox.features.tips",
    ),
    path("features/complete-pdf/", prefer_cms(views.FirefoxFeaturesCompletePDF.as_view(active_locales=["fr"])), name="firefox.features.pdf-complete"),
    path(
        "features/free-pdf-editor/", prefer_cms(views.FirefoxFeaturesFreePDFEditor.as_view(active_locales=["fr"])), name="firefox.features.pdf-free"
    ),
    path("thanks/", prefer_cms(views.DownloadThanksView.as_view()), name="firefox.download.thanks"),
    path("download/installer-help/", views.InstallerHelpView.as_view(), name="firefox.installer-help"),
    # Release notes
    re_path(f"^firefox/(?:{platform_re}/)?(?:{channel_re}/)?notes/$", springfield.releasenotes.views.latest_notes, name="firefox.notes"),
    path("firefox/nightly/notes/feed/", springfield.releasenotes.views.nightly_feed, name="firefox.nightly.notes.feed"),
    re_path("firefox/(?:latest/)?releasenotes/$", springfield.releasenotes.views.latest_notes, {"product": "firefox"}),
    path("firefox/android/releasenotes/", springfield.releasenotes.views.latest_notes, {"product": "Firefox for Android"}),
    path("firefox/ios/releasenotes/", springfield.releasenotes.views.latest_notes, {"product": "Firefox for iOS"}),
    re_path(
        f"^firefox/(?:{platform_re}/)?(?:{channel_re}/)?system-requirements/$",
        springfield.releasenotes.views.latest_sysreq,
        {"product": "firefox"},
        name="firefox.sysreq",
    ),
    re_path(releasenotes_re, springfield.releasenotes.views.release_notes, name="firefox.desktop.releasenotes"),
    re_path(
        android_releasenotes_re, springfield.releasenotes.views.release_notes, {"product": "Firefox for Android"}, name="firefox.android.releasenotes"
    ),
    re_path(ios_releasenotes_re, springfield.releasenotes.views.release_notes, {"product": "Firefox for iOS"}, name="firefox.ios.releasenotes"),
    re_path(sysreq_re, springfield.releasenotes.views.system_requirements, name="firefox.system_requirements"),
    re_path(
        android_sysreq_re,
        springfield.releasenotes.views.system_requirements,
        {"product": "Firefox for Android"},
        name="firefox.android.system_requirements",
    ),
    re_path(
        ios_sysreq_re, springfield.releasenotes.views.system_requirements, {"product": "Firefox for iOS"}, name="firefox.ios.system_requirements"
    ),
    path("releases/", springfield.releasenotes.views.releases_index, {"product": "Firefox"}, name="firefox.releases.index"),
    path("stub_attribution_code/", views.stub_attribution_code, name="firefox.stub_attribution_code"),
    # Issue 8432
    # Issue 13253: Ensure that Firefox can continue to refer to this URL.
    page("landing/set-as-default/thanks/", "firefox/default/thanks.html", ftl_files="firefox/set-as-default/thanks"),
    # Default browser campaign
    page("landing/set-as-default/", "firefox/default/landing.html", ftl_files="firefox/set-as-default/landing"),
    page("analytics-tests/", "firefox/analytics-tests/ga-index.html"),
    page("browsers/desktop/", "firefox/browsers/desktop/index.html", ftl_files=["firefox/browsers"]),
    # Privacy-focused download experiment: https://github.com/mozmeao/springfield/pull/919/
    path("landing/get/", views.landing_get_page, name="landing.get"),
    # Issue 15841, 15920, 5953 - UK influencer campaign pages
    page("landing/tech/", "firefox/landing/tech.html", ftl_files="firefox/download/desktop", active_locales="en-GB"),
    page("landing/education/", "firefox/landing/education.html", ftl_files="firefox/download/desktop", active_locales="en-GB"),
    page("landing/gaming/", "firefox/landing/gaming.html", ftl_files="firefox/download/desktop", active_locales="en-GB"),
    # Issue #444 - US-only iOS landing page
    page(
        "landing/ios-summarizer/",
        "firefox/landing/ios-summarizer.html",
        ftl_files=["firefox/browsers/mobile/ios-summarizer", "firefox/browsers/mobile/ios"],
        active_locales="en-US",
    ),
    # Issue 487 - Win10 End of Service
    page(
        "landing/win-new-features/",
        "firefox/landing/win10-eos.html",
        active_locales=["en-US", "en-GB", "en-CA", "fr", "de"],
    ),
    # Issue 606 - NA + DE Windows Defense/Josef Landing Page
    page(
        "landing/windows/",
        "firefox/landing/windows.html",
        active_locales=["en-US", "de"],
        ftl_files=["firefox/download/desktop", "firefox/download/home"],
    ),
    # Issue 684 - Kit Landing page
    page(
        "kit/",
        "firefox/landing/kit.html",
        active_locales=["en-US", "en-GB", "en-CA", "fr", "de"],
    ),
    path(
        "compare/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/index.html",
                ftl_files=["firefox/browsers/compare/index", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/index", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.index",
    ),
    path(
        "compare/brave/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/brave.html",
                ftl_files=["firefox/browsers/compare/brave", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/brave", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.brave",
    ),
    path(
        "compare/chrome/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/chrome.html",
                ftl_files=["firefox/browsers/compare/chrome", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/chrome", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.chrome",
    ),
    path(
        "compare/edge/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/edge.html",
                ftl_files=["firefox/browsers/compare/edge", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/edge", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.edge",
    ),
    path(
        "compare/opera/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/opera.html",
                ftl_files=["firefox/browsers/compare/opera", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/opera", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.opera",
    ),
    path(
        "compare/safari/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/browsers/compare/safari.html",
                ftl_files=["firefox/browsers/compare/safari", "firefox/browsers/compare/shared"],
            ),
            fallback_ftl_files=["firefox/browsers/compare/safari", "firefox/browsers/compare/shared"],
        ),
        name="firefox.browsers.compare.safari",
    ),
    page(
        "landing/year-in-review-2025/",
        "firefox/landing/year-in-review-2025.html",
        url_name="firefox.year_in_review_2025",
    ),
    # bedrock Issue 8641
    path(
        "more/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/index.html",
                ftl_files=["firefox/more/more", "firefox/more/shared"],
            ),
            fallback_ftl_files=["firefox/more/more", "firefox/more/shared"],
        ),
        name="firefox.more.index",
    ),
    path(
        "more/best-browser/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/best-browser.html",
                ftl_files=["firefox/more/best-browser", "firefox/more/shared"],
            ),
            fallback_ftl_files=["firefox/more/best-browser", "firefox/more/shared"],
        ),
        name="firefox.more.best-browser",
    ),
    path(
        "more/browser-history/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/browser-history.html",
                ftl_files=["firefox/more/browser-history", "firefox/more/shared"],
            ),
            fallback_ftl_files=["firefox/more/browser-history", "firefox/more/shared"],
        ),
        name="firefox.more.browser-history",
    ),
    path(
        "more/incognito-browser/",
        prefer_cms(
            L10nTemplateView.as_view(template_name="firefox/more/incognito-browser.html"),
            fallback_lang_codes=["en-US"],
        ),
        name="firefox.more.incognito-browser",
    ),
    path(
        "more/update-your-browser/",
        prefer_cms(
            L10nTemplateView.as_view(template_name="firefox/more/update-browser.html"),
            fallback_lang_codes=["en-US"],
        ),
        name="firefox.more.update-browser",
    ),
    path(
        "more/what-is-a-browser/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/what-is-a-browser.html",
                ftl_files=["firefox/more/what-is-a-browser", "firefox/more/shared"],
            ),
            fallback_ftl_files=["firefox/more/what-is-a-browser", "firefox/more/shared"],
        ),
        name="firefox.more.what-is-a-browser",
    ),
    path(
        "more/windows-64-bit/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/windows-64-bit.html",
                ftl_files=["firefox/more/windows-64-bit", "firefox/more/shared"],
            ),
            fallback_ftl_files=["firefox/more/windows-64-bit", "firefox/more/shared"],
        ),
        name="firefox.more.windows-64-bit",
    ),
    # Bedrock Issue #9490 - Evergreen Content for SEO
    path(
        "more/faq/",
        prefer_cms(
            L10nTemplateView.as_view(
                template_name="firefox/more/faq.html",
                ftl_files=["firefox/more/faq"],
            ),
            fallback_ftl_files=["firefox/more/faq"],
        ),
        name="firefox.more.faq",
    ),
    # START What's New Page (WNP) paths
    # 1. Legacy version format: MAJ.MIN/variant.patch (127.1a, 139.0.1, etc) rather than just MAJ
    re_path(f"^whatsnew/(?P<version>{version_re})/", views.WhatsnewView.as_view(), name="firefox.whatsnew_legacy"),
    # 2. New version format, which should be served from the CMS, but falls back to evergreen page
    re_path(r"^whatsnew/(?P<version>[1-9]\d{2})/", prefer_cms(views.WhatsnewView.as_view()), name="firefox.whatsnew"),
    # END What's New Page (WNP) paths
)

if settings.ENABLE_CMS_REFRESH_REDIRECTS:
    urlpatterns += (
        path(
            "user-privacy/",
            prefer_cms(L10nTemplateView.as_view(template_name="firefox/data.html")),
            name="firefox.user-privacy",
        ),
        path(
            "download/android/",
            prefer_cms(L10nTemplateView.as_view(template_name="firefox/browsers/mobile/android.html", ftl_files=["firefox/browsers/mobile/android"])),
            name="firefox.browsers.mobile.android",
        ),
        path(
            "download/ios/",
            prefer_cms(L10nTemplateView.as_view(template_name="firefox/browsers/mobile/ios.html", ftl_files=["firefox/browsers/mobile/ios"])),
            name="firefox.browsers.mobile.ios",
        ),
        path(
            "download/chromebook/",
            prefer_cms(
                L10nTemplateView.as_view(template_name="firefox/browsers/desktop/chromebook.html", ftl_files=["firefox/browsers/desktop/chromebook"])
            ),
            name="firefox.browsers.desktop.chromebook",
        ),
        path("download/linux/", prefer_cms(views.PlatformViewLinux.as_view()), name="firefox.browsers.desktop.linux"),
        path("download/mac/", prefer_cms(views.PlatformViewMac.as_view()), name="firefox.browsers.desktop.mac"),
        path("download/windows/", prefer_cms(views.PlatformViewWindows.as_view()), name="firefox.browsers.desktop.windows"),
        path("download/unsupported-systems/", prefer_cms(L10nTemplateView.as_view(template_name="firefox/unsupported-systems.html"))),
        path(
            "mobile/",
            prefer_cms(
                views.MobileBrowsersView.as_view(),
                fallback_ftl_files=["firefox/browsers/mobile/index"],
            ),
            name="firefox.browsers.mobile",
        ),
        path(
            "mobile/focus/",
            prefer_cms(
                L10nTemplateView.as_view(template_name="firefox/browsers/mobile/focus.html", ftl_files=["firefox/browsers/mobile/focus"]),
                fallback_ftl_files=["firefox/browsers/mobile/focus"],
            ),
            name="firefox.browsers.mobile.focus",
        ),
    )
else:
    urlpatterns += (
        page("user-privacy/", "firefox/data.html", url_name="firefox.user-privacy"),
        page("browsers/mobile/android/", "firefox/browsers/mobile/android.html", ftl_files=["firefox/browsers/mobile/android"]),
        page("browsers/mobile/ios/", "firefox/browsers/mobile/ios.html", ftl_files=["firefox/browsers/mobile/ios"]),
        path("browsers/desktop/linux/", views.PlatformViewLinux.as_view(), name="firefox.browsers.desktop.linux"),
        path("browsers/desktop/mac/", views.PlatformViewMac.as_view(), name="firefox.browsers.desktop.mac"),
        path("browsers/desktop/windows/", views.PlatformViewWindows.as_view(), name="firefox.browsers.desktop.windows"),
        page("browsers/desktop/chromebook/", "firefox/browsers/desktop/chromebook.html", ftl_files="firefox/browsers/desktop/chromebook"),
        page("browsers/unsupported-systems/", "firefox/unsupported-systems.html"),
        path(
            "browsers/mobile/",
            prefer_cms(
                views.MobileBrowsersView.as_view(),
                fallback_ftl_files=["firefox/browsers/mobile/index"],
            ),
            name="firefox.browsers.mobile",
        ),
        path(
            "mobile/focus/",
            prefer_cms(
                L10nTemplateView.as_view(template_name="firefox/browsers/mobile/focus.html", ftl_files=["firefox/browsers/mobile/focus"]),
                fallback_ftl_files=["firefox/browsers/mobile/focus"],
            ),
            name="firefox.browsers.mobile.focus",
        ),
        path(
            "mobile/get-app/",
            prefer_cms(
                L10nTemplateView.as_view(template_name="firefox/browsers/mobile/get-app.html", ftl_files=["firefox/browsers/mobile/get-app"]),
                fallback_ftl_files=["firefox/browsers/mobile/get-app"],
            ),
            name="firefox.browsers.mobile.get_app",
        ),
    )
