# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

import pytest

from springfield.cms.tests.factories import LocaleFactory


@pytest.fixture
def admin_client(client, db):
    """Force-login a superuser using the ModelBackend rather than the project's
    default SSO backend. Without the override, mozilla_django_oidc's
    SessionRefresh middleware sees an OIDC-authenticated user with no OIDC
    token in the session and redirects every admin GET to the auth0 login URL
    (302) — which would break the 302/200 assertions below.
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


@pytest.fixture
def fr_locale(db):
    """The `fr` Locale must exist in the DB so Wagtail's LocaleFilter doesn't
    404 on `?locale=fr`. (When the filter 404s, Django's LocaleMiddleware
    rewrites the URL to add a language prefix — a side-effect that's unrelated
    to our locale-defaulting feature but pollutes the test assertions.)
    """
    return LocaleFactory(language_code="fr")


LISTING_URL = reverse("wagtailsnippets_cms_pretranslatedphrase:list")
RESULTS_URL = reverse("wagtailsnippets_cms_pretranslatedphrase:list_results")
CHOOSER_URL = reverse("wagtailsnippetchoosers_cms_pretranslatedphrase:choose")


@pytest.mark.django_db
class TestPretranslatedPhraseListingLocaleDefault:
    """Locks the key-presence-not-value-truthiness rule on `?locale=`."""

    def test_listing_with_no_locale_param_redirects_to_default_locale(self, admin_client):
        """GETting the list URL redirects to the list URL with locale=en-US."""
        response = admin_client.get(LISTING_URL)
        assert response.status_code == 302
        assert response["Location"].endswith("?locale=en-US")

    def test_listing_with_explicit_locale_param_does_not_redirect(self, admin_client, fr_locale):
        """GETting the list URL with a locale parameter does not redirect."""
        response = admin_client.get(LISTING_URL + "?locale=fr")
        assert response.status_code == 200

    def test_listing_with_empty_locale_param_does_not_redirect(self, admin_client):
        """
        GETting the list URL with an empty locale parameter does not redirect.

        Having "locale=" in the URL is considered the "All locales" choice.
        """
        response = admin_client.get(LISTING_URL + "?locale=")
        assert response.status_code == 200

    def test_results_only_endpoint_does_not_redirect(self, admin_client):
        """
        GETting the results URL does not redirect.

        The /results/ AJAX endpoint is re-fetched by the inline filter form on
        every change. Redirecting that AJAX call would break the filter form
        and/or cause infinite redirect loops.
        """
        response = admin_client.get(RESULTS_URL)
        assert response.status_code == 200


@pytest.mark.django_db
class TestPretranslatedPhraseChooserNotRedirected:
    """
    Add explicit asserts for the chooser modal, to trigger failures on changes in Wagtail.
    """

    def test_chooser_modal_does_not_redirect_to_en_us(self, admin_client):
        response = admin_client.get(CHOOSER_URL)
        assert response.status_code == 200
        assert "Location" not in response
