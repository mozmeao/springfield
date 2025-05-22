# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.deprecation import MiddlewareMixin


METHOD_OVERRIDE_HEADER = "HTTP_X_HTTP_METHOD_OVERRIDE"


class PatchOverrideMiddleware(MiddlewareMixin):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.method == "POST" and request.META.get(METHOD_OVERRIDE_HEADER) == "PATCH":
            request.method = "PATCH"
