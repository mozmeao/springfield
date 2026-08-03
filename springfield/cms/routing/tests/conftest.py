# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings

import pytest
from wagtail.models import Site

from springfield.cms.routing.models import RoutingCondition, RoutingRule
from springfield.cms.routing.signals import RoutingSignal, Source, ValueType, registry
from springfield.cms.tests.factories import LocaleFactory, WhatsNewIndexPageFactory, WhatsNewPage2026Factory

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


def _publish_translation(page, locale):
    """Copy ``page`` into ``locale`` and publish it, returning the specific instance."""
    translation = page.copy_for_translation(locale)
    translation.save()
    translation.publish(translation.save_revision())
    return translation.specific


@pytest.fixture
def translated_wnp(db):
    """A canonical + variant published in both ``en-US`` and ``de``, with a rule.

    en-US:  /whatsnew/145/  ->  /whatsnew/145/145-b/   (the rule's target)
    de:     /de/whatsnew/145/  ->  /de/whatsnew/145/145-b/

    The German canonical carries the rule Wagtail copied with it, whose stored target
    still points at the *English* variant — resolved to the German one at serve time.
    The German locale's root page is copied too, or German URLs do not route.
    """
    site = Site.objects.get(is_default_site=True)
    index = WhatsNewIndexPageFactory(parent=site.root_page, slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="145", version="145", live=True)
    variant = WhatsNewPage2026Factory(parent=canonical, slug="145-b", version="145", live=True)
    rule = RoutingRule.objects.create(page=canonical, target=variant)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)

    de = LocaleFactory(language_code="de")
    _publish_translation(site.root_page, de)
    de_index = _publish_translation(index, de)
    de_canonical = _publish_translation(canonical, de)
    de_variant = _publish_translation(variant, de)

    return SimpleNamespace(
        index=index,
        canonical=canonical,
        variant=variant,
        rule=rule,
        de=de,
        de_index=de_index,
        de_canonical=de_canonical,
        de_variant=de_variant,
    )


@pytest.fixture
def resolver_strings_english_only():
    """Make the resolver's Fluent file report the activation state production sees.

    A newly added Fluent file is active in ``en-US`` alone until translations land, and
    ``l10n_utils.render`` redirects a visitor whose locale is not in that list. Tests run
    with ``DEV=True``, where the lookup returns every language instead and the redirect
    path never runs — so a locale bug in a render path is invisible by default.

    Patching the lookup rather than overriding ``DEV``: the result is memoized in the
    Fluent cache under a key that does not include the setting, so a value cached by an
    earlier test can outlive the override.
    """
    with patch("lib.l10n_utils.fluent.get_active_locales", return_value=["en-US"]):
        yield


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
