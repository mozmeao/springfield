# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.core.exceptions import ValidationError

import pytest
from wagtail.models import Locale

from springfield.cms.blocks import FluentOrCustomTextBlock, FluentOrCustomTextValue
from springfield.cms.models.snippets import PreFooterCTASnippet

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


# -- FluentOrCustomTextBlock.clean() --


def test_clean_preset_passes():
    """Choosing "Get Firefox" and setting empty custom_text is valid."""
    block = FluentOrCustomTextBlock()
    result = block.clean({"pretranslated_or_custom": "navigation-get-firefox", "custom_text": ""})
    assert result["pretranslated_or_custom"] == "navigation-get-firefox"


def test_clean_custom_with_text_passes():
    """Choosing "Custom Text" and setting non-empty custom_text is valid."""
    block = FluentOrCustomTextBlock()
    result = block.clean({"pretranslated_or_custom": "custom", "custom_text": "My Label"})
    assert result["custom_text"] == "My Label"


def test_clean_custom_without_text_raises():
    """Choosing "Custom Text" and setting empty custom_text is not valid."""
    block = FluentOrCustomTextBlock()
    with pytest.raises(ValidationError) as exc_info:
        block.clean({"pretranslated_or_custom": "custom", "custom_text": ""})
    assert "custom_text" in exc_info.value.block_errors


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
