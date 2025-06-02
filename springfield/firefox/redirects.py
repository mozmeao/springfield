# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.redirects.util import mobile_app_redirector, platform_redirector, redirect


def firefox_mobile_faq(request, *args, **kwargs):
    qs = request.META.get("QUERY_STRING", "")
    if "os=firefox-os" in qs:
        return "https://support.mozilla.org/products/firefox-os"

    return "https://support.mozilla.org/products/mobile"


def firefox_channel(*args, **kwargs):
    return platform_redirector("firefox.channel.desktop", "firefox.channel.android", "firefox.channel.ios")


def mobile_app(request, *args, **kwargs):
    product = request.GET.get("product")
    campaign = request.GET.get("campaign")

    if product not in {"firefox", "focus", "klar"}:
        product = "firefox"

    if campaign not in {"firefox-all"}:
        campaign = None

    return mobile_app_redirector(request, product, campaign)


redirectpatterns = (
    redirect(r"^download/?$", "firefox"),
    # bug 1299947, 1326383
    redirect(r"^channel/?$", firefox_channel(), cache_timeout=0),
    # issue https://github.com/mozilla/bedrock/issues/14172
    redirect(r"^browsers/mobile/app/?$", mobile_app, cache_timeout=0, query=False),
    # https://github.com/mozmeao/springfield/issues/222
    redirect(r"^os/?$", "https://support.mozilla.org/products/firefox-os?redirect_source=firefox-com"),
    redirect(r"^desktop/?$", "firefox.browsers.desktop.index"),
    redirect(r"^android/?$", "firefox.browsers.mobile.android"),
    redirect(r"^developer/?$", "firefox.developer.index"),
    redirect(r"^(10|independent)/?$", "firefox.features.index"),
    redirect(r"^hello/?$", "https://support.mozilla.org/en-US/kb/hello-status?redirect_source=firefox-com"),
    redirect(r"^personal/?$", "firefox"),
    redirect(r"^choose/?$", "firefox"),
    redirect(r"^switch/?$", "https://www.mozilla.org/firefox/switch/?redirect_source=firefox-com"),  # TODO pull this out when we port the page
    redirect(r"^enterprise/?$", "firefox.enterprise.index"),
    redirect(
        r"^containers/?$", "https://www.mozilla.org/firefox/facebookcontainer/?redirect_source=firefox-com"
    ),  # TODO remove or amend depending on whether we port the page
    redirect(r"^pdx/?$", "firefox"),
    redirect(r"^pair/?$", "https://accounts.firefox.com/pair/"),
    redirect(r"^(join|rejoindre)/?$", "https://www.mozilla.org/firefox/accounts/?redirect_source=join"),
    redirect(r"^(privacy|privatsphaere)/?$", "https://www.mozilla.org/products/?redirect_source=firefox-com"),
    redirect(r"^nightly/?$", "/channel/desktop/#nightly"),
    redirect(
        r"^en-US/famil(y|ies)/?$",
        "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families",
    ),
    redirect(r"^en-US/famil(y|ies)/?\?.*$", "https://www.mozilla.org/firefox/family/"),
)
