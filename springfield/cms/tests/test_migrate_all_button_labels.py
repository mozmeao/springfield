# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

import pytest
from wagtail.models import Locale, Page, Revision
from wagtail_localize.models import (
    String,
    StringTranslation,
    TranslatableObject,
    TranslationContext,
    TranslationSource,
)
from wagtail_localize.strings import StringValue

from springfield.cms.blocks import (
    BUTTON_TYPE,
    DOWNLOAD_BUTTON_TYPE,
    FOCUS_BUTTON_TYPE,
    FXA_BUTTON_TYPE,
    SET_AS_DEFAULT_BUTTON,
    UITOUR_BUTTON_TYPE,
)
from springfield.cms.fixtures.snippet_fixtures import get_pretranslated_phrase_snippets
from springfield.cms.management.commands.migrate_all_button_labels import (
    BUTTON_TYPES_WITH_LABEL,
    convert_button_label,
)
from springfield.cms.models import BannerSnippet, FreeFormPage
from springfield.cms.tests.factories import LocaleFactory

# ---------------------------------------------------------------------------
# Shared test data / helpers
# ---------------------------------------------------------------------------

_SETTINGS = {
    "theme": "",
    "icon": "",
    "icon_position": "right",
    "analytics_id": "00000000-0000-0000-0000-000000000001",
}

_LINK = {
    "link_to": "custom_url",
    "page": None,
    "file": None,
    "custom_url": "https://mozilla.org",
    "anchor": "",
    "email": "",
    "phone": "",
    "new_window": False,
    "relative_url": "",
}

# distinct, stable block ids per type (wagtail_localize requires stable string ids)
_BLOCK_IDS = {
    BUTTON_TYPE: "bbbbbbbb-0000-0000-0000-000000000001",
    UITOUR_BUTTON_TYPE: "bbbbbbbb-0000-0000-0000-000000000002",
    FXA_BUTTON_TYPE: "bbbbbbbb-0000-0000-0000-000000000003",
    SET_AS_DEFAULT_BUTTON: "bbbbbbbb-0000-0000-0000-000000000004",
    FOCUS_BUTTON_TYPE: "bbbbbbbb-0000-0000-0000-000000000005",
    DOWNLOAD_BUTTON_TYPE: "bbbbbbbb-0000-0000-0000-000000000006",
}


def _old_button(btn_type, label, block_id=None):
    """
    An old-format button block: has 'label', no pretranslated_label/custom_label.

    The inner value only needs ``label`` + ``settings`` for the converter; the
    block-specific children (link/store/button_type/snippet) are irrelevant to the
    conversion, which keys solely off ``type`` and ``value['label']``.
    """
    value = {"label": label, "settings": dict(_SETTINGS)}
    if btn_type == BUTTON_TYPE:
        value["link"] = dict(_LINK)
    return {
        "type": btn_type,
        "id": block_id or _BLOCK_IDS[btn_type],
        "value": value,
    }


def _new_button(btn_type, custom_label, block_id=None):
    """A converted (new-format) button block: pretranslated_label/custom_label, no 'label'."""
    value = {"pretranslated_label": None, "custom_label": custom_label, "settings": dict(_SETTINGS)}
    if btn_type == BUTTON_TYPE:
        value["link"] = dict(_LINK)
    return {
        "type": btn_type,
        "id": block_id or _BLOCK_IDS[btn_type],
        "value": value,
    }


def _intro_with_buttons(*button_blocks, intro_id="cc000000-0000-0000-0000-000000000000"):
    """Wrap button blocks in a valid IntroBlock so FreeFormPage.content accepts them."""
    return {
        "type": "intro",
        "id": intro_id,
        "value": {
            "settings": {"media_position": "after", "anchor_id": ""},
            "media": [],
            "heading": {"superheading_text": "", "heading_text": "<p>Test</p>", "subheading_text": ""},
            "buttons": list(button_blocks),
        },
    }


def _make_page(content, locale=None, slug="all-buttons-migration-test"):
    """Create a FreeFormPage under the site home with the given StreamField content."""
    parent = Page.objects.get(slug="home")
    page = FreeFormPage(slug=slug, title="All Buttons Migration Test")
    if locale is not None:
        page.locale = locale
    parent.add_child(instance=page)
    page.content = content
    page.save_revision().publish()
    return page


