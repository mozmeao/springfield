# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from io import StringIO

from django.core.management import call_command
from django.urls import reverse

import pytest
from wagtail import blocks

from springfield.cms.management.commands.find_block_instances import find_block_instances, walk_blocks
from springfield.cms.models import FreeFormPage2026

# ---------------------------------------------------------------------------
# walk_blocks(): pure recursion tests against minimal, throwaway block
# definitions (not springfield's production blocks.py) so they're independent
# of that module's structure.
# ---------------------------------------------------------------------------


class _Leaf(blocks.CharBlock):
    pass


class _Inner(blocks.StructBlock):
    leaf = _Leaf(required=False)


class _Wrapper(blocks.StructBlock):
    inner = _Inner()
    items = blocks.ListBlock(_Leaf(required=False))


class _Root(blocks.StreamBlock):
    wrapper = _Wrapper()


def test_walk_blocks_recurses_through_struct_list_and_stream_blocks():
    root_block = _Root()
    stream_value = root_block.to_python(
        [{"type": "wrapper", "value": {"inner": {"leaf": "hi"}, "items": ["a", "b"]}, "id": "w1"}],
    )

    walked = list(walk_blocks(root_block, stream_value))
    classes = [block.__class__.__name__ for block, _value in walked]

    assert classes[0] == "_Root"
    assert "_Wrapper" in classes
    assert "_Inner" in classes
    # One _Leaf from the struct field, two more from the list items.
    leaf_values = [value for block, value in walked if isinstance(block, _Leaf)]
    assert sorted(leaf_values) == ["a", "b", "hi"]


def test_walk_blocks_on_empty_containers_does_not_raise():
    root_block = _Root()
    stream_value = root_block.to_python([{"type": "wrapper", "value": {"inner": {}, "items": []}, "id": "w1"}])
    assert list(walk_blocks(root_block, stream_value))  # just shouldn't raise


# ---------------------------------------------------------------------------
# find_block_instances() / the command: exercised against real page content,
# since matching is keyed off StreamField definitions discovered via Page._meta.
# ---------------------------------------------------------------------------


def _notification_block(block_id="n1"):
    return {"type": "notification", "value": {}, "id": block_id}


def _two_column_cards_section(block_id="s1"):
    """A `section` block containing a nested `two_column_cards` block two levels down.

    TwoColumnCardsBlock (springfield/cms/blocks.py) is a factory function whose
    real class is `_TwoColumnCardsBlock` — this is what exercises the leading-
    underscore stripping in find_block_instances().
    """
    return {
        "type": "section",
        "value": {
            "settings": {},
            "heading": {},
            "content": [
                {"type": "two_column_cards", "value": {"settings": {}, "cards": []}, "id": f"{block_id}-tcc"},
            ],
            "cta": [],
        },
        "id": block_id,
    }


@pytest.fixture
def block_search_page(minimal_site):
    page = FreeFormPage2026(
        title="Block Search Test",
        slug="block-search-test",
        content=json.dumps([_notification_block(), _two_column_cards_section()]),
    )
    minimal_site.root_page.add_child(instance=page)
    page.save_revision().publish()
    return page


@pytest.mark.django_db
class TestFindBlockInstances:
    def test_matches_top_level_block_by_class_name(self, block_search_page):
        matches = find_block_instances("NotificationBlock")
        assert [page for page, _field_name, _value in matches] == [block_search_page]

    def test_matches_nested_factory_produced_block_by_public_name(self, block_search_page):
        matches = find_block_instances("TwoColumnCardsBlock")
        assert [page for page, _field_name, _value in matches] == [block_search_page]

    def test_no_match_returns_empty_list(self, block_search_page):
        assert find_block_instances("ThisBlockDoesNotExist") == []

    def test_field_name_is_recorded(self, block_search_page):
        [(_page, field_name, _value)] = find_block_instances("NotificationBlock")
        assert field_name == "content"


def _run_command(*args):
    out = StringIO()
    call_command("find_block_instances", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestFindBlockInstancesCommand:
    def test_no_matches_prints_warning(self):
        out = _run_command("ThisBlockDoesNotExist")
        assert "No instances of ThisBlockDoesNotExist found." in out

    def test_prints_table_with_page_details(self, block_search_page):
        out = _run_command("NotificationBlock")
        assert "Block Search Test" in out
        assert str(block_search_page.pk) in out
        assert "content" in out
        assert "1 instance(s) across 1 page(s)." in out

    def test_live_page_shows_frontend_url(self, block_search_page):
        out = _run_command("NotificationBlock")
        assert block_search_page.get_full_url() in out

    def test_unpublished_page_shows_draft_preview_url(self, minimal_site):
        page = FreeFormPage2026(
            title="Unpublished Block Page",
            slug="unpublished-block-page",
            content=json.dumps([_notification_block()]),
            live=False,
        )
        minimal_site.root_page.add_child(instance=page)
        page.save_revision()  # draft only — never published

        out = _run_command("NotificationBlock")

        draft_path = reverse("wagtailadmin_pages:view_draft", args=[page.pk])
        assert draft_path in out
