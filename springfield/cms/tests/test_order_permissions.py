# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import Group

import pytest

ORDER_PERMISSIONS = {"add_order", "change_order", "delete_order", "view_order"}


@pytest.mark.django_db
@pytest.mark.parametrize("group_name", ["Editors", "Moderators"])
def test_the_editing_groups_can_manage_smartling_orders(group_name):
    """The order screens are closed to anyone without these."""
    group = Group.objects.get(name=group_name)

    granted = set(
        group.permissions.filter(
            content_type__app_label="wagtail_localize_smartling",
            content_type__model="order",
        ).values_list("codename", flat=True)
    )

    assert granted == ORDER_PERMISSIONS