def _buttons_in(raw_data):
    """Yield every button-type block dict (any depth) from raw StreamField data."""

    def _walk(data):
        if isinstance(data, list):
            for item in data:
                yield from _walk(item)
        elif isinstance(data, dict):
            if data.get("type") in BUTTON_TYPES_WITH_LABEL | {DOWNLOAD_BUTTON_TYPE}:
                yield data
            for v in data.values():
                if isinstance(v, (list, dict)):
                    yield from _walk(v)

    return list(_walk(raw_data))


def _page_buttons(page):
    page.refresh_from_db()
    return _buttons_in(list(page.content.raw_data))


def _call_migrate_all_button_labels(**kwargs):
    out = StringIO()
    call_command("migrate_all_button_labels", stdout=out, **kwargs)
    return out.getvalue()


def test_button_types_with_label_matches_registered_constants():
    """Verify that the management command matches the expected button types exactly."""
    assert BUTTON_TYPES_WITH_LABEL == {
        BUTTON_TYPE,
        UITOUR_BUTTON_TYPE,
        FXA_BUTTON_TYPE,
        SET_AS_DEFAULT_BUTTON,
        FOCUS_BUTTON_TYPE,
    }
    assert DOWNLOAD_BUTTON_TYPE not in BUTTON_TYPES_WITH_LABEL


class TestConvertButtonLabel:
    def test_custom_text_becomes_custom_label(self):
        block = _old_button(BUTTON_TYPE, "Learn more")
        assert convert_button_label(block) is True
        assert "label" not in block["value"]
        assert block["value"]["pretranslated_label"] is None
        assert block["value"]["custom_label"] == "Learn more"

    def test_seeded_phrase_text_still_becomes_custom_label(self):
        """A button label that matches an existing PretranslatedPhrase still becomes custom_label."""
        block = _old_button(BUTTON_TYPE, "Get Firefox")
        assert convert_button_label(block) is True
        assert "label" not in block["value"]
        assert block["value"]["pretranslated_label"] is None
        assert block["value"]["custom_label"] == "Get Firefox"

    @pytest.mark.parametrize(
        "btn_type",
        [BUTTON_TYPE, UITOUR_BUTTON_TYPE, FXA_BUTTON_TYPE, SET_AS_DEFAULT_BUTTON, FOCUS_BUTTON_TYPE],
    )
    def test_every_non_download_type_is_converted(self, btn_type):
        block = _old_button(btn_type, "Some text")
        assert convert_button_label(block) is True
        assert "label" not in block["value"]
        assert block["value"]["custom_label"] == "Some text"

    def test_download_button_is_left_untouched(self):
        """download_button is owned by the shipped 0099 command; this converter skips it."""
        block = _old_button(DOWNLOAD_BUTTON_TYPE, "Download Firefox")
        assert convert_button_label(block) is False
        assert block["value"]["label"] == "Download Firefox"
        assert "custom_label" not in block["value"]

    def test_already_converted_block_is_idempotent(self):
        """A converted block has no 'label' key, so the guard skips it."""
        block = {
            "type": BUTTON_TYPE,
            "id": _BLOCK_IDS[BUTTON_TYPE],
            "value": {"pretranslated_label": None, "custom_label": "Learn more", "settings": dict(_SETTINGS)},
        }
        assert convert_button_label(block) is False
        assert block["value"]["custom_label"] == "Learn more"

    def test_recurses_into_nested_lists_and_dicts(self):
        data = _intro_with_buttons(_old_button(BUTTON_TYPE, "Label A"), _old_button(FXA_BUTTON_TYPE, "Label B"))
        assert convert_button_label(data) is True
        buttons = _buttons_in(data)
        assert {b["value"]["custom_label"] for b in buttons} == {"Label A", "Label B"}
        assert all("label" not in b["value"] for b in buttons)

    def test_non_button_blocks_untouched(self):
        data = {"type": "intro", "id": "x", "value": {"heading": "hi"}}
        assert convert_button_label(data) is False


