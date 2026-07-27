# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Tests for the ``data-cta-text`` rendered for buttons inside a
``button_row`` in a field of a page.

These tests exercise a real user path (using client.get() for a published page),
rather than calling block helpers directly, so we can catch issues with rendered
text. For example:
1. if block_text is undefined in a component template, the page template may
   render {{ block_text }}
2. button templates reassign the shared block_text variable to add a suffix
   that has already been added, so the page template renders
   "text - Get Firefox - Get Firefox"
"""

import re

from django.test import override_settings

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Locale

from springfield.cms.fixtures.snippet_fixtures import (
    get_pretranslated_phrase_snippets,
    get_set_as_default_snippet,
)
from springfield.cms.management.commands.create_pretranslated_phrases import PHRASES
from springfield.cms.models import FreeFormPage2026, PretranslatedPhrase

pytestmark = pytest.mark.django_db

BLOCK_TEXT_LITERAL = "{{ block_text }}"

# A unique analytics id per button so the rendered element can be matched back
# to the label we built it with (the id is emitted as ``data-cta-uid``).
UID = {
    "button_custom": "11111111-0000-0000-0000-000000000001",
    "button_pretranslated": "11111111-0000-0000-0000-000000000002",
    "fxa": "11111111-0000-0000-0000-000000000003",
    "download": "11111111-0000-0000-0000-000000000004",
    "uitour": "11111111-0000-0000-0000-000000000005",
    "set_as_default": "11111111-0000-0000-0000-000000000006",
    "focus": "11111111-0000-0000-0000-000000000007",
}

# Buttons whose analytics text is expected to include the button label exactly
# once. (The focus button's analytics text is heading-only, and the store
# button has no analytics text, so they are excluded here.)
LABEL_BEARING = {
    UID["button_custom"]: "Custom Button A",
    UID["button_pretranslated"]: "Get Firefox",
    UID["fxa"]: "Log in",
    UID["download"]: "Get Firefox",
    UID["uitour"]: "Open New Tab",
    UID["set_as_default"]: "Set Firefox as default",
}


def _link(custom_url="https://mozilla.org"):
    return {
        "link_to": "custom_url",
        "page": None,
        "file": None,
        "custom_url": custom_url,
        "anchor": "",
        "email": "",
        "phone": "",
        "new_window": False,
        "relative_url": "",
    }


def _button_settings(uid, icon="", icon_position="right", theme=""):
    return {"theme": theme, "icon": icon, "icon_position": icon_position, "analytics_id": uid}


def _build_upper_content():
    """Return ``upper_content`` StreamField data: button_rows containing every
    button type that a button_row allows (allow_uitour=True)."""
    get_pretranslated_phrase_snippets()
    get_firefox_pk = PretranslatedPhrase.objects.get(
        translation_key=PHRASES["get_firefox"]["translation_key"],
        locale=Locale.get_default(),
    ).pk
    set_as_default_snippet = get_set_as_default_snippet()

    button_custom = {
        "type": "button",
        "value": {
            "settings": _button_settings(UID["button_custom"]),
            "pretranslated_label": None,
            "custom_label": "Custom Button A",
            "link": _link(),
        },
        "id": "btn00000-0000-0000-0000-000000000001",
    }
    button_pretranslated = {
        "type": "button",
        "value": {
            "settings": _button_settings(UID["button_pretranslated"]),
            "pretranslated_label": get_firefox_pk,
            "custom_label": "",
            "link": _link(),
        },
        "id": "btn00000-0000-0000-0000-000000000002",
    }
    fxa_button = {
        "type": "fxa_button",
        "value": {
            "settings": _button_settings(UID["fxa"], icon="single-user", icon_position="left", theme="ghost"),
            "pretranslated_label": None,
            "custom_label": "Log in",
        },
        "id": "btn00000-0000-0000-0000-000000000003",
    }
    download_button = {
        "type": "download_button",
        "value": {
            "settings": {
                "theme": "",
                "icon": "downloads",
                "icon_position": "right",
                "analytics_id": UID["download"],
                "show_default_browser_checkbox": False,
            },
            "pretranslated_label": get_firefox_pk,
            "custom_label": "",
        },
        "id": "btn00000-0000-0000-0000-000000000004",
    }
    uitour_button = {
        "type": "uitour_button",
        "value": {
            "settings": _button_settings(UID["uitour"], icon="open-tabs"),
            "button_type": "open_new_tab",
            "pretranslated_label": None,
            "custom_label": "Open New Tab",
        },
        "id": "btn00000-0000-0000-0000-000000000005",
    }
    set_as_default_button = {
        "type": "set_as_default_button",
        "value": {
            "settings": _button_settings(UID["set_as_default"]),
            "pretranslated_label": None,
            "custom_label": "Set Firefox as default",
            "snippet": set_as_default_snippet.id,
        },
        "id": "btn00000-0000-0000-0000-000000000006",
    }
    focus_button = {
        "type": "focus_button",
        "value": {
            "settings": _button_settings(UID["focus"], icon="downloads"),
            "pretranslated_label": None,
            "custom_label": "Get Firefox Focus for Android",
            "store": "android",
        },
        "id": "btn00000-0000-0000-0000-000000000007",
    }
    store_button = {
        "type": "store_button",
        "value": {"store": "android"},
        "id": "btn00000-0000-0000-0000-000000000008",
    }

    def _button_row(row_id, buttons):
        return {
            "type": "button_row",
            "value": {"spacing": "", "buttons": buttons, "help_text": ""},
            "id": row_id,
        }

    # max_num=3 per button_row, so split the eight buttons across three rows.
    return [
        _button_row("row00000-0000-0000-0000-000000000001", [button_custom, button_pretranslated, fxa_button]),
        _button_row("row00000-0000-0000-0000-000000000002", [download_button, uitour_button, set_as_default_button]),
        _button_row("row00000-0000-0000-0000-000000000003", [focus_button, store_button]),
    ]


@pytest.fixture
def page_with_all_buttons(minimal_site):
    root_page = minimal_site.root_page
    page = FreeFormPage2026(
        slug="button-row-cta-text",
        title="Button Row CTA Text Test",
        upper_content=_build_upper_content(),
    )
    root_page.add_child(instance=page)
    page.save_revision().publish()
    return page


def _get_cta_texts_on_page(html):
    """Return {data-cta-uid: data-cta-text} for every element on the page."""
    soup = BeautifulSoup(html, "html.parser")
    return {el.get("data-cta-uid"): el.get("data-cta-text") for el in soup.select("[data-cta-text]")}


def test_page_with_all_buttons_renders(page_with_all_buttons, client):
    response = client.get(page_with_all_buttons.url)
    assert response.status_code == 200


@pytest.mark.parametrize("debug_value", [True, False])
def test_no_button_renders_the_undefined_block_text_literal(page_with_all_buttons, client, debug_value):
    """No button's analytics text should contain the literal {{ block_text }}."""
    with override_settings(DEBUG=debug_value):
        response = client.get(page_with_all_buttons.url)
    html = response.content.decode("utf-8")

    # Sanity: the literal must not appear anywhere in the rendered page.
    assert BLOCK_TEXT_LITERAL not in html, "Undefined block_text leaked the literal `{{ block_text }}` into the page"

    cta_texts = _get_cta_texts_on_page(html)
    for uid, cta_text in cta_texts.items():
        assert BLOCK_TEXT_LITERAL not in (cta_text or ""), f"button {uid} rendered the literal block_text: {cta_text!r}"


@override_settings(DEBUG=True)
@pytest.mark.parametrize("uid", list(LABEL_BEARING))
def test_button_label_is_not_doubled_in_cta_text(uid, page_with_all_buttons, client):
    """
    A button's analytics text must contain its label exactly once.

    This test is meant to catch when the analytics text either:
      - is missing the label
      - has the label duplicated (like "... - Get Firefox - Get Firefox").
    """
    response = client.get(page_with_all_buttons.url)
    html = response.content.decode("utf-8")
    cta_texts = _get_cta_texts_on_page(html)

    label = LABEL_BEARING[uid]
    cta_text = cta_texts.get(uid)
    assert cta_text is not None, f"no rendered button found with data-cta-uid={uid}"

    occurrences = len(re.findall(re.escape(label), cta_text))
    assert occurrences == 1, f"button {uid} label {label!r} appears {occurrences}x in {cta_text!r} (expected exactly 1)"
