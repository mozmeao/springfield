# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from copy import deepcopy
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

import pytest
from wagtail.models import Page, Revision

from springfield.cms.fixtures.snippet_fixtures import get_pretranslated_phrase_snippets
from springfield.cms.management.commands.migrate_download_button_labels import (
    convert_download_button_label,
)
from springfield.cms.models import FreeFormPage2026, PretranslatedPhrase
from springfield.cms.tests.factories import LocaleFactory

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

BLOCK_SETTINGS = {
    "theme": "",
    "icon": "",
    "icon_position": "right",
    "analytics_id": "00000000-0000-0000-0000-000000000001",
    "show_default_browser_checkbox": False,
}

EN_US_LOCALE_ID = 1
EN_CA_LOCALE_ID = 2
LABEL_MAP = {
    (EN_US_LOCALE_ID, "Get Firefox"): 1001,
    (EN_US_LOCALE_ID, "Download Firefox"): 1002,
    (EN_CA_LOCALE_ID, "Get Firefox"): 2001,
    (EN_CA_LOCALE_ID, "Download Firefox"): 2002,
}


def get_old_block(label, block_id="aaaaaaaa-0000-0000-0000-000000000001"):
    """Old-format download_button block: has 'label', no pretranslated_label."""
    return {
        "type": "download_button",
        "id": block_id,
        "value": {"label": label, "settings": BLOCK_SETTINGS},
    }


def get_new_block(pretranslated_id, custom_label="", block_id="aaaaaaaa-0000-0000-0000-000000000001"):
    """New-format download_button block: has pretranslated_label, no 'label'."""
    return {
        "type": "download_button",
        "id": block_id,
        "value": {"pretranslated_label": pretranslated_id, "custom_label": custom_label, "settings": BLOCK_SETTINGS},
    }


def get_intro_with_buttons(*download_blocks, intro_id="cc000000-0000-0000-0000-000000000000"):
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
# Unit tests for the pure conversion functions (no database)
# ---------------------------------------------------------------------------


def test_get_firefox_maps_to_snippet_id():
    block = get_old_block("Get Firefox")
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")]
    assert block["value"]["custom_label"] == ""
    assert "label" not in block["value"]


def test_download_firefox_maps_to_snippet_id():
    block = get_old_block("Download Firefox")
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Download Firefox")]
    assert block["value"]["custom_label"] == ""
    assert "label" not in block["value"]


def test_unknown_text_becomes_custom_label():
    block = get_old_block("Try Firefox Now")
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] is None
    assert block["value"]["custom_label"] == "Try Firefox Now"
    assert "label" not in block["value"]


def test_label_in_different_locale_that_has_no_snippets_becomes_custom_label():
    """A locale with no PretranslatedPhrase entries falls back to custom_label, even when another locale has a matching label."""
    locale_id_with_no_snippets = max({locale_id for locale_id, _ in LABEL_MAP}) + 1
    assert not any(locale_id == locale_id_with_no_snippets for locale_id, _ in LABEL_MAP)

    block = get_old_block("Get Firefox")

    assert convert_download_button_label(data=block, locale_id=locale_id_with_no_snippets, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] is None
    assert block["value"]["custom_label"] == "Get Firefox"


def test_get_firefox_maps_to_en_ca_snippet_for_en_ca_locale():
    """A page in en-CA referencing 'Get Firefox' must wire to en-CA's snippet, not en-US's — same label text, different locale."""
    block = get_old_block("Get Firefox")
    assert convert_download_button_label(data=block, locale_id=EN_CA_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_CA_LOCALE_ID, "Get Firefox")]
    assert block["value"]["pretranslated_label"] != LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")]
    assert block["value"]["custom_label"] == ""


def test_download_firefox_maps_to_en_ca_snippet_for_en_ca_locale():
    """A page in en-CA referencing 'Download Firefox' must wire to en-CA's snippet, not en-US's."""
    block = get_old_block("Download Firefox")
    assert convert_download_button_label(data=block, locale_id=EN_CA_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_CA_LOCALE_ID, "Download Firefox")]
    assert block["value"]["pretranslated_label"] != LABEL_MAP[(EN_US_LOCALE_ID, "Download Firefox")]
    assert block["value"]["custom_label"] == ""