@pytest.mark.django_db
class TestMigrateNonDownloadButtonLabels:
    @pytest.mark.parametrize(
        "btn_type",
        [BUTTON_TYPE, UITOUR_BUTTON_TYPE, FXA_BUTTON_TYPE, SET_AS_DEFAULT_BUTTON, FOCUS_BUTTON_TYPE],
    )
    def test_old_label_becomes_custom_label(self, btn_type):
        page = _make_page([_intro_with_buttons(_old_button(btn_type, "Some text"))], slug=f"conv-{btn_type}")
        _call_migrate_all_button_labels()
        buttons = _page_buttons(page)
        assert len(buttons) == 1
        assert "label" not in buttons[0]["value"]
        assert buttons[0]["value"]["pretranslated_label"] is None
        assert buttons[0]["value"]["custom_label"] == "Some text"

    def test_seeded_phrase_text_is_not_linked_to_snippet(self):
        """A button label that matches an existing PretranslatedPhrase still becomes custom_label."""
        get_pretranslated_phrase_snippets()  # creates "Get Firefox" / "Download Firefox"
        page = _make_page([_intro_with_buttons(_old_button(BUTTON_TYPE, "Get Firefox"))], slug="conv-nolookup")
        _call_migrate_all_button_labels()
        buttons = _page_buttons(page)
        assert buttons[0]["value"]["pretranslated_label"] is None
        assert buttons[0]["value"]["custom_label"] == "Get Firefox"

    def test_idempotent(self):
        page = _make_page([_intro_with_buttons(_old_button(BUTTON_TYPE, "Learn more"))], slug="conv-idem")
        _call_migrate_all_button_labels()
        first = [dict(b["value"]) for b in _page_buttons(page)]
        _call_migrate_all_button_labels()
        second = [dict(b["value"]) for b in _page_buttons(page)]
        assert first == second

    def test_dry_run_makes_no_changes(self):
        page = _make_page([_intro_with_buttons(_old_button(BUTTON_TYPE, "Learn more"))], slug="conv-dryrun")
        _call_migrate_all_button_labels(dry_run=True)
        buttons = _page_buttons(page)
        assert "label" in buttons[0]["value"]
        assert "custom_label" not in buttons[0]["value"]

    def test_download_button_on_page_is_untouched(self):
        """
        Verify that the command does NOT change download buttons.

        Download buttons should already have been changed by an earlier run of
        a different command, so we do not touch them here.
        """
        page = _make_page([_intro_with_buttons(_old_button(DOWNLOAD_BUTTON_TYPE, "Download Firefox"))], slug="conv-dl-untouched")
        _call_migrate_all_button_labels()
        buttons = _page_buttons(page)
        assert buttons[0]["value"]["label"] == "Download Firefox"
        assert "custom_label" not in buttons[0]["value"]


@pytest.mark.django_db
class TestMigratePageRevisionButtons:
    def test_page_revision_is_converted(self):
        page = _make_page([_intro_with_buttons(_old_button(BUTTON_TYPE, "Learn more"))], slug="conv-rev")
        _call_migrate_all_button_labels()

        ct = ContentType.objects.get_for_model(FreeFormPage)
        revision = Revision.objects.filter(content_type=ct, object_id=str(page.pk)).order_by("created_at").first()
        assert revision is not None

        field_data = json.loads(revision.content["content"])
        buttons = _buttons_in(field_data)
        assert len(buttons) == 1
        assert "label" not in buttons[0]["value"]
        assert buttons[0]["value"]["custom_label"] == "Learn more"


@pytest.mark.django_db
class TestMigrateBannerSnippetButtons:
    def _make_banner(self, locale=None, label="Learn more"):
        banner = BannerSnippet(
            heading="Banner heading",
            content="<p>Banner content</p>",
        )
        if locale is not None:
            banner.locale = locale
        banner.buttons = [_old_button(BUTTON_TYPE, label)]
        banner.save()
        return banner

    def test_live_row_is_converted(self):
        banner = self._make_banner()
        _call_migrate_all_button_labels()
        banner.refresh_from_db()
        buttons = _buttons_in(list(banner.buttons.raw_data))
        assert len(buttons) == 1
        assert "label" not in buttons[0]["value"]
        assert buttons[0]["value"]["custom_label"] == "Learn more"

    def test_snippet_revision_is_converted(self):
        banner = self._make_banner()
        banner.save_revision()
        _call_migrate_all_button_labels()

        ct = ContentType.objects.get_for_model(BannerSnippet)
        revision = Revision.objects.filter(content_type=ct, object_id=str(banner.pk)).order_by("created_at").first()
        assert revision is not None

        field_data = json.loads(revision.content["buttons"])
        buttons = _buttons_in(field_data)
        assert len(buttons) == 1
        assert "label" not in buttons[0]["value"]
        assert buttons[0]["value"]["custom_label"] == "Learn more"


