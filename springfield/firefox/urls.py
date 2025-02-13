# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.urls import path, re_path

import springfield.releasenotes.views
from springfield.base.util import page
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
    path("", views.FirefoxHomeView.as_view(), name="firefox"),
    path("download/all/", views.firefox_all, name="firefox.all"),
    path("download/all/<slug:product_slug>/", views.firefox_all, name="firefox.all.platforms"),
    path("download/all/<slug:product_slug>/<str:platform>/", views.firefox_all, name="firefox.all.locales"),
    path("download/all/<slug:product_slug>/<str:platform>/<str:locale>/", views.firefox_all, name="firefox.all.download"),
    page("channel/desktop/", "firefox/channel/desktop.html", ftl_files=["firefox/channel"]),
    page("channel/android/", "firefox/channel/android.html", ftl_files=["firefox/channel"]),
    page("channel/ios/", "firefox/channel/ios.html", ftl_files=["firefox/channel"]),
    page("developer/", "firefox/developer/index.html", ftl_files=["firefox/developer"]),
    page("enterprise/", "firefox/enterprise/index.html", ftl_files=["firefox/enterprise"]),
    page("features/", "firefox/features/index.html", ftl_files=["firefox/features/index-2023", "firefox/features/shared"]),
    page("features/customize/", "firefox/features/customize.html", ftl_files=["firefox/features/customize-2023", "firefox/features/shared"]),
    page("features/add-ons/", "firefox/features/add-ons.html", ftl_files=["firefox/features/add-ons-2023", "firefox/features/shared"]),
    page(
        "features/pinned-tabs/",
        "firefox/features/pinned-tabs.html",
        ftl_files=["firefox/features/pinned-tabs-2023", "firefox/features/shared"],
    ),
    page("features/eyedropper/", "firefox/features/eyedropper.html", ftl_files=["firefox/features/eyedropper-2023", "firefox/features/shared"]),
    path("features/pdf-editor/", views.FirefoxFeaturesPDF.as_view(), name="firefox.features.pdf-editor"),
    path("features/adblocker/", views.FirefoxFeaturesAdBlocker.as_view(), name="firefox.features.adblocker"),
    page("features/bookmarks/", "firefox/features/bookmarks.html", ftl_files=["firefox/features/bookmarks-2023", "firefox/features/shared"]),
    path("features/fast/", views.FirefoxFeaturesFast.as_view(), name="firefox.features.fast"),
    page(
        "features/block-fingerprinting/",
        "firefox/features/fingerprinting.html",
        ftl_files=["firefox/features/fingerprinting", "firefox/features/shared"],
    ),
    page(
        "features/password-manager/",
        "firefox/features/password-manager.html",
        ftl_files=["firefox/features/password-manager-2023", "firefox/features/shared"],
    ),
    page(
        "features/private/",
        "firefox/features/private.html",
        ftl_files=["firefox/features/private-2023", "firefox/features/shared"],
    ),
    page(
        "features/private-browsing/",
        "firefox/features/private-browsing.html",
        ftl_files=["firefox/features/private-browsing-2023", "firefox/features/shared"],
    ),
    page("sync/", "firefox/features/sync.html", ftl_files=["firefox/features/sync-2023", "firefox/features/shared"]),
    path("translate/", views.firefox_features_translate, name="firefox.features.translate"),
    page(
        "features/picture-in-picture/",
        "firefox/features/picture-in-picture.html",
        ftl_files=["firefox/features/picture-in-picture", "firefox/features/shared"],
    ),
    path(
        "features/tips/",
        VariationTemplateView.as_view(
            template_name="firefox/features/tips/tips.html",
            template_context_variations=["picture-in-picture", "eyedropper", "forget"],
        ),
        name="firefox.features.tips",
    ),
    path(
        "features/complete-pdf/",
        VariationTemplateView.as_view(
            template_name="firefox/features/pdf-complete-fr.html", ftl_files=["firefox/features/shared"], active_locales=["fr"]
        ),
        name="firefox.features.pdf-complete",
    ),
    path(
        "features/free-pdf-editor/",
        VariationTemplateView.as_view(
            template_name="firefox/features/pdf-free-fr.html", ftl_files=["firefox/features/shared"], active_locales=["fr"]
        ),
        name="firefox.features.pdf-free",
    ),
    path("ios/testflight/", views.ios_testflight, name="firefox.ios.testflight"),
    path("download/", views.DownloadView.as_view(), name="firefox.download"),
    path("download/thanks/", views.DownloadThanksView.as_view(), name="firefox.download.thanks"),
    path("installer-help/", views.InstallerHelpView.as_view(), name="firefox.installer-help"),
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
    page("default/thanks/", "firefox/default/thanks.html", ftl_files="firefox/set-as-default/thanks"),
    # Default browser campaign
    page("default/", "firefox/default/landing.html", ftl_files="firefox/set-as-default/landing"),
)
