# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Wagtail's v3 API, served only while the `WAGTAIL_API_ENABLED` waffle switch is on.

The switch lets the API be turned on for a working session and off again without a deploy.
No response is cacheable, so drafts never reach a shared cache and turning the switch on or off takes effect at once.
The copy endpoint is left out because it skips the hook that gives copied pages their own analytics IDs.
"""

import functools

from django.http import Http404, HttpResponseNotFound
from django.views.decorators.cache import never_cache

import waffle
from wagtail.api.v3.urls import api
from wagtail.utils.urlpatterns import decorate_urlpatterns

WAGTAIL_API_SWITCH = "WAGTAIL_API_ENABLED"


def require_wagtail_api_switch(view_func):
    @functools.wraps(view_func)
    def switched_view(request, *args, **kwargs):
        # Raw switch_is_active, not springfield.base.waffle.switch, which treats a missing switch as on when DEV=True.
        if not waffle.switch_is_active(WAGTAIL_API_SWITCH):
            return HttpResponseNotFound()
        try:
            return view_func(request, *args, **kwargs)
        except Http404:
            # Returned rather than raised, so never_cache marks it too
            return HttpResponseNotFound()

    return switched_view


EXCLUDED_URL_NAMES = {"pages_actions_copy"}

app_name = api.urls_namespace
urlpatterns = [pattern for pattern in api.urls[0] if pattern.name not in EXCLUDED_URL_NAMES]
urlpatterns = decorate_urlpatterns(urlpatterns, require_wagtail_api_switch)
urlpatterns = decorate_urlpatterns(urlpatterns, never_cache)
