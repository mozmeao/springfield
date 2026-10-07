# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from wagtail.users.apps import WagtailUsersAppConfig


class UsersConfig(WagtailUsersAppConfig):
    """Replaces `wagtail.users` in INSTALLED_APPS to serve our users views."""

    user_viewset = "springfield.users.views.UserViewSet"
