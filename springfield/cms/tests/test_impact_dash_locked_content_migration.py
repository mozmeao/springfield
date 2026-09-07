# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Covers the 0145 data migration, which renames ImpactDashBlock's locked_summary
# to locked_content. Wagtail silently falls back to the field default for a key
# the stored JSON does not have, so a rename that misses a page or a draft loses
# the editor's copy with nothing to show it happened.

import json
from collections.abc import MutableSequence
from importlib import import_module

from django.apps import apps

import pytest
from wagtail.models import Site

from springfield.cms.models.pages import ReferralHubPage
from springfield.cms.tests.factories import ReferralGetFirefoxPageFactory, ReferralHubPageFactory

pytestmark = [pytest.mark.django_db]

migration = import_module("springfield.cms.migrations.0145_impact_dash_locked_content")

LOCKED_MESSAGE = "Invite your first friend."


def _showcase_with_dash(locked_key="locked_summary"):
    """Serialised StreamField JSON holding one impact dashboard.

    Built through the real blocks so the nesting stays honest -- a dashboard sits
    under showcase > media > tabs > tab, which is easy to get wrong by hand. The
    key is then renamed in the serialised JSON, as the point of the fixture is
    data carrying a key the current block definition no longer declares.
    """
    stream_block = ReferralHubPage._meta.get_field("upper_content").stream_block
    dashboard = {
        "type": "impact_dash",
        "value": {
            "locked_heading": "Nobody yet",
            "locked_content": LOCKED_MESSAGE,
            "badges": [{"number": 1, "badge_name": "Connector", "heading": "One down", "message": "first friend"}],
        },
    }
    tabs = {"type": "tabs", "value": {"section_id": "hub", "tabs": [{"tab_name": "Your impact", "impact_dash": [dashboard]}]}}
    prepped = stream_block.get_prep_value(stream_block.to_python([{"type": "showcase", "value": {"media": [tabs]}}]))

    return json.dumps(prepped).replace('"locked_content":', f'"{locked_key}":')


def _store_dash(page, field_name, locked_key="locked_summary"):
    """Write the dashboard JSON straight to the column, skipping normalisation.

    Assigning to the field and saving would run the data back through the current
    block definitions, which drop a key those definitions no longer declare --
    the very loss this migration exists to prevent. A pre-migration row has to be
    written the way the pre-rename code wrote it.
    """
    type(page).objects.filter(pk=page.pk).update(**{field_name: _showcase_with_dash(locked_key)})


def _find_dash(data):
    """The first impact_dash block's value anywhere in a raw StreamField tree.

    Searched rather than indexed, as Wagtail stores a ListBlock's items either
    bare or wrapped in {type, value, id} depending on when the page was written,
    so the path down to a dashboard is not one fixed shape. MutableSequence
    rather than list, as a StreamField hands back its raw data as a RawDataView.
    """
    if isinstance(data, dict):
        if data.get("type") == "impact_dash":
            return data["value"]
        children = data.values()
    elif isinstance(data, (list, MutableSequence)):
        children = data
    else:
        return None

    for child in children:
        found = _find_dash(child)
        if found is not None:
            return found
    return None


def _read_stored_dash(page, field_name):
    """The impact dashboard's raw value as it sits in the database."""
    page.refresh_from_db()

    return _find_dash(getattr(page, field_name).raw_data)


@pytest.fixture
def hub_page():
    return ReferralHubPageFactory(parent=Site.objects.get(is_default_site=True).root_page)


def test_migration_renames_the_locked_key_on_a_live_page(hub_page):
    _store_dash(hub_page, "upper_content")

    migration.forwards(apps, None)

    stored = _read_stored_dash(hub_page, "upper_content")
    assert stored["locked_content"] == LOCKED_MESSAGE
    assert "locked_summary" not in stored
    # The rename must not disturb the rest of the dashboard.
    assert stored["locked_heading"] == "Nobody yet"
    assert stored["badges"][0]["message"] == "first friend"


def test_migration_covers_every_field_an_impact_dash_can_live_in(hub_page):
    _store_dash(hub_page, "upper_content")
    _store_dash(hub_page, "extra_content")
    get_firefox_page = ReferralGetFirefoxPageFactory(parent=Site.objects.get(is_default_site=True).root_page)
    _store_dash(get_firefox_page, "upper_content")

    migration.forwards(apps, None)

    assert _read_stored_dash(hub_page, "upper_content")["locked_content"] == LOCKED_MESSAGE
    assert _read_stored_dash(hub_page, "extra_content")["locked_content"] == LOCKED_MESSAGE
    assert _read_stored_dash(get_firefox_page, "upper_content")["locked_content"] == LOCKED_MESSAGE


def test_migration_renames_the_locked_key_in_an_unpublished_draft(hub_page):
    """A draft left on the old key would put the copy back the next time it saved."""
    revision = hub_page.save_revision()
    revision.content["upper_content"] = _showcase_with_dash()
    revision.save(update_fields=["content"])

    migration.forwards(apps, None)

    revision.refresh_from_db()
    stored = _find_dash(json.loads(revision.content["upper_content"]))
    assert stored["locked_content"] == LOCKED_MESSAGE
    assert "locked_summary" not in stored


def test_migration_reverses_the_rename(hub_page):
    _store_dash(hub_page, "upper_content", locked_key="locked_content")

    migration.backwards(apps, None)

    stored = _read_stored_dash(hub_page, "upper_content")
    assert stored["locked_summary"] == LOCKED_MESSAGE
    assert "locked_content" not in stored


def test_migration_leaves_a_page_without_an_impact_dash_alone(hub_page):
    hub_page.upper_content = []
    hub_page.save()

    migration.forwards(apps, None)

    hub_page.refresh_from_db()
    assert list(hub_page.upper_content.raw_data) == []
