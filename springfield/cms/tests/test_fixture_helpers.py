# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.fixtures.base_fixtures import (
    get_flare_blocks_docs_page,
    get_flare_docs_index_page,
    get_flare_pages_docs_page,
    get_flare_snippets_docs_page,
)
from springfield.cms.models.pages import FlareDocsIndexPage

pytestmark = [pytest.mark.django_db]


def test_get_flare_snippets_docs_page_creates_under_flare_docs(minimal_site):
    """get_flare_snippets_docs_page should create a 'snippets' index as a child of /flare-docs/."""
    snippets_page = get_flare_snippets_docs_page()

    assert isinstance(snippets_page, FlareDocsIndexPage)
    assert snippets_page.slug == "snippets"
    assert snippets_page.title == "Flare Docs - Snippets"

    # Parent should be the root /flare-docs/ index page
    parent = snippets_page.get_parent().specific
    assert isinstance(parent, FlareDocsIndexPage)
    assert parent.slug == "flare-docs"


def test_get_flare_snippets_docs_page_is_idempotent(minimal_site):
    """Calling the helper twice should return the same page, not duplicate it."""
    first = get_flare_snippets_docs_page()
    second = get_flare_snippets_docs_page()

    assert first.pk == second.pk
    assert FlareDocsIndexPage.objects.filter(slug="snippets").count() == 1


def test_flare_docs_index_has_three_sections(minimal_site):
    """The /flare-docs/ root should host three sibling index pages: blocks, pages, snippets."""
    get_flare_blocks_docs_page()
    get_flare_pages_docs_page()
    get_flare_snippets_docs_page()

    index = get_flare_docs_index_page()
    child_slugs = sorted(c.slug for c in index.get_children())
    assert child_slugs == ["blocks", "pages", "snippets"]
