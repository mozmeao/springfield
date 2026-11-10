# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Wagtail's v3 API, served only while the `wagtail_api` waffle switch is on.

The switch lets the API be turned on for a working session and off again without a deploy.
No response is cacheable, so drafts never reach a shared cache and turning the switch off takes effect at once.
"""

from django.http import Http404
from django.views.decorators.cache import never_cache

import waffle
from wagtail.api.v3.urls import api
from wagtail.utils.urlpatterns import decorate_urlpatterns

WAGTAIL_API_SWITCH = "WAGTAIL_API_ENABLED"


def require_wagtail_api_switch(view_func):
    def switched_view(request, *args, **kwargs):
        # Raw switch_is_active, not springfield.base.waffle.switch, which treats a missing switch as on when DEV=True.
        if not waffle.switch_is_active(WAGTAIL_API_SWITCH):
            raise Http404
        return view_func(request, *args, **kwargs)

    return switched_view


app_name = api.urls_namespace
urlpatterns = decorate_urlpatterns(api.urls[0], require_wagtail_api_switch)
urlpatterns = decorate_urlpatterns(urlpatterns, never_cache)
