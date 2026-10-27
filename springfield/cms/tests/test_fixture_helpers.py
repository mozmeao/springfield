# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import (
    get_flare_blocks_docs_page,
    get_flare_docs_index_page,
    get_flare_pages_docs_page,
    get_flare_snippets_docs_page,
)
from springfield.cms.fixtures.snippet_fixtures import BANNER_SNIPPET_TRANSLATION_KEY, get_banner_snippet, get_pretranslated_phrase_snippets
from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import BannerSnippet, PretranslatedPhrase
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
    """The /flare-docs/ root should host three sibling index pages: blocks, sample-pages, snippets."""
    get_flare_blocks_docs_page()
    get_flare_pages_docs_page()
    get_flare_snippets_docs_page()

    index = get_flare_docs_index_page()
    child_slugs = sorted(c.slug for c in index.get_children())
    assert child_slugs == ["blocks", "sample-pages", "snippets"]


def test_get_pretranslated_phrase_snippets_keeps_editor_content(minimal_site):
    """An existing phrase is reused as editors left it, never overwritten."""
    editor_phrase = PretranslatedPhrase.objects.create(
        translation_key=PHRASES["get_firefox"]["translation_key"],
        locale=Locale.get_default(),
        label="Get Firefox now",
        live=False,
    )

    get_firefox, _ = get_pretranslated_phrase_snippets()

    assert get_firefox.pk == editor_phrase.pk
    get_firefox.refresh_from_db()
    assert get_firefox.label == "Get Firefox now"
    assert get_firefox.live is False


def test_get_banner_snippet_keeps_editor_snippets(minimal_site):
    """The fixture snippet is looked up by its own translation key, so editor snippets stay untouched."""
    editor_snippet = BannerSnippet.objects.create(locale=Locale.get_default(), heading="<p>Editor heading</p>")

    fixture_snippet = get_banner_snippet()

    assert fixture_snippet.pk != editor_snippet.pk
    assert str(fixture_snippet.translation_key) == BANNER_SNIPPET_TRANSLATION_KEY
    editor_snippet.refresh_from_db()
    assert editor_snippet.heading == "<p>Editor heading</p>"
