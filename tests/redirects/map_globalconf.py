# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from .base import flatten, url_test

UA_ANDROID = {"User-Agent": "Mozilla/5.0 (Android 6.0.1; Mobile; rv:51.0) Gecko/51.0 Firefox/51.0"}
UA_IOS = {"User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3 like Mac OS X; de-de) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8F190"}

URLS = flatten(
    (
        # START https://github.com/mozmeao/springfield/issues/222
        url_test("/os/", "https://support.mozilla.org/products/firefox-os?redirect_source=firefox-com"),
        url_test("/desktop/", "/browsers/desktop/"),
        url_test("/android/", "/browsers/mobile/android/"),
        url_test("/developer/", "/channel/desktop/developer/"),
        url_test("/10/", "/features/"),
        url_test("/independent/", "/features/"),
        url_test("/hello/", "https://support.mozilla.org/en-US/kb/hello-status?redirect_source=firefox-com"),
        url_test("/personal/", "/"),
        url_test("/choose/", "/"),
        url_test("/switch/", "https://www.mozilla.org/en-GB/firefox/switch/?redirect_source=firefox-com"),
        url_test("/enterprise/", "/browsers/enterprise/"),
        url_test("/containers/", "https://www.mozilla.org/firefox/facebookcontainer/?redirect_source=firefox-com"),
        url_test("/pdx/", "/"),
        url_test("/pair/", "https://accounts.firefox.com/pair/"),
        url_test("/join/", "https://www.mozilla.org/firefox/accounts/?redirect_source=join"),
        url_test("/rejoindre/", "https://www.mozilla.org/firefox/accounts/?redirect_source=join"),
        url_test("/privacy/", "https://www.mozilla.org/products/?redirect_source=firefox-com"),
        url_test("/privatsphaere/", "https://www.mozilla.org/products/?redirect_source=firefox-com"),
        url_test("/nightly/", "/channel/desktop/#nightly`"),
        url_test("/family/", "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families"),
        url_test(
            "/families/", "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families"
        ),
        url_test("/family/some/path", "https://www.mozilla.org/firefox/family/"),
        url_test("/families/some/path", "https://www.mozilla.org/firefox/family/"),
        # END https://github.com/mozmeao/springfield/issues/222
    )
)
