# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from itertools import count
from uuid import uuid4

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale

from springfield.cms.fixtures.base_fixtures import with_fresh_ids
from springfield.cms.fixtures.block_factories import (
    button_row,
    card,
    card_content,
    card_settings,
    cards_list,
    download_button,
    heading_block,
    rich_text,
    section,
)
from springfield.cms.fixtures.comparison_table_fixtures import get_comparison_table_variants
from springfield.cms.models import FreeFormPage2026, SyncedBlockSnippet


def synced_block_item(snippet):
    """The stream item that places ``snippet`` as a synced block on a FreeFormPage2026."""
    return {"type": "synced_block", "value": snippet.pk, "id": str(uuid4())}


def synced_in_content_only(snippet):
    return {"content": [synced_block_item(snippet)]}


def synced_in_split_page_upper(snippet):
    return {"upper_content": [synced_block_item(snippet)], "content": [section_item("Lower")]}


def synced_in_split_page_lower(snippet):
    return {"upper_content": [section_item("Upper")], "content": [synced_block_item(snippet)]}


def collapse_whitespace(html):
    return " ".join(str(html).split())


def main_content_html(response):
    """The page's main content as HTML with whitespace collapsed, so two renders can be compared."""
    soup = BeautifulSoup(response.content, "html.parser")
    return collapse_whitespace(soup.find("div", class_="fl-main"))


def comparison_table_item():
    return with_fresh_ids(get_comparison_table_variants()[0])


def cards_list_item(button_analytics_id="cards-button-analytics-id", heading_text="Card heading", show_default_browser_checkbox=False):
    """A cards list holding one card with a heading and a download button."""
    download = download_button(str(uuid4()), "Download", button_analytics_id)
    download["value"]["settings"]["show_default_browser_checkbox"] = show_default_browser_checkbox
    return cards_list(
        str(uuid4()),
        cards=[
            card(
                str(uuid4()),
                card_settings(),
                [
                    heading_block(str(uuid4()), heading_text),
                    card_content(str(uuid4()), "Card body"),
                    {**button_row(str(uuid4()), [download]), "type": "buttons"},
                ],
            )
        ],
    )


def section_item(heading_text="Section heading", anchor_id="", show_to=None):
    item = section(str(uuid4()), heading_text, content_blocks=[rich_text(str(uuid4()), '<p data-block-key="sectbody">Section body</p>')])
    item["value"]["settings"]["anchor_id"] = anchor_id
    if show_to:
        item["value"]["settings"]["show_to"] = show_to
    return item


def get_locale(language_code):
    locale, _ = Locale.objects.get_or_create(language_code=language_code)
    return locale


@pytest.fixture
def serve_page(client):

    def serve(page):
        return client.get(page.url)

    return serve


@pytest.fixture
def synced_block_factory():
    """Return a function that saves a SyncedBlockSnippet holding ``block`` (a stream item),
    publishing it unless ``publish`` is false."""

    def create_synced_block(block, *, name="Synced block", locale=None, publish=True):
        snippet = SyncedBlockSnippet(name=name, locale=locale or Locale.get_default(), content=[block], live=False)
        snippet.save()
        if publish:
            snippet.save_revision().publish()
            snippet.refresh_from_db()
        return snippet

    return create_synced_block


@pytest.fixture
def synced_block_translation_factory():
    """Return a function that translates ``snippet`` into ``locale`` holding ``block``,
    publishing the translation unless ``publish`` is false."""

    def create_translation(snippet, locale, block, *, publish=True):
        translation = snippet.copy_for_translation(locale)
        translation.content = [block]
        # The copy keeps the source's live flag; a translation starts unpublished, as in the admin.
        translation.live = False
        translation.save()
        if publish:
            translation.save_revision().publish()
            translation.refresh_from_db()
        return translation

    return create_translation


@pytest.fixture
def freeform_page_factory(index_page):
    """Return a function that creates a FreeFormPage2026 under ``index_page``.

    With a non-default ``locale``, the English page is created first and the returned page is its
    translation into ``locale``, holding the given content.
    """
    slugs = count(1)

    def create_page(*, content=None, upper_content=None, locale=None, publish=True):
        slug = f"synced-block-page-{next(slugs)}"
        page = FreeFormPage2026(title=slug, slug=slug, content=content or [], upper_content=upper_content or [])
        index_page.add_child(instance=page)
        if locale and locale != page.locale:
            page.save_revision().publish()
            page = page.copy_for_translation(locale, copy_parents=True)
            page.content = content or []
            page.upper_content = upper_content or []
            page.save()
        if publish:
            page.save_revision().publish()
            page.refresh_from_db()
        return page

    return create_page