def test_already_converted_block_is_idempotent():
    block = get_new_block(LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")])

    # Call the function.
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is False
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")]

    # Call the function again.
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is False
    assert block["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")]


def test_already_converted_block_is_idempotent_for_locale_without_snippets():
    """Idempotency holds even when the page's locale has no entries in the label_map."""
    locale_id_with_no_snippets = max({locale_id for locale_id, _ in LABEL_MAP}) + 1
    block = get_new_block(1001)
    block_before = deepcopy(block)
    assert convert_download_button_label(data=block, locale_id=locale_id_with_no_snippets, label_map=LABEL_MAP) is False
    assert block == block_before


def test_recurses_into_list():
    """Top-level list (StreamField raw_data) is walked recursively."""
    data = [get_old_block("Get Firefox")]
    assert convert_download_button_label(data=data, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert data[0]["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Get Firefox")]


def test_recurses_into_nested_dict():
    """download_button nested inside another block (e.g. intro.buttons) is converted."""
    data = {
        "type": "intro",
        "id": "intro-id",
        "value": {"buttons": [get_old_block("Download Firefox")]},
    }
    assert convert_download_button_label(data=data, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert data["value"]["buttons"][0]["value"]["pretranslated_label"] == LABEL_MAP[(EN_US_LOCALE_ID, "Download Firefox")]


def test_non_download_block_is_untouched():
    block = {"type": "paragraph", "id": "p-id", "value": "Hello"}
    old_block = deepcopy(block)
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is False
    assert block == old_block


def test_no_match_for_locale_becomes_custom_label():
    block = get_old_block("Descargar Firefox", block_id="block-xyz")
    assert convert_download_button_label(data=block, locale_id=EN_US_LOCALE_ID, label_map=LABEL_MAP) is True
    assert block["value"]["pretranslated_label"] is None
    assert block["value"]["custom_label"] == "Descargar Firefox"
    assert "label" not in block["value"]


# ---------------------------------------------------------------------------
# Integration tests: command against real DB pages
# ---------------------------------------------------------------------------


def call_migrate_download_button_labels(**kwargs):
    out = StringIO()
    call_command("migrate_download_button_labels", stdout=out, **kwargs)
    return out.getvalue()


def find_download_blocks(page):
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


def make_page(content, locale=None, slug="migration-test-page"):
    """Create a FreeFormPage under the site home with the given StreamField content."""
    parent = Page.objects.get(slug="home")
    page = FreeFormPage2026(slug=slug, title="Migration Test Page")
    if locale is not None:
        page.locale = locale
    parent.add_child(instance=page)
    page.content = content
    page.save_revision().publish()
    return page


@pytest.mark.django_db
class TestMigrateDownloadButtonLabelsCommand:
    def test_get_firefox_converted_to_snippet(self):
        get_firefox, _ = get_pretranslated_phrase_snippets()
        page = make_page([get_intro_with_buttons(get_old_block("Get Firefox"))])
        call_migrate_download_button_labels()
        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == get_firefox.pk
        assert blocks[0]["value"]["custom_label"] == ""

    def test_download_firefox_converted_to_snippet(self):
        _, download_firefox = get_pretranslated_phrase_snippets()
        page = make_page([get_intro_with_buttons(get_old_block("Download Firefox"))], slug="dl-test-page")
        call_migrate_download_button_labels()
        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == download_firefox.pk

    def test_custom_text_becomes_custom_label(self):
        page = make_page([get_intro_with_buttons(get_old_block("Try Firefox Now"))], slug="custom-test-page")
        call_migrate_download_button_labels()
        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] is None
        assert blocks[0]["value"]["custom_label"] == "Try Firefox Now"

    def test_page_without_download_buttons_unchanged(self):
        page = make_page([get_intro_with_buttons()], slug="no-dl-test-page")
        call_migrate_download_button_labels()
        page.refresh_from_db()
        raw = list(page.content.raw_data)
        assert len(raw) == 1
        assert raw[0]["type"] == "intro"
        assert find_download_blocks(page) == []

    def test_idempotent(self):
        get_pretranslated_phrase_snippets()
        page = make_page([get_intro_with_buttons(get_old_block("Get Firefox"))], slug="idem-test-page")
        call_migrate_download_button_labels()
        first = [dict(b["value"]) for b in find_download_blocks(page)]
        call_migrate_download_button_labels()
        second = [dict(b["value"]) for b in find_download_blocks(page)]
        assert first == second

    def test_dry_run_makes_no_changes(self):
        page = make_page([get_intro_with_buttons(get_old_block("Get Firefox"))], slug="dryrun-test-page")
        call_migrate_download_button_labels(dry_run=True)
        blocks = find_download_blocks(page)
        assert "label" in blocks[0]["value"]
        assert "pretranslated_label" not in blocks[0]["value"]

    def test_non_english_page_becomes_custom_label_when_no_match(self):
        """Non-English pages with no matching PretranslatedPhrase get custom_label."""
        fr_locale = LocaleFactory(language_code="fr")
        page = make_page([get_intro_with_buttons(get_old_block("Télécharger Firefox"))], locale=fr_locale, slug="fr-test-page")
        call_migrate_download_button_labels()
        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] is None
        assert blocks[0]["value"]["custom_label"] == "Télécharger Firefox"

    def test_non_english_page_uses_localized_LABEL_MAP(self):
        """Non-English pages use PretranslatedPhrase records to find the locale-specific snippet pk."""
        _, download_firefox = get_pretranslated_phrase_snippets()
        fr_locale = LocaleFactory(language_code="fr")
        fr_snippet, _ = PretranslatedPhrase.objects.update_or_create(
            locale=fr_locale,
            translation_key=download_firefox.translation_key,
            defaults={"label": "Télécharger Firefox", "live": True},
        )
        page = make_page([get_intro_with_buttons(get_old_block("Télécharger Firefox"))], locale=fr_locale, slug="fr-label-map-test-page")

        call_migrate_download_button_labels()

        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert "label" not in blocks[0]["value"]
        assert blocks[0]["value"]["pretranslated_label"] == fr_snippet.pk
        assert blocks[0]["value"]["custom_label"] == ""

    def test_english_page_uses_its_own_locales_snippet(self):
        """An en-US page must reference the en-US snippet, not another English locale's snippet.

        Each English locale (en-US, en-GB, en-CA, …) has its own PretranslatedPhrase record
        sharing identical label text. The migration must wire each page to its own locale's
        snippet (wagtail-localize convention), not collapse all English locales together.
        """
        get_firefox_us, _ = get_pretranslated_phrase_snippets()  # en-US (default)
        en_ca = LocaleFactory(language_code="en-CA")
        get_firefox_ca, _ = PretranslatedPhrase.objects.update_or_create(
            locale=en_ca,
            translation_key=get_firefox_us.translation_key,
            defaults={"label": "Get Firefox", "live": True},
        )

        page = make_page([get_intro_with_buttons(get_old_block("Get Firefox"))], slug="us-page")
        assert page.locale.language_code == "en-US"

        call_migrate_download_button_labels()

        blocks = find_download_blocks(page)
        assert len(blocks) == 1
        assert blocks[0]["value"]["pretranslated_label"] == get_firefox_us.pk
        assert blocks[0]["value"]["pretranslated_label"] != get_firefox_ca.pk

    def test_revision_is_also_converted(self):
        get_firefox, _ = get_pretranslated_phrase_snippets()
        page = make_page([get_intro_with_buttons(get_old_block("Get Firefox"))], slug="rev-test-page")
        call_migrate_download_button_labels()

        ct = ContentType.objects.get_for_model(FreeFormPage2026)
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
        assert dl_blocks[0]["value"]["pretranslated_label"] == get_firefox.pk
