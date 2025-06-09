# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

from springfield.redirects.util import mobile_app_redirector, platform_redirector, redirect

# matches only ASCII letters (ignoring case), numbers, dashes, periods, and underscores.
PARAM_VALUES_RE = re.compile(r"[\w.-]+", flags=re.ASCII)


def firefox_mobile_faq(request, *args, **kwargs):
    qs = request.META.get("QUERY_STRING", "")
    if "os=firefox-os" in qs:
        return "https://support.mozilla.org/products/firefox-os"

    return "https://support.mozilla.org/products/mobile"


def firefox_channel(*args, **kwargs):
    return platform_redirector("firefox.channel.desktop", "firefox.channel.android", "firefox.channel.ios")


def validate_param_value(param: str | None) -> str | None:
    """
    Returns the value passed in if it matches the regex `PARAM_VALUES_RE`.
    Otherwise returns `None`.
    """
    if param and PARAM_VALUES_RE.fullmatch(param):
        return param

    return None


def mobile_app(request, *args, **kwargs):
    product = request.GET.get("product")
    campaign = request.GET.get("campaign")

    if product not in {"firefox", "focus", "klar"}:
        product = "firefox"

    campaign = validate_param_value(campaign)

    return mobile_app_redirector(request, product, campaign)


redirectpatterns = (
    redirect(r"^download/?$", "firefox"),
    # bug 1299947, 1326383
    redirect(r"^channel/?$", firefox_channel(), cache_timeout=0, permanent=False),
    # issue https://github.com/mozilla/bedrock/issues/14172
    redirect(r"^browsers/mobile/app/?$", mobile_app, cache_timeout=0, query=False, permanent=False),
    # https://github.com/mozmeao/springfield/issues/222
    redirect(r"^os/?$", "https://support.mozilla.org/products/firefox-os?redirect_source=firefox-com", permanent=True),
    redirect(r"^desktop/?$", "firefox.browsers.desktop.index", permanent=False),
    redirect(r"^android/?$", "firefox.browsers.mobile.android", permanent=False),
    redirect(r"^developer/?$", "firefox.developer.index", permanent=False),
    redirect(r"^(10|independent)/?$", "firefox.features.index", permanent=True),
    redirect(r"^hello/?$", "https://support.mozilla.org/en-US/kb/hello-status?redirect_source=firefox-com", permanent=True),
    redirect(r"^personal/?$", "firefox", permanent=True),
    redirect(r"^choose/?$", "firefox", permanent=True),
    redirect(
        r"^switch/?$", "https://www.mozilla.org/firefox/switch/?redirect_source=firefox-com", permanent=False
    ),  # TODO pull this out when we port the page
    redirect(r"^enterprise/?$", "firefox.enterprise.index", permanent=False),
    redirect(
        r"^containers/?$", "https://www.mozilla.org/firefox/facebookcontainer/?redirect_source=firefox-com", permanent=False
    ),  # TODO remove or amend depending on whether we port the page
    redirect(r"^pdx/?$", "firefox", permanent=False),
    redirect(r"^pair/?$", "https://accounts.firefox.com/pair/", permanent=False),
    redirect(r"^(join|rejoindre)/?$", "https://www.mozilla.org/firefox/accounts/?redirect_source=join", permanent=False),
    redirect(r"^(privacy|privatsphaere)/?$", "https://www.mozilla.org/products/?redirect_source=firefox-com", permanent=False),
    redirect(r"^nightly/?$", "/channel/desktop/#nightly", permanent=False),
    redirect(
        r"^en-US/famil(y|ies)/?$",
        "https://www.mozilla.org/firefox/family/?utm_medium=referral&utm_source=firefox.com&utm_campaign=firefox-for-families",
        permanent=False,
    ),
    redirect(
        r"^en-US/famil(y|ies)/?\?.*$",
        "https://www.mozilla.org/firefox/family/",
        permanent=False,
    ),
)
