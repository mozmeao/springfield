# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

import pytest
from wagtail.models import TranslatableMixin
from wagtail.snippets.models import get_snippet_models

from springfield.cms.tests.factories import LocaleFactory

EXPECTED_TRANSLATABLE_SNIPPETS = {
    "BannerSnippet",
    "DownloadFirefoxCallToActionSnippet",
    "PencilBannerSnippet",
    "PreFooterCTAFormSnippet",
    "PreFooterCTASnippet",
    "PretranslatedPhrase",
    "QRCodeFloatingSnippet",
    "QRCodeSnippet",
    "ScrollToSeeMoreSnippet",
    "SetAsDefaultSnippet",
    "Tag",
}

TRANSLATABLE_SNIPPET_MODELS = [m for m in get_snippet_models() if issubclass(m, TranslatableMixin)]


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


def _listing_url(model):
    return reverse(f"wagtailsnippets_{model._meta.app_label}_{model._meta.model_name}:list")


def _results_url(model):
    return reverse(f"wagtailsnippets_{model._meta.app_label}_{model._meta.model_name}:list_results")


def _chooser_url(model):
    return reverse(f"wagtailsnippetchoosers_{model._meta.app_label}_{model._meta.model_name}:choose")


@pytest.mark.django_db
def test_snippet_registry_matches_expected():
    """
    Test meant to catch accidentally forgetting to update which snippets should be translatable.

    The goal here is to ensure that each snippet that is translatable (using TranslatableMixin)
    also uses the LocaleDefaultingSnippetViewSet.
    If a translatable snippet is added and does not use the LocaleDefaultingSnippetViewSet,
    then it will fail some tests in this file.
    """
    discovered = {m.__name__ for m in TRANSLATABLE_SNIPPET_MODELS}
    assert discovered == EXPECTED_TRANSLATABLE_SNIPPETS


@pytest.mark.django_db
@pytest.mark.parametrize("model", TRANSLATABLE_SNIPPET_MODELS, ids=lambda m: m.__name__)
class TestSnippetListingLocaleDefault:
    """
    Verifies the rule for the `locale` kwarg across every translatable snippet model.

     - GETting the list URL redirects to the list URL with locale=en-US
     - GETting the list URL with a locale parameter does not redirect
     - GETting the list URL with an empty locale parameter does not redirect
     - GETting the results URL does not redirect
    """

    def test_listing_with_no_locale_param_redirects_to_default_locale(self, model, admin_client):
        """GETting the list URL redirects to the list URL with locale=en-US."""
        response = admin_client.get(_listing_url(model))
        assert response.status_code == 302
        assert response["Location"].endswith("?locale=en-US")

    def test_listing_with_explicit_locale_param_does_not_redirect(self, model, admin_client, fr_locale):
        """GETting the list URL with a locale parameter does not redirect."""
        response = admin_client.get(_listing_url(model) + "?locale=fr")
        assert response.status_code == 200

    def test_listing_with_empty_locale_param_does_not_redirect(self, model, admin_client):
        """
        GETting the list URL with an empty locale parameter does not redirect.

        Having "locale=" in the URL is considered the "All locales" choice.
        """
        response = admin_client.get(_listing_url(model) + "?locale=")
        assert response.status_code == 200

    def test_results_only_endpoint_does_not_redirect(self, model, admin_client):
        """
        GETting the results URL does not redirect.

        The /results/ AJAX endpoint is re-fetched by the inline filter form on
        every change. Redirecting that AJAX call would break the filter form
        and/or cause infinite redirect loops.
        """
        response = admin_client.get(_results_url(model))
        assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("model", TRANSLATABLE_SNIPPET_MODELS, ids=lambda m: m.__name__)
def test_chooser_modal_does_not_redirect_to_en_us(model, admin_client):
    """
    The chooser modal is a separate ChooseView and must NOT receive the
    listing-level locale-defaulting redirect — otherwise the chooser breaks
    inside the block editor.
    """
    response = admin_client.get(_chooser_url(model))
    assert response.status_code == 200
    assert "Location" not in response
