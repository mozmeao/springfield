# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Data migration to move label data from label_old to the new
# FluentOrCustomTextBlock format (pretranslated_or_custom + custom_text)
# for DownloadFirefoxButtonBlock, and from label_old to
# pretranslated_label + custom_label for PreFooterCTASnippet.

import json
import logging
from collections.abc import MutableSequence

from django.db import migrations

logger = logging.getLogger(__name__)

# Inline constants — not imported from blocks.py so the migration is stable.
# These use fluent IDs from globally-loaded FTL files (navigation-firefox.ftl,
# download_button.ftl) so translations already exist in all locales.
LABEL_TO_PRESET = {
    "Get Firefox": "navigation-get-firefox",
    "Download Firefox": "download-button-download-firefox",
}
DEFAULT_PRESET = "download-button-download-firefox"

PAGE_MODELS_AND_FIELDS = [
    ("HomePage", ["upper_content", "lower_content"]),
    ("DownloadPage", ["content"]),
    ("ThanksPage", ["content"]),
    ("ArticleThemePage", ["upper_content", "content"]),
    ("FreeFormPage", ["content"]),
    ("FreeFormPage2026", ["upper_content", "content"]),
    ("WhatsNewPage", ["content"]),
]

PAGE_MODEL_NAMES = [name for name, _ in PAGE_MODELS_AND_FIELDS]


def migrate_snippets(apps, schema_editor):
    PreFooterCTASnippet = apps.get_model("cms", "PreFooterCTASnippet")

    # Pass 1: Migrate English snippets using text matching.
    for snippet in PreFooterCTASnippet.objects.filter(locale__language_code__startswith="en"):
        preset = LABEL_TO_PRESET.get(snippet.label_old)
        if preset:
            snippet.pretranslated_label = preset
            snippet.custom_label = ""
        else:
            snippet.pretranslated_label = "custom"
            snippet.custom_label = snippet.label_old
            logger.info(
                "PreFooterCTASnippet pk=%s has custom label_old=%r, keeping as custom text",
                snippet.pk,
                snippet.label_old,
            )
        snippet.save(update_fields=["pretranslated_label", "custom_label"])

    # Pass 2: Migrate non-English snippets by copying the English sibling's preset.
    for snippet in PreFooterCTASnippet.objects.exclude(locale__language_code__startswith="en"):
        english_sibling = PreFooterCTASnippet.objects.filter(
            translation_key=snippet.translation_key,
            locale__language_code__startswith="en",
        ).first()
        if english_sibling and english_sibling.pretranslated_label:
            snippet.pretranslated_label = english_sibling.pretranslated_label
            if english_sibling.pretranslated_label == "custom":
                # Preserve the non-English translated label as custom text.
                snippet.custom_label = snippet.label_old
            else:
                snippet.custom_label = ""
        else:
            logger.warning(
                "PreFooterCTASnippet pk=%s (locale=%s) has no English sibling, defaulting to %s",
                snippet.pk,
                snippet.locale.language_code,
                DEFAULT_PRESET,
            )
            snippet.pretranslated_label = DEFAULT_PRESET
            snippet.custom_label = ""
        snippet.save(update_fields=["pretranslated_label", "custom_label"])


def convert_download_button_label(data, is_english=True):
    """Recursively convert label in download_button blocks. Returns True if any change was made.

    For English pages, matches label text to a fluent preset; unrecognised
    labels are kept as custom text.  For non-English pages, the translated
    label text is not useful (fluent handles it), so we always use
    DEFAULT_PRESET.
    """
    changed = False
    if isinstance(data, dict):
        if data.get("type") == "download_button" and isinstance(data.get("value"), dict):
            value = data["value"]
            old_label = value.get("label")
            if isinstance(old_label, str):
                if is_english:
                    preset = LABEL_TO_PRESET.get(old_label)
                    if preset:
                        value["label"] = {"pretranslated_or_custom": preset, "custom_text": ""}
                    else:
                        value["label"] = {"pretranslated_or_custom": "custom", "custom_text": old_label}
                else:
                    value["label"] = {"pretranslated_or_custom": DEFAULT_PRESET, "custom_text": ""}
                changed = True
        for v in list(data.values()):
            if convert_download_button_label(v, is_english=is_english):
                changed = True
    elif isinstance(data, (list, MutableSequence)):
        for item in data:
            if convert_download_button_label(item, is_english=is_english):
                changed = True
    return changed


def convert_pages(apps, schema_editor):
    for model_name, field_names in PAGE_MODELS_AND_FIELDS:
        Model = apps.get_model("cms", model_name)
        for page in Model.objects.all():
            is_english = page.locale.language_code.startswith("en")
            changed_fields = []
            for field_name in field_names:
                stream_value = getattr(page, field_name)
                if stream_value and convert_download_button_label(stream_value.raw_data, is_english=is_english):
                    changed_fields.append(field_name)
            if changed_fields:
                page.save(update_fields=changed_fields)


def convert_revisions(apps, schema_editor):
    """Update Wagtail page revisions to use the new label format."""
    try:
        Revision = apps.get_model("wagtailcore", "Revision")
    except LookupError:
        return

    from django.contrib.contenttypes.models import ContentType

    Locale = apps.get_model("wagtailcore", "Locale")
    english_locale_ids = set(Locale.objects.filter(language_code__startswith="en").values_list("pk", flat=True))

    page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
    content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]

    field_names = ["content", "upper_content", "lower_content"]

    for revision in Revision.objects.filter(content_type_id__in=content_type_ids).iterator():
        locale_id = revision.content.get("locale")
        is_english = locale_id in english_locale_ids if locale_id else True
        modified = False
        for field_name in field_names:
            raw_json = revision.content.get(field_name)
            if not raw_json:
                continue
            try:
                field_data = json.loads(raw_json)
                if convert_download_button_label(field_data, is_english=is_english):
                    revision.content[field_name] = json.dumps(field_data)
                    modified = True
            except (json.JSONDecodeError, TypeError):
                pass
        if modified:
            revision.save(update_fields=["content"])


def update_translation_sources(apps, schema_editor):
    """Re-sync TranslationSource records so wagtail-localize sees the new block structure."""
    try:
        from wagtail_localize.models import TranslationSource
    except ImportError:
        return

    from django.contrib.contenttypes.models import ContentType

    page_models = [apps.get_model("cms", name) for name in PAGE_MODEL_NAMES]
    content_type_ids = [ContentType.objects.get_for_model(m).pk for m in page_models]

    for source in TranslationSource.objects.filter(specific_content_type_id__in=content_type_ids):
        try:
            source.update_from_db()
        except Exception:
            logger.warning("Failed to update TranslationSource pk=%s", source.pk, exc_info=True)


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0057_prefootercta_pretranslated_label"),
    ]

    operations = [
        migrations.RunPython(migrate_snippets, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(convert_pages, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(convert_revisions, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(update_translation_sources, reverse_code=migrations.RunPython.noop),
    ]
