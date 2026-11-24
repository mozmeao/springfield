# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Covers the backfill in the 0169 migration, which carries the old marketing attribution checkbox
# into the three-way setting. The editor loads a page's latest revision, so a revision
# the migration misses opens as "Disabled" and switches attribution off on the next publish.

from importlib import import_module

from django.apps import apps

import pytest
from wagtail.models import Site

from springfield.cms.models import FreeFormPage2026
from springfield.cms.models.base import MarketingAttributionMode
from springfield.cms.tests.factories import FreeFormPage2026Factory

pytestmark = [pytest.mark.django_db]

migration = import_module("springfield.cms.migrations.0169_freeformpage2026_marketing_attribution_mode_and_more")


def store_pre_migration_page(page, *, enabled):
    """Write the page and a revision the way code from before the new field did: only the old checkbox."""
    revision = page.save_revision(clean=False)
    revision.content["enable_marketing_attribution"] = enabled
    del revision.content["marketing_attribution_mode"]
    revision.save(update_fields=["content"])
    FreeFormPage2026.objects.filter(pk=page.pk).update(enable_marketing_attribution=enabled, marketing_attribution_mode="")
    return revision


@pytest.fixture
def landing_page():
    return FreeFormPage2026Factory(parent=Site.objects.get(is_default_site=True).root_page)


def test_migration_turns_the_checkbox_into_always_promoted(landing_page):
    revision = store_pre_migration_page(landing_page, enabled=True)

    migration.copy_enabled_flag_to_mode(apps)

    landing_page.refresh_from_db()
    revision.refresh_from_db()
    assert landing_page.marketing_attribution_mode == MarketingAttributionMode.ALWAYS
    assert revision.content["marketing_attribution_mode"] == MarketingAttributionMode.ALWAYS
    assert landing_page.get_latest_revision_as_object().marketing_attribution_mode == MarketingAttributionMode.ALWAYS


def test_migration_leaves_unchecked_pages_disabled(landing_page):
    revision = store_pre_migration_page(landing_page, enabled=False)

    migration.copy_enabled_flag_to_mode(apps)

    landing_page.refresh_from_db()
    revision.refresh_from_db()
    assert landing_page.marketing_attribution_mode == MarketingAttributionMode.DISABLED
    assert "marketing_attribution_mode" not in revision.content


def test_migration_keeps_a_mode_already_chosen(landing_page):
    revision = store_pre_migration_page(landing_page, enabled=True)
    revision.content["marketing_attribution_mode"] = MarketingAttributionMode.URL_PARAM
    revision.save(update_fields=["content"])
    FreeFormPage2026.objects.filter(pk=landing_page.pk).update(marketing_attribution_mode=MarketingAttributionMode.URL_PARAM)

    migration.copy_enabled_flag_to_mode(apps)

    landing_page.refresh_from_db()
    revision.refresh_from_db()
    assert landing_page.marketing_attribution_mode == MarketingAttributionMode.URL_PARAM
    assert revision.content["marketing_attribution_mode"] == MarketingAttributionMode.URL_PARAM
