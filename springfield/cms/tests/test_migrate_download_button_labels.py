# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from copy import deepcopy
from io import StringIO

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

import pytest
from wagtail.models import Page, Revision

from springfield.cms.fixtures.snippet_fixtures import get_button_label_snippets
from springfield.cms.management.commands.migrate_download_button_labels import (
    collect_english_block_labels,
    convert_english_download_button_label,
    convert_non_english_download_button_label,
)
from springfield.cms.models import ButtonLabelSnippet, FreeFormPage
from springfield.cms.tests.factories import LocaleFactory

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SETTINGS = {
    "theme": "",
    "icon": "",
    "icon_position": "right",
    "analytics_id": "00000000-0000-0000-0000-000000000001",
    "show_default_browser_checkbox": False,
}


def _old_block(label, block_id="aaaaaaaa-0000-0000-0000-000000000001"):
    """Old-format download_button block: has 'label', no pretranslated_label."""
    return {
        "type": "download_button",
        "id": block_id,
        "value": {"label": label, "settings": _SETTINGS},
    }


def _new_block(pretranslated_id, custom_label="", block_id="aaaaaaaa-0000-0000-0000-000000000001"):
    """New-format download_button block: has pretranslated_label, no 'label'."""
    return {
        "type": "download_button",
        "id": block_id,
        "value": {"pretranslated_label": pretranslated_id, "custom_label": custom_label, "settings": _SETTINGS},
    }


def _intro_with_buttons(*download_blocks, intro_id="cc000000-0000-0000-0000-000000000000"):
    """Wrap download_button blocks in a valid IntroBlock so FreeFormPage.content accepts them."""
    return {
        "type": "intro",
        "id": intro_id,
        "value": {
            "settings": {"media_position": "after", "anchor_id": ""},
            "media": [],
            "heading": {"superheading_text": "", "heading_text": "<p>Test</p>", "subheading_text": ""},
            "buttons": list(download_blocks),
        },
    }


# ---------------------------------------------------------------------------
# Unit tests for the three pure conversion functions (no database)
# ---------------------------------------------------------------------------


class TestConvertEnglishDownloadButtonLabel:
    def test_get_firefox_maps_to_snippet_id(self):
        block = _old_block("Get Firefox")
        assert convert_english_download_button_label(block) is True
        assert block["value"]["pretranslated_label"] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID
        assert block["value"]["custom_label"] == ""
        assert "label" not in block["value"]

    def test_download_firefox_maps_to_snippet_id(self):
        block = _old_block("Download Firefox")
        assert convert_english_download_button_label(block) is True
        assert block["value"]["pretranslated_label"] == settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID
        assert block["value"]["custom_label"] == ""
        assert "label" not in block["value"]

    def test_unknown_text_becomes_custom_label(self):
        block = _old_block("Try Firefox Now")
        assert convert_english_download_button_label(block) is True
        assert block["value"]["pretranslated_label"] is None
        assert block["value"]["custom_label"] == "Try Firefox Now"
        assert "label" not in block["value"]

    def test_already_converted_block_is_idempotent(self):
        block = _new_block(settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID)
        assert convert_english_download_button_label(block) is False
        assert block["value"]["pretranslated_label"] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID

    def test_recurses_into_list(self):
        """Top-level list (StreamField raw_data shape) is walked recursively."""
        data = [_old_block("Get Firefox")]
        assert convert_english_download_button_label(data) is True
        assert data[0]["value"]["pretranslated_label"] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID

    def test_recurses_into_nested_dict(self):
        """download_button nested inside another block (e.g. intro.buttons) is converted."""
        data = {
            "type": "intro",
            "id": "intro-id",
            "value": {"buttons": [_old_block("Download Firefox")]},
        }
        assert convert_english_download_button_label(data) is True
        assert data["value"]["buttons"][0]["value"]["pretranslated_label"] == settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID

    def test_non_download_block_is_untouched(self):
        block = {"type": "paragraph", "id": "p-id", "value": "Hello"}
        old_block = deepcopy(block)
        assert convert_english_download_button_label(block) is False
        assert block == old_block


