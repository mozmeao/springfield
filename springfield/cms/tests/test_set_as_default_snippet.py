# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from bs4 import BeautifulSoup

from springfield.cms.fixtures.freeformpage_2026 import get_freeform_page_2026_with_set_as_default_button
from springfield.cms.fixtures.snippet_fixtures import get_set_as_default_snippet

pytestmark = [pytest.mark.django_db]


def _get_set_as_default_dialog(soup):
    return soup.find("div", class_="fl-set-as-default-dialog")


def test_page_with_set_as_default_button_renders_dialog(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)
    assert dialog_wrapper, "Set as default dialog wrapper should be rendered"
    assert dialog_wrapper.find("dialog", {"id": "set-as-default-dialog"}), "Dialog element should be rendered with correct id"


def test_page_with_set_as_default_button_renders_trigger_button(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    trigger = soup.find("button", class_="fl-set-as-default-button")
    assert trigger, "Set as default trigger button should be rendered"
    assert trigger.get("data-target-id") == "set-as-default-dialog", "Trigger button should point to the dialog"
    assert "Set Firefox as default" in trigger.get_text()


def test_set_as_default_dialog_contains_heading(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)
    assert "Thanks for choosing Firefox" in dialog_wrapper.get_text()


def test_set_as_default_dialog_contains_all_content_sections(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)

    assert dialog_wrapper.find("div", class_="conditional-not-firefox"), "Not-Firefox content section should be rendered"
    assert dialog_wrapper.find("div", class_="condition-is-not-default"), "Not-default content section should be rendered"
    assert dialog_wrapper.find("div", class_="condition-is-default"), "Success content section should be rendered"


def test_set_as_default_dialog_contains_platform_content(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)
    not_default_section = dialog_wrapper.find("div", class_="condition-is-not-default")

    assert not_default_section.find("div", class_="condition-android"), "Android content section should be rendered"
    assert not_default_section.find("div", class_="condition-ios"), "iOS content section should be rendered"
    assert not_default_section.find("div", class_="condition-osx"), "Desktop content section should be rendered"


def test_set_as_default_dialog_renders_snippet_text(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)
    dialog_text = dialog_wrapper.get_text()

    assert "Looks like you're using a different browser" in dialog_text, "Not-Firefox content should be rendered"
    assert "You're almost done" in dialog_text, "Desktop not-default content should be rendered"
    assert "Android devices" in dialog_text, "Android not-default content should be rendered"
    assert "iOS devices" in dialog_text, "iOS not-default content should be rendered"
    assert "You're all set" in dialog_text, "Success content should be rendered"


def test_set_as_default_button_shows_error_when_no_snippet(minimal_site, rf):
    """When no SetAsDefaultSnippet exists, an error notification should be rendered instead of the dialog."""
    from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page
    from springfield.cms.fixtures.freeformpage_2026 import get_set_as_default_button_block
    from springfield.cms.models import FreeFormPage2026

    index_page = get_2026_test_index_page()
    slug = "freeform-2026-no-snippet"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="No Snippet Test")
        index_page.add_child(instance=page)
    page.content = [get_set_as_default_button_block()]
    page.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    assert not _get_set_as_default_dialog(soup), "Dialog should not render when no snippet exists"
    notification = soup.find("p", class_="fl-notification-red")
    assert "The Set as Default button requires a Set as Default snippet. Please add one in the CMS." in notification.get_text()


def test_set_as_default_snippet_str(minimal_site):
    snippet = get_set_as_default_snippet()
    assert "Thanks for choosing Firefox" in str(snippet)


def test_set_as_default_snippet_is_live(minimal_site):
    snippet = get_set_as_default_snippet()
    assert snippet.live


def test_updated_snippet_content_is_reflected_on_page(minimal_site, rf):
    page = get_freeform_page_2026_with_set_as_default_button()
    snippet = get_set_as_default_snippet()
    snippet.success_content = '<p data-block-key="sc002">Success! Your default browser is set to Firefox.</p>'
    snippet.save()
    snippet.save_revision().publish()

    request = rf.get(page.get_full_url())
    response = page.serve(request)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    dialog_wrapper = _get_set_as_default_dialog(soup)
    assert "Success! Your default browser is set to Firefox." in dialog_wrapper.get_text()
