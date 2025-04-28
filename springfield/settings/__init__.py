# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging.config
import sys
from copy import deepcopy

import csp.constants

from .base import *  # noqa: F403, F405

# This file:
# 1. Handles setting specific settings based on the site Springfield is serving - currently Firefox.com
# 2. Tweaks some settings if Django can detect we're running tests
# 3. django_csp settings
# 4. Sets a number of general settings applicable to all site modes


ROOT_URLCONF = "springfield.urls"

# CSP settings, expanded upon later:
# NOTE: We are providing all settings to django-csp as sets, not lists.
# - This is for de-duping, and because django-csp will convert them to `sorted` lists for us.
_csp_default_src = {
    csp.constants.SELF,
    "*.firefox.com",
    "assets.mozilla.net",
}
_csp_img_src = {
    "data:",
    "www.googletagmanager.com",
    "www.google-analytics.com",
}
_csp_script_src = {
    # TODO change settings so we don't need unsafes even in dev
    csp.constants.UNSAFE_INLINE,
    csp.constants.UNSAFE_EVAL,
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "tagmanager.google.com",
    "www.youtube.com",
    "s.ytimg.com",
}
_csp_style_src = {
    # TODO fix things so that we don't need this
    csp.constants.UNSAFE_INLINE,
}
_csp_frame_src = {
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "accounts.firefox.com",
    "www.youtube.com",
}
_csp_connect_src = {
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "region1.google-analytics.com",
    "sentry.prod.mozaws.net",  # DEPRECATED. TODO: remove this once all sites are talking to sentry.io instead
    "o1069899.sentry.io",
    "o1069899.ingest.sentry.io",
    FXA_ENDPOINT,  # noqa: F405
}
_csp_font_src = set()

# 2. TEST-SPECIFIC SETTINGS
# TODO: make this selectable by an env var, like the other modes
if (len(sys.argv) > 1 and sys.argv[1] == "test") or "pytest" in sys.modules:
    # Using the CachedStaticFilesStorage for tests breaks all the things.
    STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405
    # TEMPLATE_DEBUG has to be True for Jinja to call the template_rendered
    # signal which Django's test client uses to save away the contexts for your
    # test to look at later.
    TEMPLATES[0]["OPTIONS"]["debug"] = True  # noqa: F405
    # use default product-details data
    PROD_DETAILS_STORAGE = "product_details.storage.PDFileStorage"

    # If we're using sqlite, run tests on an in-memory version, else use the configured default DB engine
    if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
        DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}


# 3. DJANGO-CSP SETTINGS
if extra_csp_default_src := config("CSP_DEFAULT_SRC", default="", parser=ListOf(str, allow_empty=False)):  # noqa: F405
    _csp_default_src |= set(extra_csp_default_src)
if extra_csp_connect_src := config("CSP_CONNECT_SRC", default="", parser=ListOf(str, allow_empty=False)):  # noqa: F405
    _csp_connect_src |= set(extra_csp_connect_src)
_csp_frame_src |= _csp_default_src
if csp_extra_frame_src := config("CSP_EXTRA_FRAME_SRC", default="", parser=ListOf(str, allow_empty=False)):  # noqa: F405
    _csp_child_src |= set(csp_extra_frame_src)
csp_report_uri = config("CSP_REPORT_URI", default="") or None  # noqa: F405
csp_ro_report_uri = config("CSP_RO_REPORT_URI", default="") or None  # noqa: F405
# On hosts with wagtail admin enabled, we need to allow the admin to frame itself for previews.
if WAGTAIL_ENABLE_ADMIN:  # noqa: F405
    _csp_frame_ancestors = {csp.constants.SELF}
else:
    _csp_frame_ancestors = {csp.constants.NONE}

CONTENT_SECURITY_POLICY = {
    # Default report percentage to 1% just in case the env var isn't set, we don't want to bombard Sentry.
    "REPORT_PERCENTAGE": config("CSP_REPORT_PERCENTAGE", default="1.0", parser=float),  # noqa: F405
    "DIRECTIVES": {
        "default-src": _csp_default_src,
        "connect-src": _csp_default_src | _csp_connect_src,
        "font-src": _csp_default_src | _csp_font_src,
        "frame-ancestors": _csp_frame_ancestors,
        "frame-src": _csp_frame_src,
        "img-src": _csp_default_src | _csp_img_src,
        "script-src": _csp_default_src | _csp_script_src,
        "style-src": _csp_default_src | _csp_style_src,
        "upgrade-insecure-requests": False if DEBUG else True,  # noqa: F405
        "report-uri": csp_report_uri,
    },
}

# Only set up report-only CSP if we have a report-uri set.
CONTENT_SECURITY_POLICY_REPORT_ONLY = None
if csp_ro_report_uri:
    # Copy CSP and override report-uri for report-only.
    CONTENT_SECURITY_POLICY_REPORT_ONLY = deepcopy(CONTENT_SECURITY_POLICY)
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["report-uri"] = csp_ro_report_uri

    # CSP directive updates we're testing that we hope to move to the enforced policy.
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["default-src"] = {csp.constants.SELF}
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["base-uri"] = {csp.constants.NONE}
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["media-src"] = {csp.constants.SELF, "assets.mozilla.net", "videos.cdn.mozilla.net"}
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["object-src"] = {csp.constants.NONE}
    CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]["style-src"] -= {csp.constants.UNSAFE_INLINE}


