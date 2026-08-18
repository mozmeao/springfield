# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
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


def _english_wnp_with_rule():
    """An ``en-US`` canonical + nested variant, with a rule targeting the variant."""
    site = Site.objects.get(is_default_site=True)
    index = WhatsNewIndexPageFactory(parent=site.root_page, slug="whatsnew")
    canonical = WhatsNewPage2026Factory(parent=index, slug="145", version="145", live=True)
    variant = WhatsNewPage2026Factory(parent=canonical, slug="145-b", version="145", live=True)
    rule = RoutingRule.objects.create(page=canonical, target=variant)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)
    return SimpleNamespace(site=site, index=index, canonical=canonical, variant=variant, rule=rule)


def _publish_tree_in(tree, language_code):
    """Publish a whole ``_english_wnp_with_rule`` tree in another locale.

    The locale's root page is copied too, or its URLs do not route at all.
    """
    locale = LocaleFactory(language_code=language_code)
    _publish_translation(tree.site.root_page, locale)
    return SimpleNamespace(
        locale=locale,
        index=_publish_translation(tree.index, locale),
        canonical=_publish_translation(tree.canonical, locale),
        variant=_publish_translation(tree.variant, locale),
    )


@pytest.fixture
def translated_wnp(db):
    """A canonical + variant published in both ``en-US`` and ``de``, with a rule.

    en-US:  /whatsnew/145/  ->  /whatsnew/145/145-b/   (the rule's target)
    de:     /de/whatsnew/145/  ->  /de/whatsnew/145/145-b/

    The German canonical carries the rule Wagtail copied with it, whose stored target
    still points at the *English* variant — resolved to the German one at serve time.
    """
    tree = _english_wnp_with_rule()
    de = _publish_tree_in(tree, "de")
    return SimpleNamespace(
        index=tree.index,
        canonical=tree.canonical,
        variant=tree.variant,
        rule=tree.rule,
        de=de.locale,
        de_index=de.index,
        de_canonical=de.canonical,
        de_variant=de.variant,
    )


@pytest.fixture
def fallback_locale_wnp(db):
    """A tree published in ``es-MX``, plus an ``es-AR`` locale that has no pages of its own.

    ``settings.FALLBACK_LOCALES`` maps es-AR to es-MX, so a visitor asking for
    ``/es-AR/whatsnew/145/`` is served the **es-MX** page at the **es-AR** URL. The alias
    locale needs a live root page for that fallback to happen at all, and nothing below it.

    Returns the served (es-MX) pages plus the es-AR URL the visitor actually requests.
    """
    tree = _english_wnp_with_rule()
    es_mx = _publish_tree_in(tree, "es-MX")

    alias_locale = LocaleFactory(language_code="es-AR")
    alias_root = tree.site.root_page.copy_for_translation(alias_locale)
    alias_root.save_revision().publish()

    return SimpleNamespace(
        locale=es_mx.locale,
        canonical=es_mx.canonical,
        variant=es_mx.variant,
        alias_locale=alias_locale,
        alias_url=es_mx.canonical.get_url().replace("/es-MX/", "/es-AR/", 1),
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


@pytest.fixture
def restricted_client(client, db):
    """A logged-in staff client with admin access but no page permissions yet.

    A test grants ``GroupPagePermission`` on ``.group`` for whichever pages it wants
    visible, then everything else stays invisible — proving the listing is actually
    scoped rather than open to any staff user.
    """
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        user = User.objects.create_user(username="restricted-editor", email="restricted@example.com", password="pass", is_staff=True)
        group = Group.objects.create(name="Restricted editors")
        group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
        user.groups.add(group)
        client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        yield SimpleNamespace(client=client, group=group)
