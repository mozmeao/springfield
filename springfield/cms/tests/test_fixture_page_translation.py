# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.fields import StreamField
from wagtail.models import Locale, Page
from wagtail_localize.operations import translate_object

from springfield.base.fixtures.registry import PAGE_FIXTURES
from springfield.cms.fixtures.base_fixtures import get_flare_docs_index_page, get_placeholder_images
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet, get_scroll_to_see_more_snippet

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture
def base_fixtures():
    """The shared setup that load_page_fixtures runs before any page fixture:
    the docs index page, placeholder images, and the always-referenced snippets."""
    get_flare_docs_index_page()
    get_placeholder_images()
    get_pre_footer_cta_form_snippet()
    get_scroll_to_see_more_snippet()


def as_pages(result):
    """Normalise a fixture's return value (a page, list, or dict of pages) to a
    list of pages."""
    if isinstance(result, dict):
        return list(result.values())
    if isinstance(result, (list, tuple)):
        return list(result)
    return [result]


@pytest.mark.parametrize("fixture_func", PAGE_FIXTURES, ids=lambda func: func.__name__)
def test_fixture_page_can_be_submitted_for_translation(fixture_func, base_fixtures):
    """Every seeded fixture page must translate without a duplicate-block-id
    error. Duplicate StreamField block ids collapse wagtail-localize segment
    paths and raise "... can only have a single segment"."""
    fr_locale = Locale.objects.get_or_create(language_code="fr")[0]

    for page in as_pages(fixture_func()):
        page = Page.objects.get(pk=page.pk).specific
        translate_object(page, [fr_locale])
        assert page.get_translation(fr_locale) is not None


def iter_block_entries(data):
    """Yield every StreamField block entry (a dict carrying a ``type``) at any depth."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "type" in item:
                yield item
            yield from iter_block_entries(item)
    elif isinstance(data, dict):
        for value in data.values():
            yield from iter_block_entries(value)


def build_and_collect_block_ids(fixture_func):
    """Run a fixture and return ``{(page pk, field name): [block ids]}`` for its StreamFields."""
    block_ids = {}
    for page in as_pages(fixture_func()):
        page = Page.objects.get(pk=page.pk).specific
        for field in page._meta.get_fields():
            if not isinstance(field, StreamField):
                continue
            stream_value = getattr(page, field.name, None)
            if not stream_value:
                continue
            block_ids[(page.pk, field.name)] = [entry.get("id") for entry in iter_block_entries(list(stream_value.raw_data))]
    return block_ids


@pytest.mark.parametrize("fixture_func", PAGE_FIXTURES, ids=lambda func: func.__name__)
def test_fixture_page_block_ids_are_stable_across_rebuilds(fixture_func, base_fixtures):
    """
    Rebuilding a fixture must not change its block ids, including nested blocks

    A fixture that omits an explicit ``id`` still gets one, because Wagtail assigns a
    fresh uuid in ``get_prep_value()`` on every save, so the ids look fine on any
    single page, and silently differ the next time ``load_page_fixtures`` runs. That
    orphans the wagtail-localize segments keyed to the old id, which surfaces as
    translations vanishing from the editor, rather than as an error. Asserting the ids
    merely exist would pass for exactly the fixtures this is meant to catch."""
    first = build_and_collect_block_ids(fixture_func)
    second = build_and_collect_block_ids(fixture_func)

    assert first.keys() == second.keys(), f"{fixture_func.__name__}: rebuilding changed which pages or fields hold blocks"
    for key, first_ids in first.items():
        page_pk, field_name = key
        assert first_ids == second[key], (
            f"{fixture_func.__name__}: page pk={page_pk} field {field_name} changed block ids on rebuild — "
            'a block is missing an explicit "id" and Wagtail generated a new one'
        )
