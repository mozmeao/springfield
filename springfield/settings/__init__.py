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

# NOTE: Any URLs that contain a path, not just the origin, trailing slashes are important.
# - if no path is provided, all resources are allowed from the origin.
# - if path is provided with no trailing slash: an exact-match is required.
#   - e.g. `https://example.com/api` will only match `https://example.com/api`
# - if path is provided with trailing slash: the path is a prefix-match.
#   - e.g. `https://example.com/api/` will match anything that starts with `https://example.com/api/`


CSP_ASSETS_HOST = config("CSP_ASSETS_HOST", default="")

_csp_default_src = {
    # Keep `default-src` minimal. Best to set resources in the specific directives.
    csp.constants.SELF,
}
_csp_connect_src = {
    # NOTE: Check if these need to be in the `_csp_form_action` list as well since we often
    # progressively enhance forms by using Javascript.
    csp.constants.SELF,
    CSP_ASSETS_HOST,
    BASKET_URL,
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "region1.google-analytics.com",
    "o1069899.sentry.io",
    "o1069899.ingest.sentry.io",
    "o1069899.ingest.us.sentry.io",
    FXA_ENDPOINT,  # noqa: F405
    "telemetry.transcend.io",  # Transcend Consent Management
    "telemetry.us.transcend.io",  # Transcend Consent Management
}
_csp_font_src = {
    csp.constants.SELF,
    CSP_ASSETS_HOST,
}
_csp_form_action = {
    csp.constants.SELF,
    # NOTE: Check if these need to be in the `_csp_connect_src` list as well since we often
    # progressively enhance forms by using Javascript.
    BASKET_URL,
    FXA_ENDPOINT,
}
# On hosts with wagtail admin enabled, we need to allow the admin to frame itself for previews.
_csp_frame_ancestors = {
    csp.constants.SELF if WAGTAIL_ENABLE_ADMIN else csp.constants.NONE,
}
_csp_frame_src = {
    csp.constants.SELF,
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "accounts.firefox.com",
    "www.youtube.com",
    "www.youtube-nocookie.com",
}
_csp_img_src = {
    csp.constants.SELF,
    CSP_ASSETS_HOST,
    "data:",
    "www.mozilla.org",  # mainly for release notes images.
    "www.googletagmanager.com",
    "www.google-analytics.com",
}
_csp_media_src = {
    csp.constants.SELF,
    CSP_ASSETS_HOST,
    "www.mozilla.org",  # mainly for release notes videos.
    "assets.mozilla.net",
    "videos.cdn.mozilla.net",
}
_csp_script_src = {
    csp.constants.SELF,
    CSP_ASSETS_HOST,
    # TODO change settings so we don't need unsafes even in dev
    csp.constants.UNSAFE_INLINE,
    csp.constants.UNSAFE_EVAL,
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "tagmanager.google.com",
    "www.youtube.com",
    "s.ytimg.com",
    "cdn.transcend.io",  # Transcend Consent Management
    "transcend-cdn.com",  # Transcend Consent Management
}
_csp_style_src = {
    csp.constants.SELF,
    CSP_ASSETS_HOST,
}
# # TODO change settings so we don't need unsafes even in dev
if config("ENABLE_DJANGO_PATTERN_LIBRARY", parser=bool, default="False"):
    _csp_style_src.add(csp.constants.UNSAFE_INLINE)

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
if csp_extra_frame_src := config("CSP_EXTRA_FRAME_SRC", default="", parser=ListOf(str, allow_empty=False)):  # noqa: F405
    _csp_frame_src |= set(csp_extra_frame_src)
csp_report_uri = config("CSP_REPORT_URI", default="") or None  # noqa: F405
csp_ro_report_uri = config("CSP_RO_REPORT_URI", default="") or None  # noqa: F405

CONTENT_SECURITY_POLICY = {
    # Default report percentage to 1% just in case the env var isn't set, we don't want to bombard Sentry.
    "REPORT_PERCENTAGE": config("CSP_REPORT_PERCENTAGE", default="1.0", parser=float),  # noqa: F405
    "DIRECTIVES": {
        "default-src": _csp_default_src,
        "base-uri": {csp.constants.NONE},
        "connect-src": _csp_connect_src,
        "font-src": _csp_font_src,
        "form-action": _csp_form_action,
        "frame-ancestors": _csp_frame_ancestors,
        "frame-src": _csp_frame_src,
        "img-src": _csp_img_src,
        "media-src": _csp_media_src,
        "object-src": {csp.constants.NONE},
        "script-src": _csp_script_src,
        "style-src": _csp_style_src,
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
# The CMS admin needs unsafe-inline styles for now.
CMS_ADMIN_CSP = _override_csp(CONTENT_SECURITY_POLICY, append={"style-src": {csp.constants.UNSAFE_INLINE}})
CMS_ADMIN_CSP_RO = csp_ro_report_uri and _override_csp(CONTENT_SECURITY_POLICY, append={"style-src": {csp.constants.UNSAFE_INLINE}})

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
