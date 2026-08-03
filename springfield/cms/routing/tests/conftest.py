# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.test import override_settings

import pytest

from springfield.cms.routing.signals import RoutingSignal, Source, ValueType, registry

User = get_user_model()


@pytest.fixture
def temp_signal():
    """Register a throwaway signal into the global registry, then clean it up.

    Lets a test prove the reference page reflects registry changes with no page edit.
    """
    signal = RoutingSignal(
        name="temp_test_signal",
        description="Temporary signal for testing the reference page.",
        source=Source.URL,
        value_type=ValueType.STRING,
    )
    registry.register(signal)
    try:
        yield signal
    finally:
        registry._signals.pop(signal.name, None)


@pytest.fixture
def admin_client(client, db):
    """Superuser client using the ModelBackend, mirroring cms/tests/conftest.py.

    Locally ``USE_SSO_AUTH=False`` strips the OIDC middleware, but a naive
    ``force_login`` on a staff user 302s to Auth0 on CI; the override keeps the admin
    views returning 200 in both places.
    """
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        admin = User.objects.create_superuser(username="routing-admin", email="routing-admin@example.com", password="adminpass")
        client.force_login(admin, backend="django.contrib.auth.backends.ModelBackend")
        yield client
