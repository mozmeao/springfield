# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from importlib import import_module
from unittest import mock

from django.conf import settings
from django.test import override_settings

import pytest
from wagtail.models import Locale, Page, Site
from wagtail_localize.views.submit_translations import SubmitTranslationForm

from springfield.cms.tests.factories import LocaleFactory
from springfield.cms.utils import get_locales_for_cms_page
from springfield.settings.base import lazy_wagtail_langs

pytestmark = [pytest.mark.django_db]

PAGE_PATH = "/test-page/child-page/"


def _build_welsh_tree(live_child=True):
    """Give the site a Welsh page tree: a live locale root plus a child page.

    The locale root has to be live or Wagtail resolves /cy/ against the en-US tree.
    """
    site = Site.objects.get(is_default_site=True)
    en_us_root_page = site.root_page
    en_us_child = Page.objects.get(locale__language_code="en-US", slug="child-page")

    welsh_locale = LocaleFactory(language_code="cy")

    welsh_root_page = en_us_root_page.copy_for_translation(welsh_locale)
    welsh_root_page.live = True
    welsh_root_page.save()

    en_us_test_page = en_us_root_page.get_children()[0]
    welsh_test_page = en_us_test_page.copy_for_translation(welsh_locale)
    welsh_test_page.live = True
    welsh_test_page.save()
    welsh_test_page.save_revision().publish()

    welsh_child = en_us_child.copy_for_translation(welsh_locale)
    welsh_child.live = live_child
    welsh_child.save()
    if live_child:
        welsh_child.save_revision().publish()

    return en_us_child, welsh_child


@override_settings(FALLBACK_LOCALES={})
def test_welsh_page_is_served_at_its_own_url(client, tiny_localized_site):
    """Welsh is a real locale, so its pages are served directly and indexed as their own."""
    _, welsh_child = _build_welsh_tree()

    response = client.get(f"/cy{PAGE_PATH}")

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert welsh_child.title in html
    assert f'rel="canonical" href="{settings.CANONICAL_URL}/cy{PAGE_PATH}"' in html
    assert '<meta name="robots" content="noindex,follow">' not in html
    # Nothing should be treated as fallback content — that is what alias locales do.
    assert not getattr(response.wsgi_request, "content_locale", None)


@override_settings(FALLBACK_LOCALES={})
def test_welsh_listed_as_hreflang_alternate_on_english_page(client, tiny_localized_site):
    en_us_child, _ = _build_welsh_tree()

    response = client.get(en_us_child.url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert f'hreflang="cy" href="{settings.CANONICAL_URL}/cy{PAGE_PATH}"' in html


@override_settings(FALLBACK_LOCALES={})
def test_unpublishing_welsh_page_withdraws_the_locale(client, tiny_localized_site):
    """Unpublishing is how Welsh gets withdrawn: no locale option, and /cy/ redirects away."""
    en_us_child, welsh_child = _build_welsh_tree(live_child=False)

    assert "cy" not in get_locales_for_cms_page(en_us_child)

    response = client.get(en_us_child.url)
    assert 'hreflang="cy"' not in response.content.decode("utf-8")

    response = client.get(f"/cy{PAGE_PATH}")
    assert response.status_code == 302
    assert response.url == en_us_child.url


def test_welsh_is_an_enabled_cms_locale():
    assert ("cy", "Welsh") in lazy_wagtail_langs()


def test_welsh_is_excluded_from_smartling():
    excluded = settings.WAGTAIL_LOCALIZE_SMARTLING["EXCLUDE_LOCALES"]
    assert "cy" in excluded
    # Alias locales serve another locale's content, so they must stay excluded too.
    assert set(settings.FALLBACK_LOCALES).issubset(set(excluded))


def test_welsh_is_not_a_fallback_locale():
    assert "cy" not in settings.FALLBACK_LOCALES


def test_translate_form_offers_welsh_last(tiny_localized_site):
    """Welsh sorts first by language_code, so the form has to push it to the end.

    Every other locale keeps Wagtail's language_code ordering.
    """
    LocaleFactory(language_code="cy")
    # Two others, so the secondary language_code ordering is actually exercised.
    LocaleFactory(language_code="de")
    LocaleFactory(language_code="it")
    root_page = Site.objects.get(is_default_site=True).root_page

    form = SubmitTranslationForm(root_page)
    offered = [locale.language_code for locale in form.fields["locales"].queryset]

    assert offered[-1] == "cy"
    others = offered[:-1]
    assert len(others) > 1
    assert others == sorted(others)


@pytest.fixture
def welsh_migration():
    """The 0153 migration module, with its environment guard disabled.

    The guard makes both functions no-ops under pytest, so tests patch it off to
    exercise the real behaviour. The module name starts with a digit, so it has to
    be imported by string.
    """
    module = import_module("springfield.cms.migrations.0153_create_welsh_locale")
    with mock.patch.object(module, "_should_skip", return_value=False):
        yield module


def test_migration_creates_a_live_welsh_homepage_alias(welsh_migration, prod_shape_site):
    """Exercised against the production tree shape, where Site.root_page is at depth 3.

    The `copy_parents=True` branch that builds the per-locale root only runs there.
    """
    welsh_migration.create_welsh_locale(None, None)

    welsh_locale = Locale.objects.get(language_code="cy")
    welsh_homepage = prod_shape_site["homepage"].get_translation(welsh_locale)

    assert welsh_homepage.live is True
    assert welsh_homepage.alias_of_id == prod_shape_site["homepage"].id
    # Its parent is the per-locale root, created alongside the other locale roots.
    assert welsh_homepage.get_parent().depth == 2


def test_migration_is_idempotent(welsh_migration, prod_shape_site):
    welsh_migration.create_welsh_locale(None, None)
    welsh_migration.create_welsh_locale(None, None)

    welsh_locale = Locale.objects.get(language_code="cy")
    assert Page.objects.filter(locale=welsh_locale, depth=3).count() == 1


def test_reverse_migration_removes_an_untouched_alias(welsh_migration, prod_shape_site):
    welsh_migration.create_welsh_locale(None, None)

    welsh_migration.remove_welsh_locale(None, None)

    assert not Locale.objects.filter(language_code="cy").exists()


def test_reverse_migration_keeps_a_promoted_welsh_homepage(welsh_migration, prod_shape_site):
    """Clearing `alias_of` is how wagtail-localize promotes the alias to a translation.

    That page holds Welsh content, so a rollback must leave it alone.
    """
    welsh_migration.create_welsh_locale(None, None)
    welsh_locale = Locale.objects.get(language_code="cy")
    welsh_homepage = prod_shape_site["homepage"].get_translation(welsh_locale)
    welsh_homepage.alias_of_id = None
    welsh_homepage.title = "Hafan Firefox"
    welsh_homepage.save()

    welsh_migration.remove_welsh_locale(None, None)

    welsh_homepage.refresh_from_db()
    assert welsh_homepage.title == "Hafan Firefox"
    assert Locale.objects.filter(language_code="cy").exists()
