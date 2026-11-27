# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import messages
from django.contrib.messages import get_messages
from django.urls import reverse

import pytest
from wagtail.test.utils.form_data import inline_formset, nested_form_data, rich_text, streamfield

from springfield.cms.fixtures.block_factories import show_to_value
from springfield.cms.tests.test_pages import build_page_save_request
from springfield.cms.tests.test_synced_blocks.conftest import get_locale, section_item, synced_block_item
from springfield.cms.wagtail_hooks import warn_about_leading_conditional_blocks

pytestmark = [pytest.mark.django_db]


def section_form_data(heading_text, anchor_id=""):
    """An inline section as the page editor posts it."""
    return (
        "section",
        {
            "settings": {"anchor_id": anchor_id},
            "heading": {"heading_text": rich_text(f"<p>{heading_text}</p>")},
            "content": streamfield([]),
            "cta": streamfield([]),
        },
    )


def synced_block_form_data(snippet):
    return ("synced_block", snippet.pk)


def save_draft(admin_client, page, *, upper_content=(), content=()):
    """Save ``page`` as a draft through the admin edit view with the given stream areas."""
    data = {
        "title": page.title,
        "slug": page.slug,
        "pre_footer_image": "kit",
        "upper_content": streamfield(list(upper_content)),
        "content": streamfield(list(content)),
        "pencil_banner_placements": inline_formset([]),
    }
    return admin_client.post(reverse("wagtailadmin_pages:edit", args=[page.id]), nested_form_data(data))


def synced_block_pks(stream_value):
    return [child.value.pk for child in stream_value if child.block_type == "synced_block"]


def assert_page_rejects(response, snippet_name, reason_text):
    assert response.status_code == 200
    form_errors = response.context["form"].errors
    messages = [
        message
        for field_name in ("upper_content", "content")
        if field_name in form_errors
        for block_error in form_errors[field_name].as_data()[0].block_errors.values()
        for message in block_error.messages
    ]
    assert any(snippet_name in message and reason_text in message for message in messages), messages


def synced_in_split_page_upper(snippet):
    return {"upper_content": [synced_block_form_data(snippet)], "content": [section_form_data("Lower")]}


def synced_in_content_only(snippet):
    return {"content": [synced_block_form_data(snippet)]}


def same_block_twice_without_anchor(snippet):
    return {"content": [synced_block_form_data(snippet), synced_block_form_data(snippet)]}


def blank_anchor_beside_inline_blank_anchor(snippet):
    return {"content": [section_form_data("Inline", anchor_id=""), synced_block_form_data(snippet)]}


def anchor_unique_against_inline_blocks_in_both_areas(snippet):
    return {
        "upper_content": [section_form_data("Upper inline", anchor_id="upper-anchor")],
        "content": [section_form_data("Lower inline", anchor_id="lower-anchor"), synced_block_form_data(snippet)],
    }


@pytest.mark.parametrize(
    "snippet_anchor_id, build_page_content",
    [
        pytest.param("", synced_in_split_page_upper, id="split_page_upper"),
        pytest.param("", synced_in_content_only, id="content_only"),
        pytest.param("", same_block_twice_without_anchor, id="same_block_twice_without_anchor"),
        pytest.param("", blank_anchor_beside_inline_blank_anchor, id="blank_anchor_beside_inline_blank_anchor"),
        pytest.param("synced-anchor", anchor_unique_against_inline_blocks_in_both_areas, id="anchor_unique_against_inline_blocks_in_both_areas"),
    ],
)
def test_page_accepts_synced_block(admin_client, build_page_content, freeform_page_factory, snippet_anchor_id, synced_block_factory):
    snippet = synced_block_factory(section_item("Synced", anchor_id=snippet_anchor_id))
    page = freeform_page_factory(publish=False)
    page_content = build_page_content(snippet)

    response = save_draft(admin_client, page, **page_content)

    assert response.status_code == 302
    page.refresh_from_db()
    saved_page = page.get_latest_revision_as_object()
    for field_name, blocks in page_content.items():
        assert synced_block_pks(getattr(saved_page, field_name)) == [value for block_type, value in blocks if block_type == "synced_block"]


