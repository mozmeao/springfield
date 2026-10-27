# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from wagtail.admin.ui.tables import Column
from wagtail.users.views import users


class UserIndexView(users.IndexView):
    """Wagtail's users listing with an extra column for each user's groups."""

    @cached_property
    def columns(self):
        return [
            *super().columns,
            Column(
                "groups",
                accessor=lambda user: ", ".join(sorted(group.name for group in user.groups.all())),
                label=_("Groups"),
            ),
        ]

    def get_base_queryset(self):
        return super().get_base_queryset().prefetch_related("groups")


class UserViewSet(users.UserViewSet):
    index_view_class = UserIndexView
