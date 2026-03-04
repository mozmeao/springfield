# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from wagtail.models import Page

from springfield.redirects.util import redirect


def _cms_page_exists(locale_code, path):
    """Check if a live CMS page exists at the given path for this locale.

    Uses the same url_path convention as CMSLocaleFallbackMiddleware:
    /home/{path} for the default locale, /home-{locale}/{path} for others.
    """
    url_path = path.strip("/") + "/"
    if locale_code == settings.LANGUAGE_CODE:
        root = "/home"
    else:
        root = f"/home-{locale_code}"
    return Page.objects.live().filter(url_path=f"{root}/{url_path}").exists()


def prefer_cms_redirect(pattern, to, **kwargs):
    """Like redirect(), but only fires when a live CMS page exists at
    the destination for the requested locale.

    When no page exists, the callable returns None, causing the redirect
    middleware to pass the request through to normal Django URL
    resolution — where the legacy FTL-based view can handle it.
    """

    def locale_aware_to(request, *args, **inner_kwargs):
        locale = inner_kwargs.get("locale", "").rstrip("/")
        locale = locale or settings.LANGUAGE_CODE
        if _cms_page_exists(locale, to):
            return to
        return None

    return redirect(pattern, locale_aware_to, **kwargs)