class TestCollectEnglishBlockLabels:
    def test_collects_snippet_id_by_block_id(self):
        block = _new_block(settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID, block_id="block-abc")
        out = {}
        collect_english_block_labels([block], "translation-key-1", out)
        assert out[("translation-key-1", "block-abc")] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID

    def test_ignores_custom_label_blocks(self):
        """Blocks with pretranslated_label=None (custom path) are not recorded."""
        block = _new_block(None, custom_label="Custom", block_id="block-xyz")
        out = {}
        collect_english_block_labels([block], "tk", out)
        assert out == {}

    def test_ignores_blocks_without_id(self):
        block = {
            "type": "download_button",
            "value": {"pretranslated_label": settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID, "custom_label": "", "settings": _SETTINGS},
            # no "id" key
        }
        out = {}
        collect_english_block_labels([block], "tk", out)
        assert out == {}


class TestConvertNonEnglishDownloadButtonLabel:
    def test_english_block_labels_are_not_used_for_lookup(self):
        """Block-ID matching was removed; english_block_labels is ignored."""
        english_block_labels = {("tk-1", "block-abc"): settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID}
        block = _old_block("Télécharger Firefox", block_id="block-abc")
        assert convert_non_english_download_button_label(block, "tk-1", english_block_labels) is True
        # No localized_label_map provided → becomes custom_label, not the matched EN snippet
        assert block["value"]["pretranslated_label"] is None
        assert block["value"]["custom_label"] == "Télécharger Firefox"
        assert "label" not in block["value"]

    def test_becomes_custom_label_when_no_match(self):
        block = _old_block("Descargar Firefox", block_id="block-xyz")
        assert convert_non_english_download_button_label(block, "tk-1", {}) is True
        assert block["value"]["pretranslated_label"] is None
        assert block["value"]["custom_label"] == "Descargar Firefox"
        assert "label" not in block["value"]

    def test_uses_localized_label_map(self):
        """localized_label_map maps (locale_id, label_text) → locale-specific snippet pk."""
        locale_specific_snippet_id = 9999
        localized_label_map = {(42, "Descargar Firefox"): locale_specific_snippet_id}
        block = _old_block("Descargar Firefox", block_id="block-xyz")
        assert convert_non_english_download_button_label(block, "tk-1", {}, locale_id=42, localized_label_map=localized_label_map) is True
        assert block["value"]["pretranslated_label"] == locale_specific_snippet_id
        assert block["value"]["custom_label"] == ""
        assert "label" not in block["value"]

    def test_already_converted_is_idempotent(self):
        block = _new_block(settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID)
        block_before_calling_method = deepcopy(block)
        assert convert_non_english_download_button_label(block, "tk-1", {}) is False
        assert block == block_before_calling_method


# ---------------------------------------------------------------------------
# Integration tests: command against real DB pages
# ---------------------------------------------------------------------------


def _call_migrate_download_button_labels(**kwargs):
    out = StringIO()
    call_command("migrate_download_button_labels", stdout=out, **kwargs)
    return out.getvalue()


def _download_blocks(page):
    """Reload page from DB and return raw dicts for all download_button blocks (at any depth)."""
    page.refresh_from_db()

    def _find(data):
        if isinstance(data, list):
            for item in data:
                yield from _find(item)
        elif isinstance(data, dict):
            if data.get("type") == "download_button":
                yield data
            else:
                for v in data.values():
                    if isinstance(v, (list, dict)):
                        yield from _find(v)

    return list(_find(list(page.content.raw_data)))


def _make_page(content, locale=None, slug="migration-test-page"):
    """Create a FreeFormPage under the site home with the given StreamField content."""
    parent = Page.objects.get(slug="home")
    page = FreeFormPage(slug=slug, title="Migration Test Page")
    if locale is not None:
        page.locale = locale
    parent.add_child(instance=page)
    page.content = content
    page.save_revision().publish()
    return page