@pytest.mark.django_db
class TestMigrateTranslatedSnippetSourceSync:
    def test_translation_source_sync_does_not_raise_and_reflects_new_field_name(self):
        """§8.2 (local half): _update_translation_sources includes snippet sources and
        runs update_from_db over them without raising, leaving the source's serialized
        content in the new shape.

        The source is built from a NEW-shape snippet on purpose. In production the
        source predates the deploy (created under old code), and the migration's
        update_from_db re-extracts from the already-converted (new-shape) row — which
        is the state modelled here. Creating a source from OLD-shape data under the new
        block definition raises during wagtail-localize segment extraction (custom_label
        reads as None), but that's an artificial sequence that never occurs in production.
        """
        fr_locale = LocaleFactory(language_code="fr")
        banner = BannerSnippet(heading="Banner heading", content="<p>Banner content</p>")
        banner.buttons = [_new_button(BUTTON_TYPE, "Learn more")]
        banner.save()
        banner.copy_for_translation(fr_locale)
        TranslationSource.get_or_create_from_instance(banner)

        # Must complete without raising — the command's _update_translation_sources
        # walks the BannerSnippet content type and calls update_from_db on its source.
        _call_migrate_all_button_labels()

        source = TranslationSource.objects.get(
            object_id=banner.translation_key,
            specific_content_type=ContentType.objects.get_for_model(BannerSnippet),
        )
        # content_json is a JSON string with the buttons StreamField nested as an
        # escaped JSON string, so assert on substrings rather than exact key/value text.
        content = source.content_json
        assert "custom_label" in content
        assert "Learn more" in content


@pytest.mark.django_db
class TestMigrateRelinkButtonTranslations:
    """
    Verify that the migration allows button translations to persist.

    The label -> custom_label rename re-paths the wagtail-localize segment, orphaning
    existing StringTranslations at the old `…<block_id>.label` context.
    The management command re-links them to the new `…<block_id>.custom_label` context,
    so the translation editor and preview still see them.
    """

    def test_relinks_label_translations_to_custom_label(self):
        en = Locale.get_default()
        fr = LocaleFactory(language_code="fr")

        banner = BannerSnippet(heading="H", content="<p>c</p>")
        banner.buttons = [_new_button(BUTTON_TYPE, "Learn more")]
        banner.save()
        obj, _ = TranslatableObject.objects.get_or_create_from_instance(banner)

        # Simulate the pre-migration state: a translation at the old `.label`
        # context, with the new `.custom_label` context present but empty.
        source_string = String.from_value(en, StringValue.from_plaintext("Learn more"))
        base = f"buttons.{_BLOCK_IDS[BUTTON_TYPE]}"
        old_ctx = TranslationContext.objects.create(object=obj, path=f"{base}.label", field_path=f"{base}.label")
        new_ctx = TranslationContext.objects.create(object=obj, path=f"{base}.custom_label", field_path=f"{base}.custom_label")
        StringTranslation.objects.create(translation_of=source_string, locale=fr, context=old_ctx, data="Apprends-en plus", translation_type="manual")

        _call_migrate_all_button_labels()

        # Assert that the translation was re-linked to the new (custom_label field) context.
        copied = StringTranslation.objects.filter(context=new_ctx, locale=fr).first()
        assert copied is not None, "translation was not re-linked to the custom_label context"
        assert copied.data == "Apprends-en plus"
        assert copied.translation_of_id == source_string.id

    def test_relink_does_not_touch_label_without_custom_label_sibling(self):
        """
        A plain .label segment that is NOT a button (no `.custom_label` sibling) must be left alone.
        """
        en = Locale.get_default()
        fr = LocaleFactory(language_code="fr")

        banner = BannerSnippet(heading="H", content="<p>c</p>")
        banner.buttons = [_new_button(BUTTON_TYPE, "Learn more")]
        banner.save()
        obj, _ = TranslatableObject.objects.get_or_create_from_instance(banner)

        s = String.from_value(en, StringValue.from_plaintext("Link text"))
        link_ctx = TranslationContext.objects.create(object=obj, path="buttons.X.link.label", field_path="buttons.X.link.label")
        StringTranslation.objects.create(translation_of=s, locale=fr, context=link_ctx, data="Texte du lien", translation_type="manual")

        _call_migrate_all_button_labels()

        # No `.custom_label` sibling exists, so nothing new is created for this string.
        assert StringTranslation.objects.filter(translation_of=s, locale=fr).count() == 1
