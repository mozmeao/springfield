# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import pytest

from springfield.cms.fixtures.line_cards_fixtures import get_line_cards_test_page
from springfield.cms.models import FreeFormPage2026


@pytest.fixture
def line_cards_searchable_content(index_page, placeholder_images):
    """Searchable content for a page whose upper_content nests section (StructBlock) >
    line_cards (StructBlock) > cards (ListBlock) > buttons (StreamBlock)."""
    page = get_line_cards_test_page()
    page = FreeFormPage2026.objects.get(pk=page.pk)
    field = FreeFormPage2026._meta.get_field("upper_content")
    return field.get_searchable_content(page.upper_content)


@pytest.mark.django_db
def test_get_searchable_content_collects_block_types_through_list_blocks(line_cards_searchable_content):
    """Block-type slugs are collected recursively at every nesting level, and the
    block text still comes through from the parent implementation."""
    assert "section" in line_cards_searchable_content
    assert "line_cards" in line_cards_searchable_content
    assert "button" in line_cards_searchable_content
    assert "Line Cards Inside a Section" in line_cards_searchable_content


@pytest.mark.django_db
def test_get_searchable_content_deduplicates_block_types(line_cards_searchable_content):
    """A block type used across many cards is collected only once."""
    assert line_cards_searchable_content.count("button") == 1
