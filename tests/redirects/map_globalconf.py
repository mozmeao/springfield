# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from .base import flatten, url_test

UA_ANDROID = {"User-Agent": "Mozilla/5.0 (Android 6.0.1; Mobile; rv:51.0) Gecko/51.0 Firefox/51.0"}
UA_IOS = {"User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3 like Mac OS X; de-de) AppleWebKit/533.17.9 (KHTML, like Gecko) Mobile/8F190"}

URLS = flatten(
    (
        # START https://github.com/mozmeao/springfield/issues/222
        url_test("/os/", "https://support.mozilla.org/products/firefox-os?redirect_source=firefox-com", status_code=302),
        url_test("/desktop/", "/browsers/desktop/", status_code=302),
        url_test("/android/", "/browsers/mobile/android/", status_code=302),
        url_test("/developer/", "/channel/desktop/developer/", status_code=302),
        url_test("/10/", "/features/", status_code=302),
        url_test("/independent/", "/features/", status_code=302),
        url_test("/hello/", "https://support.mozilla.org/en-US/kb/hello-status?redirect_source=firefox-com", status_code=302),
        url_test("/personal/", "/", status_code=302),
        url_test("/choose/", "/", status_code=302),
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
        # END https://github.com/mozmeao/springfield/issues/222
    )
)
