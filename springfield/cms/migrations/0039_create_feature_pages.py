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

import os
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

    index_page, feature_pages = load_feature_page_fixtures(publish=False)
    print(f"\n  Created feature index page: {index_page.slug}")
    print(f"  Created {len(feature_pages)} feature pages")


def get_source_locale():
    from wagtail.models import Locale

    return Locale.objects.get(language_code="en-US")


def get_article_index_page_in_source_locale():
    from wagtail.models import Site

    from springfield.cms.models import ArticleIndexPage

    source_locale = get_source_locale()
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    return ArticleIndexPage.objects.get(
        slug="features",
        locale=source_locale,
        # Get the ArticleIndexPage that is a direct child of the root page
        path__startswith=root_page.path,
        depth=root_page.depth + 1,
    )


def create_translation_sources(apps, schema_editor):
    """Create TranslationSource records and segments for feature pages."""
    from wagtail_localize.models import TranslationSource

    from springfield.cms.models import ArticleDetailPage

    source_locale = get_source_locale()

    # Create TranslationSource for the index page
    index_page = get_article_index_page_in_source_locale()
    source, created = TranslationSource.get_or_create_from_instance(index_page)
    if created:
        print(f"\n  Created TranslationSource for index page: {index_page.slug}")
    else:
        source.refresh_segments()
        print(f"\n  Refreshed segments for index page: {index_page.slug}")

    # Create TranslationSource for each feature page
    for slug in PAGE_FTL_MAPPING.keys():
        page = ArticleDetailPage.objects.get(
            slug=slug,
            locale=source_locale,
            path__contains=index_page.path,  # Make sure to get the ArticleDetailPage that is a child of index_page
        )
        source, created = TranslationSource.get_or_create_from_instance(page)
        if created:
            print(f"  Created TranslationSource for: {slug}")
        else:
            source.refresh_segments()
            print(f"  Refreshed segments for: {slug}")