@pytest.mark.django_db
class TestMigrateDownloadButtonLabelsCommand:
    def test_get_firefox_converted_to_snippet(self):
        page = _make_page([_intro_with_buttons(_old_block("Get Firefox"))])
        _call_migrate_download_button_labels()
        blocks = _download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID
        assert blocks[0]["value"]["custom_label"] == ""

    def test_download_firefox_converted_to_snippet(self):
        page = _make_page([_intro_with_buttons(_old_block("Download Firefox"))], slug="dl-test-page")
        _call_migrate_download_button_labels()
        blocks = _download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID

    def test_custom_text_becomes_custom_label(self):
        page = _make_page([_intro_with_buttons(_old_block("Try Firefox Now"))], slug="custom-test-page")
        _call_migrate_download_button_labels()
        blocks = _download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] is None
        assert blocks[0]["value"]["custom_label"] == "Try Firefox Now"

    def test_page_without_download_buttons_unchanged(self):
        page = _make_page([_intro_with_buttons()], slug="no-dl-test-page")
        _call_migrate_download_button_labels()
        page.refresh_from_db()
        raw = list(page.content.raw_data)
        assert len(raw) == 1
        assert raw[0]["type"] == "intro"
        assert _download_blocks(page) == []

    def test_idempotent(self):
        page = _make_page([_intro_with_buttons(_old_block("Get Firefox"))], slug="idem-test-page")
        _call_migrate_download_button_labels()
        first = [dict(b["value"]) for b in _download_blocks(page)]
        _call_migrate_download_button_labels()
        second = [dict(b["value"]) for b in _download_blocks(page)]
        assert first == second

    def test_dry_run_makes_no_changes(self):
        page = _make_page([_intro_with_buttons(_old_block("Get Firefox"))], slug="dryrun-test-page")
        _call_migrate_download_button_labels(dry_run=True)
        blocks = _download_blocks(page)
        assert "label" in blocks[0]["value"]
        assert "pretranslated_label" not in blocks[0]["value"]

    def test_non_english_page_becomes_custom_label_when_no_match(self):
        """Non-English pages with no matching ButtonLabelSnippet get custom_label."""
        fr_locale = LocaleFactory(language_code="fr")
        page = _make_page([_intro_with_buttons(_old_block("Télécharger Firefox"))], locale=fr_locale, slug="fr-test-page")
        _call_migrate_download_button_labels()
        blocks = _download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] is None
        assert blocks[0]["value"]["custom_label"] == "Télécharger Firefox"

    def test_non_english_page_uses_localized_label_map(self):
        """Non-English pages use ButtonLabelSnippet records to find the locale-specific snippet pk."""
        get_button_label_snippets()
        fr_locale = LocaleFactory(language_code="fr")
        en_snippet = ButtonLabelSnippet.objects.get(id=settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID)
        fr_snippet, _ = ButtonLabelSnippet.objects.update_or_create(
            locale=fr_locale,
            translation_key=en_snippet.translation_key,
            defaults={"key": en_snippet.key, "label": "Télécharger Firefox", "live": True},
        )
        page = _make_page([_intro_with_buttons(_old_block("Télécharger Firefox"))], locale=fr_locale, slug="fr-label-map-test-page")

        _call_migrate_download_button_labels()

        blocks = _download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == fr_snippet.pk
        assert blocks[0]["value"]["custom_label"] == ""

    def test_revision_is_also_converted(self):
        page = _make_page([_intro_with_buttons(_old_block("Get Firefox"))], slug="rev-test-page")
        _call_migrate_download_button_labels()

        ct = ContentType.objects.get_for_model(FreeFormPage)
        revision = Revision.objects.filter(content_type=ct, object_id=str(page.pk)).order_by("created_at").first()
        assert revision is not None

        raw_json = revision.content.get("content")
        assert raw_json is not None
        field_data = json.loads(raw_json)

        def _find_dl(data):
            if isinstance(data, list):
                for item in data:
                    yield from _find_dl(item)
            elif isinstance(data, dict):
                if data.get("type") == "download_button":
                    yield data
                else:
                    for v in data.values():
                        if isinstance(v, (list, dict)):
                            yield from _find_dl(v)

        dl_blocks = list(_find_dl(field_data))
        assert len(dl_blocks) == 1
        assert "label" not in dl_blocks[0]["value"]
        assert dl_blocks[0]["value"]["pretranslated_label"] == settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID
