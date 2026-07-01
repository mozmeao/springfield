# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.blocks import regenerate_analytics_ids
from springfield.cms.fixtures.button_fixtures import get_buttons_test_page
from springfield.cms.tests.factories import LocaleFactory, SimpleRichTextPageFactory

pytestmark = [
    pytest.mark.django_db,
]


def collect_analytics_ids(data):
    """Recursively collect every value stored under an analytics-id key in a
    StreamField's prepared (JSON-serialisable) representation."""
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "analytics_id" or key.endswith("_analytics_id"):
                found.append(value)
            else:
                found.extend(collect_analytics_ids(value))
    elif isinstance(data, list):
        for item in data:
            found.extend(collect_analytics_ids(item))
    return found


def test_regenerate_analytics_ids_replaces_every_id_and_preserves_structure():
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())
    # Sanity check: the fixture actually contains analytics IDs to regenerate.
    assert len(original_ids) > 1

    regenerated_value = regenerate_analytics_ids(page.content)
    new_ids = collect_analytics_ids(regenerated_value.get_prep_value())

    # Same number of analytics-id fields — structure is preserved, not dropped.
    assert len(new_ids) == len(original_ids)
    # None of the original IDs survive — every one was regenerated.
    assert set(new_ids).isdisjoint(original_ids)
    # Every regenerated ID is unique, even where the source repeated an ID.
    assert len(set(new_ids)) == len(new_ids)
    # The original value is left untouched (regeneration returns a new value).
    assert collect_analytics_ids(page.content.get_prep_value()) == original_ids


def test_copy_regenerates_analytics_ids_across_all_streamfields():
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value()) + collect_analytics_ids(page.upper_content.get_prep_value())
    assert len(original_ids) > 1

    copied = page.copy(update_attrs={"slug": "test-buttons-copy", "title": "Buttons Copy"})
    copied.refresh_from_db()
    copied_ids = collect_analytics_ids(copied.content.get_prep_value()) + collect_analytics_ids(copied.upper_content.get_prep_value())

    # Every StreamField's analytics IDs are regenerated, none shared with the source.
    assert len(copied_ids) == len(original_ids)
    assert set(copied_ids).isdisjoint(original_ids)
    # The source page keeps its original IDs.
    source_ids = collect_analytics_ids(page.content.get_prep_value()) + collect_analytics_ids(page.upper_content.get_prep_value())
    assert source_ids == original_ids


def test_copy_for_translation_preserves_analytics_ids():
    fr_locale = LocaleFactory(language_code="fr")
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())
    assert len(original_ids) > 1

    translated = page.copy_for_translation(fr_locale, copy_parents=True)
    translated_ids = collect_analytics_ids(translated.content.get_prep_value())

    # A translation keeps the source page's analytics IDs, in the same order.
    assert translated_ids == original_ids


def test_copy_page_without_analytics_ids_succeeds(minimal_site):
    """A page whose StreamFields contain no analytics IDs copies without error."""
    page = SimpleRichTextPageFactory(slug="no-analytics", title="No Analytics", parent=minimal_site.root_page)

    copied = page.copy(update_attrs={"slug": "no-analytics-copy", "title": "No Analytics Copy"})

    assert copied.pk != page.pk
    assert copied.slug == "no-analytics-copy"
