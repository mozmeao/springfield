# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.test import override_settings

import pytest

User = get_user_model()


@pytest.fixture
def admin_client(client, db):
    """Force-login a superuser using the ModelBackend rather than the project's
    default SSO backend. Without the override, mozilla_django_oidc's
    SessionRefresh middleware sees an OIDC-authenticated user with no OIDC
    token in the session and redirects every admin GET to the auth0 login URL.
    """
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass",
        )
        client.force_login(admin, backend="django.contrib.auth.backends.ModelBackend")
        yield client
