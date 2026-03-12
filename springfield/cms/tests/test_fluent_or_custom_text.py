# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from copy import deepcopy
from importlib import import_module
from unittest import mock

import pytest
from wagtail.models import Locale

from springfield.cms.blocks import FluentOrCustomTextBlock, FluentOrCustomTextValue
from springfield.cms.models.snippets import PreFooterCTASnippet

_mgmt_cmd = import_module("springfield.cms.management.commands.migrate_download_button_labels")
convert_download_button_label = _mgmt_cmd.convert_download_button_label

pytestmark = [pytest.mark.django_db]


# -- FluentOrCustomTextValue.resolve_text() --


@mock.patch("springfield.cms.blocks.ftl", return_value="Get Firefox")
def test_resolve_text_with_preset_get_firefox(mock_ftl):
    value = FluentOrCustomTextValue(None, [("pretranslated_or_custom", "navigation-get-firefox"), ("custom_text", "")])
    result = value.resolve_text()
    assert result == "Get Firefox"
    mock_ftl.assert_called_once_with("navigation-get-firefox", ftl_files=["navigation-firefox", "download_button"])


@mock.patch("springfield.cms.blocks.ftl", return_value="Download Firefox")
def test_resolve_text_with_preset_download_firefox(mock_ftl):
    value = FluentOrCustomTextValue(None, [("pretranslated_or_custom", "download-button-download-firefox"), ("custom_text", "")])
    result = value.resolve_text()
    assert result == "Download Firefox"
    mock_ftl.assert_called_once_with("download-button-download-firefox", ftl_files=["navigation-firefox", "download_button"])


def test_resolve_text_with_custom():
    value = FluentOrCustomTextValue(None, [("pretranslated_or_custom", "custom"), ("custom_text", "My Label")])
    assert value.resolve_text() == "My Label"


def test_resolve_text_with_custom_empty():
    value = FluentOrCustomTextValue(None, [("pretranslated_or_custom", "custom"), ("custom_text", "")])
    assert value.resolve_text() == ""


# -- FluentOrCustomTextBlock.get_translatable_segments() --


def test_translatable_segments_preset_returns_empty():
    block = FluentOrCustomTextBlock()
    segments = block.get_translatable_segments({"pretranslated_or_custom": "navigation-get-firefox", "custom_text": ""})
    assert segments == []
    segments = block.get_translatable_segments({"pretranslated_or_custom": "download-button-download-firefox", "custom_text": ""})
    assert segments == []


def test_translatable_segments_custom_returns_segment():
    block = FluentOrCustomTextBlock()
    segments = block.get_translatable_segments({"pretranslated_or_custom": "custom", "custom_text": "My Label"})
    assert len(segments) == 1
    assert segments[0].path == "custom_text"
    assert segments[0].string.data == "My Label"


def test_translatable_segments_custom_empty_returns_empty():
    block = FluentOrCustomTextBlock()
    segments = block.get_translatable_segments({"pretranslated_or_custom": "custom", "custom_text": ""})
    assert segments == []


# -- PreFooterCTASnippet.resolve_label() --


@mock.patch("springfield.cms.models.snippets.ftl", return_value="Download Firefox")
def test_snippet_resolve_label_preset(mock_ftl):
    locale = Locale.objects.get(language_code="en-US")
    snippet = PreFooterCTASnippet(
        pretranslated_label="download-button-download-firefox",
        custom_label="",
        locale=locale,
    )
    assert snippet.resolve_label() == "Download Firefox"
    mock_ftl.assert_called_once_with("download-button-download-firefox", ftl_files=["navigation-firefox", "download_button"])


def test_snippet_resolve_label_custom():
    locale = Locale.objects.get(language_code="en-US")
    snippet = PreFooterCTASnippet(
        pretranslated_label="custom",
        custom_label="Buy Firefox",
        locale=locale,
    )
    assert snippet.resolve_label() == "Buy Firefox"


# -- convert_download_button_label() management command helper --


def _make_download_button_block(label):
    """Create a download_button block with old-style string label."""
    return {
        "type": "download_button",
        "value": {
            "label": label,
            "settings": {"theme": "", "icon": "downloads"},
        },
    }


def test_convert_english_get_firefox():
    data = _make_download_button_block("Get Firefox")
    assert convert_download_button_label(data, is_english=True) is True
    assert data["value"]["label"] == {"pretranslated_or_custom": "navigation-get-firefox", "custom_text": ""}


def test_convert_english_download_firefox():
    data = _make_download_button_block("Download Firefox")
    assert convert_download_button_label(data, is_english=True) is True
    assert data["value"]["label"]["pretranslated_or_custom"] == "download-button-download-firefox"


def test_convert_english_unknown_label():
    data = _make_download_button_block("Something Else")
    assert convert_download_button_label(data, is_english=True) is True
    assert data["value"]["label"] == {"pretranslated_or_custom": "custom", "custom_text": "Something Else"}


def test_convert_non_english():
    data = _make_download_button_block("Télécharger Firefox")
    assert convert_download_button_label(data, is_english=False) is True
    assert data["value"]["label"]["pretranslated_or_custom"] == "download-button-download-firefox"


def test_convert_nested_blocks():
    data = {
        "type": "section",
        "value": {
            "buttons": [
                _make_download_button_block("Get Firefox"),
                _make_download_button_block("Download Firefox"),
            ]
        },
    }
    assert convert_download_button_label(data, is_english=True) is True
    assert data["value"]["buttons"][0]["value"]["label"]["pretranslated_or_custom"] == "navigation-get-firefox"
    assert data["value"]["buttons"][1]["value"]["label"]["pretranslated_or_custom"] == "download-button-download-firefox"


def test_convert_no_download_button():
    data = {"type": "button", "value": {"label": "Click me"}}
    assert convert_download_button_label(data, is_english=True) is False


def test_convert_already_migrated():
    """Block with dict label (already migrated) is not touched."""
    data = {
        "type": "download_button",
        "value": {
            "label": {"pretranslated_or_custom": "navigation-get-firefox", "custom_text": ""},
            "settings": {"theme": ""},
        },
    }
    original = deepcopy(data)
    assert convert_download_button_label(data, is_english=True) is False
    assert data == original