def test_page_rejects_unpublished_synced_block(admin_client, freeform_page_factory, synced_block_factory):
    snippet = synced_block_factory(section_item(), name="Draft pricing table", publish=False)
    page = freeform_page_factory(publish=False)

    response = save_draft(admin_client, page, content=[synced_block_form_data(snippet)])

    assert_page_rejects(response, "Draft pricing table", "The selected snippet is not published.")


@pytest.mark.parametrize(
    "page_language_code, snippet_language_code",
    [
        pytest.param("en-US", "fr", id="en_page_fr_snippet"),
        pytest.param("fr", "en-US", id="fr_page_en_snippet"),
    ],
)
def test_page_accepts_synced_block_in_another_locale(
    admin_client, freeform_page_factory, page_language_code, snippet_language_code, synced_block_factory
):
    """Translated pages keep pointing at the English snippet, so the editor must be able to save them."""
    snippet = synced_block_factory(section_item(), locale=get_locale(snippet_language_code))
    page = freeform_page_factory(locale=get_locale(page_language_code), publish=False)

    response = save_draft(admin_client, page, content=[synced_block_form_data(snippet)])

    assert response.status_code == 302


def anchor_used_by_inline_block_in_same_area(snippet, other_snippet):
    return {"content": [section_form_data("Inline", anchor_id="pricing"), synced_block_form_data(snippet)]}


def anchor_used_by_inline_block_in_other_area(snippet, other_snippet):
    return {"upper_content": [section_form_data("Inline", anchor_id="pricing")], "content": [synced_block_form_data(snippet)]}


def same_synced_block_twice(snippet, other_snippet):
    return {"content": [synced_block_form_data(snippet), synced_block_form_data(snippet)]}


def two_synced_blocks(snippet, other_snippet):
    return {"content": [synced_block_form_data(other_snippet), synced_block_form_data(snippet)]}


@pytest.mark.parametrize(
    "build_page_content",
    [
        pytest.param(anchor_used_by_inline_block_in_same_area, id="inline_same_area"),
        pytest.param(anchor_used_by_inline_block_in_other_area, id="inline_other_area"),
        pytest.param(same_synced_block_twice, id="same_synced_block_twice"),
        pytest.param(two_synced_blocks, id="two_synced_blocks"),
    ],
)
def test_page_rejects_duplicate_anchor_id(admin_client, build_page_content, freeform_page_factory, synced_block_factory):
    snippet = synced_block_factory(section_item("Synced", anchor_id="pricing"), name="Pricing section")
    other_snippet = synced_block_factory(section_item("Other synced", anchor_id="pricing"), name="Plans section")
    page = freeform_page_factory(publish=False)

    response = save_draft(admin_client, page, **build_page_content(snippet, other_snippet))

    assert_page_rejects(response, "Pricing section", "pricing")


def conditional_section(heading_text):
    return section_item(heading_text, show_to=show_to_value(firefox="is-firefox"))


def leading_warnings(page, content, rf):
    page.content = content
    page.save_revision().publish()
    request = build_page_save_request(rf, page)
    warn_about_leading_conditional_blocks(request, page)
    return [str(message) for message in get_messages(request) if message.level == messages.WARNING]


def test_editor_is_warned_when_a_conditional_synced_block_leads(freeform_page_factory, rf, synced_block_factory):
    snippet = synced_block_factory(conditional_section("Synced"))

    warnings = leading_warnings(freeform_page_factory(), [synced_block_item(snippet)], rf)

    assert len(warnings) == 1
    assert "leads with 1 conditional block" in warnings[0]


def test_editor_is_not_warned_when_an_unconditional_synced_block_leads(freeform_page_factory, rf, synced_block_factory):
    snippet = synced_block_factory(section_item("Synced"))

    warnings = leading_warnings(freeform_page_factory(), [synced_block_item(snippet), conditional_section("Inline")], rf)

    assert warnings == []
