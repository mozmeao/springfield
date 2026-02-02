# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Data migration to create feature pages and import FTL translations.

This migration:
1. Creates the Firefox Features index page (ArticleIndexPage)
2. Creates all feature detail pages (ArticleDetailPage) with content matching FTL source strings
3. Creates TranslationSource records and segments for each page
4. Imports FTL translations for all configured target locales
"""

import re

from django.db import migrations

# Mapping of page slugs to FTL files
PAGE_FTL_MAPPING = {
    "fast": "fast-2024.ftl",
    "block-fingerprinting": "fingerprinting.ftl",
    "private": "private-2023.ftl",
    "add-ons": "add-ons-2023.ftl",
    "customize": "customize-2023.ftl",
    "private-browsing": "private-browsing-2023.ftl",
    "bookmarks": "bookmarks-2023.ftl",
    "sync": "sync-2023.ftl",
    "password-manager": "password-manager-2023.ftl",
    "picture-in-picture": "picture-in-picture.ftl",
    "translate": "translate.ftl",
    "adblocker": "adblocker-2025.ftl",
    "pdf-editor": "pdf-editor-2023.ftl",
    "eyedropper": "eyedropper-2023.ftl",
    "pinned-tabs": "pinned-tabs-2023.ftl",
}


def create_feature_pages(apps, schema_editor):
    """Create feature pages using fixture data."""
    # Import here to avoid issues with app registry not being ready
    from springfield.cms.fixtures.feature_page_fixtures import load_feature_page_fixtures

    index_page, feature_pages = load_feature_page_fixtures()
    print(f"\n  Created feature index page: {index_page.slug}")
    print(f"  Created {len(feature_pages)} feature pages")


def create_translation_sources(apps, schema_editor):
    """Create TranslationSource records and segments for feature pages."""
    from wagtail.models import Locale
    from wagtail_localize.models import TranslationSource

    from springfield.cms.models import ArticleDetailPage, ArticleIndexPage

    source_locale = Locale.objects.get(language_code="en-US")

    # Create TranslationSource for the index page
    index_page = ArticleIndexPage.objects.get(slug="features", locale=source_locale)
    source, created = TranslationSource.get_or_create_from_instance(index_page)
    if created:
        print(f"\n  Created TranslationSource for index page: {index_page.slug}")
    else:
        source.refresh_segments()
        print(f"\n  Refreshed segments for index page: {index_page.slug}")

    # Create TranslationSource for each feature page
    for slug in PAGE_FTL_MAPPING.keys():
        page = ArticleDetailPage.objects.get(slug=slug, locale=source_locale)
        source, created = TranslationSource.get_or_create_from_instance(page)
        if created:
            print(f"  Created TranslationSource for: {slug}")
        else:
            source.refresh_segments()
            print(f"  Refreshed segments for: {slug}")


def import_ftl_translations(apps, schema_editor):
    """Import FTL translations for all feature pages and locales."""
    from django.contrib.contenttypes.models import ContentType

    from wagtail.models import Locale
    from wagtail_localize.models import Translation, TranslationSource

    from springfield.cms.ftl_parser import (
        get_english_ftl_strings,
        get_english_ui_strings,
        get_ftl_translations,
        get_ui_translations,
        normalize_text_for_matching,
    )
    from springfield.cms.models import ArticleDetailPage

    source_locale = Locale.objects.get(language_code="en-US")

    # Target locales for FTL translation import
    target_locales = [
        Locale.objects.get(language_code="de"),  # German
        Locale.objects.get(language_code="fr"),  # French
        Locale.objects.get(language_code="es-ES"),  # Spanish - Spain
        Locale.objects.get(language_code="es-MX"),  # Spanish - México
        Locale.objects.get(language_code="zh-CN"),  # Chinese (Simplified)
        Locale.objects.get(language_code="pt-BR"),  # Portuguese (Brazil)
        Locale.objects.get(language_code="ru"),  # Russian
        Locale.objects.get(language_code="pl"),  # Polish
        Locale.objects.get(language_code="it"),  # Italian
        Locale.objects.get(language_code="ja"),  # Japanese
        Locale.objects.get(language_code="id"),  # Indonesian
        Locale.objects.get(language_code="nl"),  # Dutch
        Locale.objects.get(language_code="tr"),  # Turkish
    ]

    content_type = ContentType.objects.get_for_model(ArticleDetailPage)
    total_imported = 0

    # Get index page FTL strings (for descriptions shown on feature cards)
    index_en_strings = get_english_ftl_strings("index-2023.ftl")

    # Get UI strings (for common strings like "Learn more")
    ui_en_strings = get_english_ui_strings()

    for page_slug, ftl_filename in PAGE_FTL_MAPPING.items():
        # Get the source page
        source_page = ArticleDetailPage.objects.get(slug=page_slug, locale=source_locale)

        # Get English FTL strings for matching (from page's FTL file + index file + ui)
        en_ftl_strings = get_english_ftl_strings(ftl_filename)
        # Merge with index page strings for description matching
        en_ftl_strings.update(index_en_strings)
        # Merge with UI strings for common strings like "Learn more"
        en_ftl_strings.update(ui_en_strings)

        # Build lookup from normalized text to FTL message ID
        en_text_to_msgid = {}
        for msgid, text in en_ftl_strings.items():
            normalized = normalize_text_for_matching(text)
            en_text_to_msgid[normalized] = msgid

        # Get the TranslationSource for this page
        translation_source = (
            TranslationSource.objects.filter(
                object_id=source_page.translation_key,
                specific_content_type=content_type,
            )
            .order_by("-created_at")
            .first()
        )

        if not translation_source:
            raise Exception(f"No TranslationSource found for page: {page_slug}")

        for target_locale in target_locales:
            # Get FTL translations for this locale (from page's FTL file + index file + ui)
            translations = get_ftl_translations(target_locale.language_code, ftl_filename)
            index_translations = get_ftl_translations(target_locale.language_code, "index-2023.ftl")
            # Merge with index translations for description matching
            translations.update(index_translations)
            # Merge with UI translations for common strings like "Learn more"
            ui_translations = get_ui_translations(target_locale.language_code)
            translations.update(ui_translations)
            if not translations:
                continue

            # Get or create Translation
            translation, _ = Translation.objects.get_or_create(
                source=translation_source,
                target_locale=target_locale,
            )

            # Build PO file from FTL translations
            po = _build_po_from_ftl(translation, en_text_to_msgid, translations)

            if po:
                # Import the PO file
                translation.import_po(
                    po,
                    delete=False,
                    translation_type="manual",
                    tool_name="ftl_import",
                )
                total_imported += len(po)

                # Create the translated page
                translation.save_target(publish=True)

    print(f"\n  Imported {total_imported} translations")


def _build_po_from_ftl(translation, en_text_to_msgid, translations):
    """Build a PO file by matching Wagtail segments to FTL translations."""
    import polib
    from wagtail_localize.models import StringSegment

    from springfield.cms.ftl_parser import normalize_text_for_matching

    po = polib.POFile(wrapwidth=200)
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=utf-8",
        "X-WagtailLocalize-TranslationID": str(translation.uuid),
    }

    # Get all string segments for this translation source
    string_segments = StringSegment.objects.filter(source=translation.source).select_related("string", "context")

    for segment in string_segments:
        source_text = segment.string.data
        normalized_source = normalize_text_for_matching(source_text)

        # Try to find matching FTL message ID
        msgid = en_text_to_msgid.get(normalized_source)

        if msgid and msgid in translations:
            translated_text = translations[msgid]

            # Handle link attribute restoration
            translated_text = _convert_ftl_links_to_wagtail(translated_text, source_text)

            po.append(
                polib.POEntry(
                    msgid=source_text,
                    msgctxt=segment.context.path,
                    msgstr=translated_text,
                )
            )

    return po


def _convert_ftl_links_to_wagtail(translated, source):
    """Convert FTL link format to Wagtail link format.

    FTL files use two different link formats:
    1. <a { $variable }>text</a> - variable reference without href
    2. <a href="{ $url }">text</a> - variable reference inside href attribute

    Both need to be converted to Wagtail's <a id="a1"> format.
    """
    # Find all link IDs in the source text
    source_link_ids = re.findall(r'<a id="(a\d+)">', source)

    if not source_link_ids:
        return translated

    # FTL uses two different link formats:
    # 1. <a { $variable }> - variable as attribute shorthand (may have space before >)
    # 2. <a href="{ $url }"> - variable inside href attribute
    ftl_link_patterns = [
        r"<a\s*\{\s*\$[\w_]+\s*\}\s*>",  # Format 1: <a { $url }> or <a { $url } >
        r'<a\s+href="\{\s*\$[\w_]+\s*\}">',  # Format 2: <a href="{ $url }">
    ]

    # Combined pattern to match either format
    combined_pattern = "|".join(f"({p})" for p in ftl_link_patterns)

    # Replace each FTL link with corresponding Wagtail link ID
    result = translated
    for link_id in source_link_ids:
        result = re.sub(
            combined_pattern,
            f'<a id="{link_id}">',
            result,
            count=1,
        )

    return result


def run_all_forward(apps, schema_editor):
    """Run all migration steps in order."""
    create_feature_pages(apps, schema_editor)
    create_translation_sources(apps, schema_editor)
    import_ftl_translations(apps, schema_editor)


def reverse_migration(apps, schema_editor):
    """Reverse the migration by deleting created pages, translations, and unused images."""
    from springfield.cms.fixtures.feature_page_fixtures import FEATURE_IMAGES
    from springfield.cms.models import ArticleDetailPage, ArticleIndexPage, SpringfieldImage

    # Delete ALL feature detail pages (including translations in all locales)
    deleted_detail = ArticleDetailPage.objects.filter(
        slug__in=PAGE_FTL_MAPPING.keys(),
    ).delete()
    detail_count = deleted_detail[0] if deleted_detail else 0

    # Delete ALL features index pages (including translations)
    deleted_index = ArticleIndexPage.objects.filter(slug="features").delete()
    index_count = deleted_index[0] if deleted_index else 0

    # Delete images created for feature pages (only if not in use elsewhere)
    image_titles = [info["title"] for info in FEATURE_IMAGES.values()]
    deleted_images_count = 0
    for image in SpringfieldImage.objects.filter(title__in=image_titles):
        # Check if image is in use (Wagtail tracks usage via ReferenceIndex)
        # get_usage() returns a ReferenceGroups object - check if it has any items
        # Wrap in try/except because usage check may fail if referenced objects were already deleted
        try:
            usage = image.get_usage()
            if any(usage):
                continue  # Image is in use elsewhere, don't delete
        except Exception:
            pass  # If usage check fails, assume safe to delete
        image.delete()
        deleted_images_count += 1

    print(f"\n  Deleted feature pages: {detail_count} detail pages, {index_count} index pages, {deleted_images_count} unused images")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0037_articledetailpage_index_page_heading"),
    ]

    operations = [
        migrations.RunPython(run_all_forward, reverse_migration),
    ]
