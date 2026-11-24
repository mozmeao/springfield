# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import reverse
from django.utils import translation

import pytest
from bs4 import BeautifulSoup

from springfield.cms.models import SyncedBlockSnippet
from springfield.cms.tests.test_synced_blocks.conftest import (
    cards_list_item,
    collapse_whitespace,
    comparison_table_item,
    get_locale,
    section_item,
    synced_block_item,
)

pytestmark = [pytest.mark.django_db]

LISTING_URL_NAME = "wagtailsnippets_cms_syncedblocksnippet:list"


def listing_row(response, snippet_name):
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.find(lambda tag: tag.name == "tr" and snippet_name in tag.get_text())


def keep_published(snippet):
    return snippet


def unpublish(snippet):
    snippet.unpublish()
    return snippet


def save_draft_edit(snippet):
    snippet.content = [comparison_table_item()]
    snippet.save_revision()
    return snippet


def test_snippets_menu_lists_synced_blocks(admin_client):
    response = admin_client.get(reverse("wagtailsnippets:index"))

    assert response.status_code == 200
    assert "Synced blocks" in response.content.decode()


@pytest.mark.parametrize(
    "change_state, expected_status",
    [
        pytest.param(keep_published, "live", id="live"),
        pytest.param(unpublish, "draft", id="draft"),
        pytest.param(save_draft_edit, "live + draft", id="live_with_draft"),
    ],
)
def test_listing_shows_name_block_type_locale_and_status(admin_client, change_state, expected_status, synced_block_factory):
    snippet = change_state(synced_block_factory(comparison_table_item(), name="Enterprise support tiers"))

    response = admin_client.get(reverse(LISTING_URL_NAME), follow=True)

    assert response.status_code == 200
    row_text = collapse_whitespace(listing_row(response, "Enterprise support tiers").get_text(" ")).lower()
    assert "comparison table" in row_text
    assert snippet.locale.get_display_name().lower() in row_text
    assert expected_status in row_text


def used_on_two_pages(freeform_page_factory, snippet):
    freeform_page_factory(content=[synced_block_item(snippet)])
    freeform_page_factory(content=[synced_block_item(snippet)])


def used_twice_on_one_page(freeform_page_factory, snippet):
    freeform_page_factory(content=[synced_block_item(snippet), synced_block_item(snippet)])


@pytest.mark.parametrize(
    "place_snippet, expected_usage",
    [
        pytest.param(used_on_two_pages, "Used 2 times", id="two_pages"),
        pytest.param(used_twice_on_one_page, "Used 1 time", id="twice_on_one_page"),
    ],
)
def test_listing_usage_count_counts_pages(admin_client, expected_usage, freeform_page_factory, place_snippet, synced_block_factory):
    snippet = synced_block_factory(section_item(), name="Shared section")
    place_snippet(freeform_page_factory, snippet)

    response = admin_client.get(reverse(LISTING_URL_NAME), follow=True)

    usage_link = listing_row(response, "Shared section").find("a", string=lambda text: text and expected_usage in collapse_whitespace(text))
    assert usage_link["href"] == reverse("wagtailsnippets_cms_syncedblocksnippet:usage", args=[snippet.pk])


@pytest.mark.parametrize(
    "make_block",
    [
        pytest.param(comparison_table_item, id="comparison_table"),
        pytest.param(cards_list_item, id="cards_list"),
        pytest.param(section_item, id="section"),
    ],
)
def test_preview_renders_block_as_on_page(freeform_page_factory, make_block, rf, serve_page, synced_block_factory):
    block = make_block()
    snippet = synced_block_factory(block)
    page = freeform_page_factory(content=[block])
    block_html = BeautifulSoup(serve_page(page).content, "html.parser").find("div", class_="fl-main").find(recursive=False)

    with translation.override("en-US"):
        preview_response = snippet.serve_preview(rf.get("/"), snippet.default_preview_mode)
        preview_response.render()

    preview_html = BeautifulSoup(preview_response.content, "html.parser")
    # Store links carry the page's campaign, which a preview has no page to take from.
    for store_link in [*block_html.select(".fl-store-button"), *preview_html.select(".fl-store-button")]:
        store_link.decompose()
    assert collapse_whitespace(block_html) in collapse_whitespace(preview_html)


def english_snippet_with_french_translation(synced_block_factory, synced_block_translation_factory):
    english = synced_block_factory(section_item("English"), name="Shared section")
    french = synced_block_translation_factory(english, get_locale("fr"), section_item("Français"))
    french.name = "Section partagée"
    french.save()
    return english, french


def test_listing_usage_counts_pages_using_any_translation(
    admin_client, freeform_page_factory, synced_block_factory, synced_block_translation_factory
):
    """Translated pages reference the English snippet, so each translation's row counts them too."""
    english, french = english_snippet_with_french_translation(synced_block_factory, synced_block_translation_factory)
    # Creates the English page and its French translation, both referencing the English snippet.
    freeform_page_factory(content=[synced_block_item(english)], locale=get_locale("fr"))

    response = admin_client.get(reverse(LISTING_URL_NAME), {"locale": "fr"}, follow=True)

    usage_link = listing_row(response, "Section partagée").find("a", string=lambda text: text and "Used 2 times" in collapse_whitespace(text))
    assert usage_link["href"] == reverse("wagtailsnippets_cms_syncedblocksnippet:usage", args=[english.pk])


def delete_url(snippet):
    return reverse("wagtailsnippets_cms_syncedblocksnippet:delete", args=[snippet.pk])


@pytest.mark.parametrize("method", ["get", "post"])
def test_deleting_a_used_synced_block_is_blocked(admin_client, freeform_page_factory, method, synced_block_factory):
    snippet = synced_block_factory(section_item(), name="Shared section")
    freeform_page_factory(content=[synced_block_item(snippet)])

    response = getattr(admin_client, method)(delete_url(snippet), follow=True)

    assert SyncedBlockSnippet.objects.filter(pk=snippet.pk).exists()
    assert any("Shared section" in str(message) and "used on 1 page" in str(message) for message in response.context["messages"])


def test_deleting_a_translation_of_a_used_synced_block_warns_then_deletes(
    admin_client, freeform_page_factory, synced_block_factory, synced_block_translation_factory
):
    english, french = english_snippet_with_french_translation(synced_block_factory, synced_block_translation_factory)
    freeform_page_factory(content=[synced_block_item(english)], locale=get_locale("fr"))

    confirm_response = admin_client.get(delete_url(french))

    assert confirm_response.status_code == 200
    assert any("fall back" in str(message) for message in confirm_response.context["messages"])
    admin_client.post(delete_url(french))
    assert not SyncedBlockSnippet.objects.filter(pk=french.pk).exists()


def test_deleting_an_unused_synced_block_is_allowed(admin_client, synced_block_factory):
    snippet = synced_block_factory(section_item())

    admin_client.post(delete_url(snippet))

    assert not SyncedBlockSnippet.objects.filter(pk=snippet.pk).exists()