# `CSP_PATH_OVERRIDES` and `CSP_PATH_OVERRIDES_REPORT_ONLY` are mainly for overriding CSP settings
# for CMS admin, but can override other paths.  Works in conjunction with the
# `springfield.base.middleware.CSPMiddlewareByPathPrefix` middleware.


def _override_csp(
    csp: dict[str, dict[str, set[str]]],
    append: dict[str, set[str]] = None,
    replace: dict[str, set[str]] = None,
) -> dict[str, dict[str, set[str]]]:
    # Don't modify the original CSP settings.
    csp = deepcopy(csp)

    if append is not None:
        for key, value in append.items():
            csp["DIRECTIVES"][key] = csp["DIRECTIVES"].get(key, set()) | value

    if replace is not None:
        for key, value in replace.items():
            csp["DIRECTIVES"][key] = value

    return csp


#
# Path based overrides.
#

# /cms-admin/images/ loads just-uploaded images as blobs.
CMS_ADMIN_IMAGES_CSP = _override_csp(CONTENT_SECURITY_POLICY, append={"img-src": {"blob:"}})
CMS_ADMIN_IMAGES_CSP_RO = csp_ro_report_uri and _override_csp(CONTENT_SECURITY_POLICY_REPORT_ONLY, append={"img-src": {"blob:"}})
# The CMS admin frames itself for page previews.
CMS_ADMIN_CSP = _override_csp(CONTENT_SECURITY_POLICY, replace={"frame-ancestors": {csp.constants.SELF}})
CMS_ADMIN_CSP_RO = csp_ro_report_uri and _override_csp(CONTENT_SECURITY_POLICY_REPORT_ONLY, replace={"frame-ancestors": {csp.constants.SELF}})

CSP_PATH_OVERRIDES = {
    # Order them from most specific to least.
    "/cms-admin/images/": CMS_ADMIN_IMAGES_CSP,
    "/cms-admin/": CMS_ADMIN_CSP,
}

# Path based overrides for report-only CSP.
if csp_ro_report_uri:
    CSP_PATH_OVERRIDES_REPORT_ONLY = {
        # Order them from most specific to least.
        "/cms-admin/images/": CMS_ADMIN_IMAGES_CSP_RO,
        "/cms-admin/": CMS_ADMIN_CSP_RO,
    }

if not DEV:  # noqa: F405
    MIDDLEWARE += ["springfield.base.middleware.FrameOptionsHeader"]  # noqa: F405


if CACHES["default"]["BACKEND"] == "django_pylibmc.memcached.PyLibMCCache":  # noqa: F405
    CACHES["default"]["BINARY"] = True  # noqa: F405
    CACHES["default"]["OPTIONS"] = {  # Maps to pylibmc "behaviors"  # noqa: F405
        "tcp_nodelay": True,
        "ketama": True,
    }

# cache for Fluent files
CACHES["fluent"] = {  # noqa: F405
    "BACKEND": "springfield.base.cache.SimpleDictCache",
    "LOCATION": "fluent",
    "TIMEOUT": FLUENT_CACHE_TIMEOUT,  # noqa: F405
    "OPTIONS": {
        "MAX_ENTRIES": 5000,
        "CULL_FREQUENCY": 4,  # 1/4 entries deleted if max reached
    },
}

# cache for product details
CACHES["product-details"] = {  # noqa: F405
    "BACKEND": "springfield.base.cache.SimpleDictCache",
    "LOCATION": "product-details",
    "OPTIONS": {
        "MAX_ENTRIES": 200,  # currently 104 json files
        "CULL_FREQUENCY": 4,  # 1/4 entries deleted if max reached
    },
}

# cache for release notes
CACHES["release-notes"] = {  # noqa: F405
    "BACKEND": "springfield.base.cache.SimpleDictCache",
    "LOCATION": "release-notes",
    "TIMEOUT": 5,
    "OPTIONS": {
        "MAX_ENTRIES": 300,  # currently 564 json files but most are rarely accessed
        "CULL_FREQUENCY": 4,  # 1/4 entries deleted if max reached
    },
}

# cache for generated QR codes
CACHES["qrcode"] = {  # noqa: F405
    "BACKEND": "springfield.base.cache.SimpleDictCache",
    "LOCATION": "qrcode",
    "TIMEOUT": None,
    "OPTIONS": {
        "MAX_ENTRIES": 20,
        "CULL_FREQUENCY": 4,  # 1/4 entries deleted if max reached
    },
}

MEDIA_URL = CDN_BASE_URL + MEDIA_URL  # noqa: F405
STATIC_URL = CDN_BASE_URL + STATIC_URL  # noqa: F405
logging.config.dictConfig(LOGGING)  # noqa: F405
