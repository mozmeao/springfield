# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Locale, Page
from wagtail_localize.operations import translate_object

from springfield.cms.fixtures.base_fixtures import get_flare_docs_index_page, get_placeholder_images
from springfield.cms.fixtures.registry import PAGE_FIXTURES
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