def import_ftl_translations(apps, schema_editor):
    """Import FTL translations for all feature pages and locales.

    In production (DEBUG=False), all locales are translated.
    In development (DEBUG=True), only es-ES is translated for speed.
    Set ALL_LOCALES=1 in development to translate all locales.
    """
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType

    from wagtail.models import Locale
    from wagtail_localize.models import Translation, TranslationSource

    from springfield.cms.ftl_parser import (
        get_english_ftl_strings,
        get_english_shared_strings,
        get_english_ui_strings,
        get_ftl_translations,
        get_shared_translations,
        get_ui_translations,
        normalize_text_for_matching,
    )
    from springfield.cms.models import ArticleDetailPage, ArticleIndexPage

    source_locale = Locale.objects.get(language_code="en-US")

    # All available target locales
    all_locale_codes = [
        "de",  # German
        "fr",  # French
        "es-ES",  # Spanish - Spain
        "es-MX",  # Spanish - México
        "zh-CN",  # Chinese (Simplified)
        "pt-BR",  # Portuguese (Brazil)
        "ru",  # Russian
        "pl",  # Polish
        "it",  # Italian
        "ja",  # Japanese
        "id",  # Indonesian
        "nl",  # Dutch
        "tr",  # Turkish
    ]

    # Determine which locales to translate:
    # - Production (DEBUG=False): all locales
    # - Development with ALL_LOCALES=1: all locales
    # - Development otherwise: es-ES only (for speed)
    all_locales_env = os.environ.get("ALL_LOCALES", "").lower() in ("1", "true", "yes")
    if not settings.DEBUG or all_locales_env:
        locale_codes = all_locale_codes
    else:
        locale_codes = ["es-ES"]
        print("\n  Development mode: translating es-ES only (set ALL_LOCALES=1 for all)")

    # Fetch target locales from database
    target_locales = []
    for code in locale_codes:
        locale, _ = Locale.objects.get_or_create(language_code=code)
        target_locales.append(locale)

    total_imported = 0

    # Get index page FTL strings (for descriptions shown on feature cards)
    index_en_strings = get_english_ftl_strings("index-2023.ftl")

    # Get shared strings (for "Do more with Firefox" heading)
    shared_en_strings = get_english_shared_strings()

    # Get UI strings (for common strings like "Learn more")
    ui_en_strings = get_english_ui_strings()

    # ==========================================================================
    # Translate the index page
    # ==========================================================================
    index_page = get_article_index_page_in_source_locale()
    index_content_type = ContentType.objects.get_for_model(ArticleIndexPage)

    # Build lookup from normalized English text to FTL message ID
    # Include index-2023.ftl and shared.ftl strings
    index_en_text_to_msgid = {}
    for msgid, text in index_en_strings.items():
        normalized = normalize_text_for_matching(text)
        index_en_text_to_msgid[normalized] = msgid
    for msgid, text in shared_en_strings.items():
        normalized = normalize_text_for_matching(text)
        index_en_text_to_msgid[normalized] = msgid

    # Get the TranslationSource for the index page
    index_translation_source = (
        TranslationSource.objects.filter(
            object_id=index_page.translation_key,
            specific_content_type=index_content_type,
        )
        .order_by("-created_at")
        .first()
    )

    if not index_translation_source:
        raise Exception("No TranslationSource found for index page: features")

    for target_locale in target_locales:
        # Get translations from both index-2023.ftl and shared.ftl
        index_translations = get_ftl_translations(target_locale.language_code, "index-2023.ftl")
        index_translations.update(get_shared_translations(target_locale.language_code))
        if not index_translations:
            continue

        # Get or create Translation for the index page
        translation, _ = Translation.objects.get_or_create(
            source=index_translation_source,
            target_locale=target_locale,
        )

        # Build PO file from FTL translations
        po = _build_po_from_ftl(translation, index_en_text_to_msgid, index_translations)

        if po:
            translation.import_po(
                po,
                delete=False,
                translation_type="manual",
                tool_name="ftl_import",
            )
            total_imported += len(po)
            translation.save_target(publish=False)

    print(f"\n  Translated index page to {len(target_locales)} locales")

    # ==========================================================================
    # Translate detail pages
    # ==========================================================================
    content_type = ContentType.objects.get_for_model(ArticleDetailPage)

    for page_slug, ftl_filename in PAGE_FTL_MAPPING.items():
        # Get the source page
        source_page = ArticleDetailPage.objects.get(
            slug=page_slug,
            locale=source_locale,
            path__contains=index_page.path,  # Make sure to get the ArticleDetailPage that is a child of index_page
        )

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
                translation.save_target(publish=False)

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
    # In tests, the code to create feature pages is skipped entirely.
    if os.environ.get("DJANGO_SETTINGS_MODULE") == "springfield.settings.test":
        print("Skipping feature page creation in test environment")
        return

    create_feature_pages(apps, schema_editor)
    create_translation_sources(apps, schema_editor)
    import_ftl_translations(apps, schema_editor)


def reverse_migration(apps, schema_editor):
    """Reverse the migration by deleting created pages, translations, and unused images."""

    from springfield.cms.fixtures.feature_page_fixtures import FEATURE_IMAGES
    from springfield.cms.models import ArticleDetailPage, ArticleIndexPage, SpringfieldImage

    try:
        index_page = get_article_index_page_in_source_locale()
    except ArticleIndexPage.DoesNotExist:
        detail_count = 0
        index_count = 0
    else:
        # Delete ALL feature detail pages (including translations in all locales)
        deleted_detail = ArticleDetailPage.objects.filter(
            slug__in=PAGE_FTL_MAPPING.keys(),
            # Make sure to match only the ArticleDetailPages that are a child of index_page
            path__contains=index_page.path,
        ).delete()
        detail_count = deleted_detail[0] if deleted_detail else 0

        # Delete ALL features index pages (including translations)
        deleted_index = index_page.get_translations().count()
        index_page.get_translations().delete()
        index_page.delete()
        deleted_index += 1
        index_count = deleted_index

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
        ("cms", "0038_articledetailpage_index_page_heading"),
        # Required because save_target() may interact with wagtail_localize_smartling
        # which has a handler that queries LandedTranslationTask
        ("wagtail_localize_smartling", "0004_landedtranslationtask"),
    ]

    operations = [
        migrations.RunPython(run_all_forward, reverse_migration),
    ]
