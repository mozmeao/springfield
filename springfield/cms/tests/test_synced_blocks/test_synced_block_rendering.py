# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from uuid import uuid4

from django.urls import reverse

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.block_factories import show_to_value
from springfield.cms.models import FreeFormPage2026
from springfield.cms.tests.test_synced_blocks.conftest import (
    cards_list_item,
    comparison_table_item,
    main_content_html,
    section_item,
    synced_block_item,
    synced_in_content_only,
    synced_in_split_page_lower,
    synced_in_split_page_upper,
)

pytestmark = [pytest.mark.django_db]

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def heading_tag_name(response, heading_text):
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.find(lambda tag: tag.name in HEADING_TAGS and tag.get_text(strip=True) == heading_text).name


def cta_attribute_values(response, attribute):
    main = BeautifulSoup(response.content, "html.parser").find("div", class_="fl-main")
    return [tag[attribute] for tag in main.find_all(attrs={attribute: True})]


def section_with_display_conditions():
    return section_item("Firefox users only", show_to=show_to_value(firefox="is-firefox"))


def content_only_layout(block, intro, other):
    return {"content": [intro, block]}


def split_page_upper_layout(block, intro, other):
    return {"upper_content": [intro, block], "content": [other]}


def split_page_lower_layout(block, intro, other):
    return {"upper_content": [other], "content": [intro, block]}


@pytest.mark.parametrize(
    "make_block, layout",
    [
        pytest.param(comparison_table_item, content_only_layout, id="comparison_table"),
        pytest.param(cards_list_item, content_only_layout, id="cards_list"),
        pytest.param(section_item, content_only_layout, id="section"),
        pytest.param(section_with_display_conditions, content_only_layout, id="section_with_display_conditions"),
        pytest.param(cards_list_item, split_page_upper_layout, id="split_page_upper"),
        pytest.param(cards_list_item, split_page_lower_layout, id="split_page_lower"),
    ],
)
def test_synced_block_renders_same_markup_as_inline_block(freeform_page_factory, layout, make_block, serve_page, synced_block_factory):
    block = make_block()
    intro = section_item("Intro")
    other = section_item("Other area")
    snippet = synced_block_factory(block)

    inline_page = freeform_page_factory(**layout(block, intro, other))
    synced_page = freeform_page_factory(**layout(synced_block_item(snippet), intro, other))

    # Download buttons put the page slug in their store links' campaign.
    synced_html = main_content_html(serve_page(synced_page)).replace(synced_page.slug, "page-slug")
    inline_html = main_content_html(serve_page(inline_page)).replace(inline_page.slug, "page-slug")
    assert synced_html == inline_html


def synced_first(synced_block_factory):
    return [synced_block_item(synced_block_factory(section_item("Synced")))]


def synced_after_heading_block(synced_block_factory):
    return [section_item("Inline"), synced_block_item(synced_block_factory(section_item("Synced")))]


def inline_after_synced(synced_block_factory):
    return [synced_block_item(synced_block_factory(section_item("Synced"))), section_item("Inline")]


def synced_after_leading_inline_with_display_conditions(synced_block_factory):
    snippet = synced_block_factory(section_item("Synced", show_to=show_to_value(firefox="not-firefox")))
    return [section_item("Inline", show_to=show_to_value(firefox="is-firefox")), synced_block_item(snippet)]


def inline_after_unpublished_synced(synced_block_factory):
    snippet = synced_block_factory(section_item("Synced"))
    snippet.unpublish()
    return [synced_block_item(snippet), section_item("Inline")]


def inline_after_synced_without_heading(synced_block_factory):
    return [synced_block_item(synced_block_factory(comparison_table_item())), section_item("Inline")]


@pytest.mark.parametrize(
    "build_content, heading_text, expected_tag",
    [
        pytest.param(synced_first, "Synced", "h1", id="synced_first_gets_h1"),
        pytest.param(synced_after_heading_block, "Synced", "h2", id="synced_after_heading_block_gets_h2"),
        pytest.param(inline_after_synced, "Inline", "h2", id="inline_after_synced_gets_h2"),
        pytest.param(
            synced_after_leading_inline_with_display_conditions,
            "Synced",
            "h1",
            id="synced_in_leading_run_with_display_conditions_gets_h1",
        ),
        pytest.param(inline_after_unpublished_synced, "Inline", "h1", id="inline_after_unpublished_synced_gets_h1"),
        pytest.param(inline_after_synced_without_heading, "Inline", "h1", id="inline_after_synced_without_heading_gets_h1"),
    ],
)
def test_synced_block_heading_level(build_content, expected_tag, freeform_page_factory, heading_text, serve_page, synced_block_factory):
    page = freeform_page_factory(content=build_content(synced_block_factory))

    assert heading_tag_name(serve_page(page), heading_text) == expected_tag


@pytest.mark.parametrize(
    "build_page_content, expected_position",
    [
        pytest.param(synced_in_content_only, "block-1-cards_list", id="content_only_page"),
        pytest.param(synced_in_split_page_upper, "upper-block-1-cards_list", id="split_page_upper"),
        pytest.param(synced_in_split_page_lower, "lower-block-1-cards_list", id="split_page_lower"),
    ],
)
def test_synced_block_cta_position_names_inner_block_type(
    build_page_content, expected_position, freeform_page_factory, serve_page, synced_block_factory
):
    snippet = synced_block_factory(cards_list_item())
    page = freeform_page_factory(**build_page_content(snippet))

    [position] = cta_attribute_values(serve_page(page), "data-cta-position")
    assert position.startswith(expected_position)


