# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import Group
from django.urls import reverse

import pytest


@pytest.mark.django_db
def test_user_listing_shows_groups(admin_client, django_user_model):
    user = django_user_model.objects.create_user(username="editor", email="editor@example.com")
    user.groups.add(Group.objects.create(name="Copywriters"), Group.objects.create(name="Reviewers"))

    response = admin_client.get(reverse("wagtailusers_users:index"))

    assert response.status_code == 200
    assert b"Groups" in response.content
    assert b"Copywriters, Reviewers" in response.content
