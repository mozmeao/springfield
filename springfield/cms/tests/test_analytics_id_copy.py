# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse

import pytest

from springfield.cms.blocks import regenerate_analytics_ids
from springfield.cms.fixtures.button_fixtures import get_button_blocks, get_buttons_test_page
from springfield.cms.fixtures.smart_window_page_fixtures import get_smart_window_test_page
from springfield.cms.models import FreeFormPage2026, SimpleRichTextPage, SmartWindowPage
from springfield.cms.tests.factories import LocaleFactory

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


def copy_via_admin(admin_client, page, **extra):
    """POST the Wagtail copy form for ``page`` and return the response."""
    data = {
        "new_title": "Buttons Copy",
        "new_slug": "buttons-copy",
        "new_parent_page": page.get_parent().id,
        "publish_copies": "on",
        **extra,
    }
    return admin_client.post(reverse("wagtailadmin_pages:copy", args=[page.id]), data)


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


def test_admin_copy_regenerates_analytics_ids_by_default(admin_client):
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())
    assert len(original_ids) > 1

    response = copy_via_admin(admin_client, page)
    assert response.status_code == 302

    copied = FreeFormPage2026.objects.get(slug="buttons-copy")
    copied_ids = collect_analytics_ids(copied.content.get_prep_value())

    assert len(copied_ids) == len(original_ids)
    assert set(copied_ids).isdisjoint(original_ids)
    assert len(set(copied_ids)) == len(copied_ids)


def test_admin_copy_keeps_analytics_ids_when_checkbox_checked(admin_client):
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())

    response = copy_via_admin(admin_client, page, keep_analytics_ids="on")
    assert response.status_code == 302

    copied = FreeFormPage2026.objects.get(slug="buttons-copy")
    copied_ids = collect_analytics_ids(copied.content.get_prep_value())

    # Opt-out: the copy keeps the source page's analytics IDs exactly.
    assert copied_ids == original_ids


def test_admin_copy_regenerates_analytics_ids_across_subpages(admin_client):
    parent_page = get_buttons_test_page()
    child_page = FreeFormPage2026(slug="child-buttons", title="Child Buttons", content=get_button_blocks())
    parent_page.add_child(instance=child_page)
    child_page.save_revision().publish()
    original_child_ids = collect_analytics_ids(child_page.content.get_prep_value())
    assert len(original_child_ids) > 1

    response = copy_via_admin(admin_client, parent_page, copy_subpages="on")
    assert response.status_code == 302

    copied_parent = FreeFormPage2026.objects.get(slug="buttons-copy")
    copied_child = FreeFormPage2026.objects.get(slug="child-buttons", path__startswith=copied_parent.path)
    copied_child_ids = collect_analytics_ids(copied_child.content.get_prep_value())

    # Subpages copied recursively also get fresh analytics IDs.
    assert len(copied_child_ids) == len(original_child_ids)
    assert set(copied_child_ids).isdisjoint(original_child_ids)


def test_admin_copy_as_alias_preserves_analytics_ids(admin_client):
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())

    response = copy_via_admin(admin_client, page, alias="on")
    assert response.status_code == 302

    alias = FreeFormPage2026.objects.get(slug="buttons-copy")
    assert alias.alias_of_id == page.id
    # Aliases must mirror their original exactly, including analytics IDs.
    assert collect_analytics_ids(alias.content.get_prep_value()) == original_ids


def test_copy_for_translation_preserves_analytics_ids():
    fr_locale = LocaleFactory(language_code="fr")
    page = get_buttons_test_page()
    original_ids = collect_analytics_ids(page.content.get_prep_value())
    assert len(original_ids) > 1

    translated = page.copy_for_translation(fr_locale, copy_parents=True)
    translated_ids = collect_analytics_ids(translated.content.get_prep_value())

    # A translation keeps the source page's analytics IDs, in the same order.
    assert translated_ids == original_ids


def test_copy_form_renders_keep_analytics_ids_checkbox(admin_client):
    page = get_buttons_test_page()

    response = admin_client.get(reverse("wagtailadmin_pages:copy", args=[page.id]))

    assert response.status_code == 200
    assert b"keep_analytics_ids" in response.content


SMART_WINDOW_UID_FIELDS = [
    "nav_button_uid",
    "intro_button_uid",
    "waitlist_submit_uid",
    "nav_download_button_uid",
    "intro_download_button_uid",
    "update_button_uid",
]


def collect_uids(page):
    return {name: getattr(page, name) for name in SMART_WINDOW_UID_FIELDS}


def test_admin_copy_regenerates_uuid_fields_held_on_the_model(admin_client, placeholder_images):
    """SmartWindowPage keeps its analytics IDs in model fields rather than StreamField
    blocks, so copying must regenerate those too."""
    assert SmartWindowPage.analytics_id_fields == SMART_WINDOW_UID_FIELDS

    page = get_smart_window_test_page()
    original_uids = collect_uids(page)

    response = copy_via_admin(admin_client, page, new_title="Smart Window Copy", new_slug="smart-window-copy")
    assert response.status_code == 302

    copied = SmartWindowPage.objects.get(slug="smart-window-copy")
    copied_uids = collect_uids(copied)

    assert set(copied_uids.values()).isdisjoint(original_uids.values())
    assert len(set(copied_uids.values())) == len(SMART_WINDOW_UID_FIELDS)


def test_admin_copy_keeps_uuid_fields_when_checkbox_checked(admin_client, placeholder_images):
    page = get_smart_window_test_page()
    original_uids = collect_uids(page)

    response = copy_via_admin(admin_client, page, new_title="Smart Window Copy", new_slug="smart-window-copy", keep_analytics_ids="on")
    assert response.status_code == 302

    copied = SmartWindowPage.objects.get(slug="smart-window-copy")
    assert collect_uids(copied) == original_uids


def test_admin_copy_leaves_pages_with_no_analytics_ids_untouched(admin_client):
    """A page with neither StreamFields nor analytics_id_fields has nothing to regenerate,
    so the hook must skip it instead of saving and publishing a redundant revision."""
    parent_page = get_buttons_test_page()
    plain_page = SimpleRichTextPage(slug="plain-child", title="Plain Child")
    parent_page.add_child(instance=plain_page)
    plain_page.save_revision().publish()

    response = copy_via_admin(admin_client, parent_page, copy_subpages="on")
    assert response.status_code == 302

    copied_parent = FreeFormPage2026.objects.get(slug="buttons-copy")
    copied_plain = SimpleRichTextPage.objects.get(slug="plain-child", path__startswith=copied_parent.path)

    # The parent has StreamFields, so the hook saves it an extra revision; the plain
    # child has nothing to regenerate and must not pick one up.
    assert copied_plain.revisions.count() < copied_parent.revisions.count()