def test_publishing_synced_block_updates_page_using_it(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(section_item("Original heading"))
    page = freeform_page_factory(content=[synced_block_item(snippet)])

    snippet.content = [section_item("Updated heading")]
    snippet.save_revision().publish()

    assert "Updated heading" in main_content_html(serve_page(page))


def test_draft_edit_to_synced_block_does_not_render(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(section_item("Published heading"))
    page = freeform_page_factory(content=[synced_block_item(snippet)])

    snippet.content = [section_item("Draft heading")]
    snippet.save_revision()

    html = main_content_html(serve_page(page))
    assert "Published heading" in html
    assert "Draft heading" not in html


@pytest.mark.parametrize("removal_method", ["unpublish", "delete"])
def test_unpublished_or_deleted_synced_block_renders_nothing(freeform_page_factory, removal_method, serve_page, synced_block_factory):
    snippet = synced_block_factory(section_item("Synced heading"))
    page = freeform_page_factory(content=[synced_block_item(snippet), section_item("Inline heading")])

    getattr(snippet, removal_method)()
    response = serve_page(page)

    assert response.status_code == 200
    html = main_content_html(response)
    assert "Inline heading" in html
    assert "Synced heading" not in html


def test_synced_block_buttons_render_stored_analytics_ids(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(cards_list_item(button_analytics_id="stored-analytics-id"))
    page = freeform_page_factory(content=[synced_block_item(snippet)])

    assert cta_attribute_values(serve_page(page), "data-cta-uid") == ["stored-analytics-id"]


def test_copy_page_keeps_synced_block_and_its_analytics_ids(admin_client, freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(cards_list_item(button_analytics_id="stored-analytics-id"))
    page = freeform_page_factory(content=[synced_block_item(snippet)])

    response = admin_client.post(
        reverse("wagtailadmin_pages:copy", args=[page.id]),
        {"new_title": "Synced copy", "new_slug": "synced-copy", "new_parent_page": page.get_parent().id, "publish_copies": "on"},
    )

    assert response.status_code == 302
    copied_page = FreeFormPage2026.objects.get(slug="synced-copy")
    assert copied_page.content[0].block_type == "synced_block"
    assert copied_page.content[0].value == snippet
    assert cta_attribute_values(serve_page(copied_page), "data-cta-uid") == ["stored-analytics-id"]


def test_html_ids_are_unique_when_synced_block_placed_twice(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(cards_list_item(button_analytics_id="stored-analytics-id", show_default_browser_checkbox=True))
    page = freeform_page_factory(content=[synced_block_item(snippet), synced_block_item(snippet)])

    response = serve_page(page)

    # Other fixed IDs inside the download button (e.g. the Play Store link) repeat for any two buttons, synced or not.
    main = BeautifulSoup(response.content, "html.parser").find("div", class_="fl-main")
    analytics_html_ids = [tag["id"] for tag in main.find_all(id=lambda html_id: html_id and "stored-analytics-id" in html_id)]
    assert len(analytics_html_ids) == 4
    assert len(set(analytics_html_ids)) == 4
    assert cta_attribute_values(response, "data-cta-uid") == ["stored-analytics-id", "stored-analytics-id"]


def section_with_qr_code_modal_button(analytics_id):
    item = section_item()
    item["value"]["cta"] = [
        {
            "type": "qr_code_modal_button",
            "value": {
                "settings": {"theme": "", "icon": "device-mobile", "icon_position": "left", "analytics_id": analytics_id},
                "pretranslated_label": None,
                "custom_label": "Get Firefox on your phone",
                "url": "https://www.mozilla.org/firefox/mobile/",
                "heading": "Get Firefox on your phone",
                "content": "",
            },
            "id": str(uuid4()),
        }
    ]
    return item


def test_qr_code_dialog_ids_are_unique_when_synced_block_placed_twice(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(section_with_qr_code_modal_button("qr-analytics-id"))
    page = freeform_page_factory(content=[synced_block_item(snippet), synced_block_item(snippet)])

    main = BeautifulSoup(serve_page(page).content, "html.parser").find("div", class_="fl-main")

    dialog_ids = [dialog["id"] for dialog in main.find_all("dialog")]
    assert len(set(dialog_ids)) == 2
    assert [trigger["data-target-id"] for trigger in main.select(".fl-dialog-trigger")] == dialog_ids


def test_rendered_blocks_number_headings_across_split_layout(freeform_page_factory):
    firefox_only = show_to_value(firefox="is-firefox")
    page = freeform_page_factory(
        upper_content=[section_item("Upper conditional", show_to=firefox_only)],
        content=[section_item("Lower conditional", show_to=firefox_only), section_item("Everyone"), section_item("Later")],
    )

    levels_and_positions = [
        (block_level, block_position)
        for field_name in ("upper_content", "content")
        for _block, _suffix, block_level, block_position in page.rendered_blocks[field_name]
    ]

    assert levels_and_positions == [
        (1, "upper-block-1-section"),
        (1, "lower-block-1-section"),
        (2, "lower-block-2-section"),
        (2, "lower-block-3-section"),
    ]


def test_unpublished_synced_block_alone_in_upper_content_drops_split_layout(freeform_page_factory, serve_page, synced_block_factory):
    snippet = synced_block_factory(section_item("Synced hero"))
    page = freeform_page_factory(upper_content=[synced_block_item(snippet)], content=[section_item("Lower heading")])

    snippet.unpublish()
    response = serve_page(page)

    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(class_="fl-split-page-upper") is None
    assert heading_tag_name(response, "Lower heading") == "h1"
