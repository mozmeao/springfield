# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from uuid import uuid4

from django.core.exceptions import ValidationError

import pytest
from wagtail.models import Locale

from springfield.cms.fixtures.block_factories import button_row
from springfield.cms.models import SyncedBlockSnippet
from springfield.cms.tests.test_synced_blocks.conftest import cards_list_item, comparison_table_item, section_item

pytestmark = [pytest.mark.django_db]


def uitour_button_row():
    return button_row(
        str(uuid4()),
        [
            {
                "type": "uitour_button",
                "value": {
                    "settings": {"theme": "", "icon": "open-tabs", "icon_position": "right", "analytics_id": str(uuid4())},
                    "button_type": "open_new_tab",
                    "pretranslated_label": None,
                    "custom_label": "Open New Tab",
                },
                "id": str(uuid4()),
            }
        ],
    )


def cards_list_with_uitour_button():
    item = cards_list_item()
    item["value"]["cards"][0]["value"]["content"][-1] = {**uitour_button_row(), "type": "buttons"}
    return item


def section_with_uitour_button():
    item = section_item()
    item["value"]["content"].append(uitour_button_row())
    return item


def build_snippet(blocks, name="Synced block"):
    return SyncedBlockSnippet(name=name, locale=Locale.get_default(), content=blocks)


def test_snippet_offers_only_comparison_table_cards_list_and_section():
    stream_block = SyncedBlockSnippet._meta.get_field("content").stream_block

    assert set(stream_block.child_blocks) == {"comparison_table", "cards_list", "section"}


@pytest.mark.parametrize(
    "make_block",
    [
        pytest.param(comparison_table_item, id="comparison_table"),
        pytest.param(cards_list_item, id="cards_list"),
        pytest.param(section_item, id="section"),
        pytest.param(cards_list_with_uitour_button, id="cards_list_with_uitour_button"),
        pytest.param(section_with_uitour_button, id="section_with_uitour_button"),
    ],
)
def test_snippet_with_one_block_is_valid(make_block):
    build_snippet([make_block()]).full_clean()


@pytest.mark.parametrize(
    "blocks, name, invalid_field",
    [
        pytest.param([], "Synced block", "content", id="no_blocks"),
        pytest.param([comparison_table_item(), section_item()], "Synced block", "content", id="two_blocks"),
        pytest.param([section_item()], "", "name", id="blank_name"),
    ],
)
def test_invalid_snippet_reports_field_error(blocks, invalid_field, name):
    with pytest.raises(ValidationError) as exc_info:
        build_snippet(blocks, name=name).full_clean()

    assert invalid_field in exc_info.value.message_dict


def test_snippet_str():
    assert str(build_snippet([section_item()], name="Enterprise support tiers")) == "Enterprise support tiers"


@pytest.mark.parametrize(
    "make_block, label",
    [
        pytest.param(comparison_table_item, "Comparison Table", id="comparison_table"),
        pytest.param(cards_list_item, "Cards List", id="cards_list"),
        pytest.param(section_item, "Section", id="section"),
    ],
)
def test_snippet_block_type(make_block, label):
    snippet = build_snippet([make_block()])
    snippet.save()

    assert SyncedBlockSnippet.objects.get(pk=snippet.pk).block_type == label
