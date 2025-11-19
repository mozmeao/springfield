# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from .base import flatten, url_test

UA_ANDROID = {"User-Agent": "Mozilla/5.0 (Android 6.0.1; Mobile; rv:51.0) Gecko/51.0 Firefox/51.0"}
UA_IOS = {"User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3 like Mac OS X; de-de) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8F190"}

URLS = flatten(
    (
        # issue 222
        url_test("/os/", "https://support.mozilla.org/products/firefox-os?redirect_source=firefox-com", status_code=301),
        url_test("/desktop/", "/browsers/desktop/", status_code=302),
        url_test("/android/", "/browsers/mobile/android/", status_code=302),
        url_test("/developer/", "/channel/desktop/developer/", status_code=302),
        url_test("/10/", "/features/", status_code=301),
        url_test("/independent/", "/features/", status_code=301),
        url_test("/hello/", "https://support.mozilla.org/en-US/kb/hello-status?redirect_source=firefox-com", status_code=301),
        url_test("/personal/", "/", status_code=301),
        url_test("/choose/", "/", status_code=301),
        url_test("/switch/", "https://www.mozilla.org/firefox/switch/?redirect_source=firefox-com", status_code=302),
        url_test("/enterprise/", "/browsers/enterprise/", status_code=302),
        url_test("/containers/", "https://www.mozilla.org/firefox/facebookcontainer/?redirect_source=firefox-com", status_code=302),
        url_test("/pdx/", "/", status_code=302),
        url_test("/pair/", "https://accounts.firefox.com/pair/", status_code=302),
        url_test("/join/", "https://www.mozilla.org/firefox/accounts/?redirect_source=join", status_code=302),
        url_test("/rejoindre/", "https://www.mozilla.org/firefox/accounts/?redirect_source=join", status_code=302),
        url_test("/privacy/", "https://www.mozilla.org/products/?redirect_source=firefox-com", status_code=302),
        url_test("/privatsphaere/", "https://www.mozilla.org/products/?redirect_source=firefox-com", status_code=302),
        url_test("/nightly/", "/channel/desktop/#nightly", status_code=302),
        url_test(
            "/family/",
            "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families",
            follow_redirects=True,
        ),
        url_test(
            "/families/",
            "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families",
            follow_redirects=True,
        ),
        url_test("/family/?query=string", "https://www.mozilla.org/firefox/family/", follow_redirects=True, final_status_code=200),
        url_test("/families/?query=string", "https://www.mozilla.org/firefox/family/", follow_redirects=True, final_status_code=200),
        # issue 260
        # bug 1041712, 1069335, 1069902
        url_test(
            "/{firefox,mobile}/{2,19,27}.0{a2,beta,.2}/{release,aurora}notes/{,stuff}",
            "http://website-archive.mozilla.org/www.mozilla.org/firefox_releasenotes/en-US"
            "/{firefox,mobile}/{2,19,27}.0{a2,beta,.2}/{release,aurora}notes/{,stuff}",
        ),
        # bug 947890, 1069902
        url_test(
            "/firefox/releases/{0.9.1,1.5.0.1}.html",
            "http://website-archive.mozilla.org/www.mozilla.org/firefox_releasenotes/en-US/firefox/releases/{0.9.1,1.5.0.1}.html",
        ),
        url_test(
            "/{firefox,mobile}/{2,9,18,25}.0/releasenotes/",
            "http://website-archive.mozilla.org/www.mozilla.org/firefox_releasenotes/en-US/{firefox,mobile}/{2,9,18,25}.0/releasenotes/",
        ),
        # bug 988746, 989423, 994186, 1153351
        url_test("/mobile/{23,28,29}.0/releasenotes/", "/firefox/android/{23,28,29}.0/releasenotes/"),
        url_test("/mobile/{3,4}2.0beta/{aurora,release}notes/", "/firefox/android/{3,4}2.0beta/{aurora,release}notes/"),
        # bug 868182
        url_test("/mobile/faq/?os=firefox-os", "https://support.mozilla.org/products/firefox-os"),
        url_test("/mobile/faq/", "https://support.mozilla.org/products/mobile"),
        # issue 765, https://github.com/mozilla/bedrock/issues/14172
        url_test(
            "/browsers/mobile/app/?product=firefox",
            "https://play.google.com/store/apps/details?id=org.mozilla.firefox",
            req_headers=UA_ANDROID,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/",
            "https://apps.apple.com/app/apple-store/id989804926",
            req_headers=UA_IOS,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?campaign=firefox-whatsnew",
            "https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-whatsnew",
            req_headers=UA_ANDROID,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?c=firefox-whatsnew",
            "https://apps.apple.com/app/apple-store/id989804926?mz_pr=firefox_mobile&pt=373246&ct=firefox-whatsnew&mt=8",
            req_headers=UA_IOS,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?product=focus&campaign=firefox-browsers-mobile-focus",
            "https://play.google.com/store/apps/details?id=org.mozilla.focus&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-browsers-mobile-focus",
            req_headers=UA_ANDROID,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?p=focus&c=firefox-browsers-mobile-focus",
            "https://apps.apple.com/app/apple-store/id1055677337?mz_pr=focus&pt=373246&ct=firefox-browsers-mobile-focus&mt=8",
            req_headers=UA_IOS,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?product=klar&campaign=firefox-browsers-mobile-focus",
            "https://play.google.com/store/apps/details?id=org.mozilla.klar&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-browsers-mobile-focus",
            req_headers=UA_ANDROID,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/browsers/mobile/app/?product=klar&campaign=firefox-browsers-mobile-focus",
            "https://apps.apple.com/app/apple-store/id1073435754?mz_pr=klar&pt=373246&ct=firefox-browsers-mobile-focus&mt=8",
            req_headers=UA_IOS,
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
        url_test(
            "/qr/?c=firefox-whatsnew",
            "https://apps.apple.com/app/apple-store/id989804926?mz_pr=firefox_mobile&pt=373246&ct=firefox-whatsnew&mt=8",
            resp_headers={"Cache-Control": "max-age=0"},
            status_code=302,
        ),
    )
)
