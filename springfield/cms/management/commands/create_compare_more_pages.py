# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to create Firefox compare and more pages in the CMS.

Runs three phases:
1. Create ArticleIndexPage + ArticleDetailPage instances for compare and more pages.
2. Create TranslationSource records and fix schema_version on all new sources.
3. Import FTL translations for all pages that have FTL files configured.

Pages with no FTL files (incognito-browser, update-your-browser) are created in
Phase 1 but skipped in Phase 3 — they have English-only content.
"""

import os
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale
from wagtail_localize.models import Translation, TranslationSource

from springfield.cms.fixtures.compare_more_page_fixtures import (
    COMPARE_INDEX_FTL_FILES,
    COMPARE_PAGES,
    MORE_INDEX_FTL_FILES,
    MORE_PAGES,
    load_compare_more_page_fixtures,
)
from springfield.cms.ftl_parser import (
    build_po_from_ftl,
    build_text_to_msgid_mapping,
    get_english_ftl_strings_at_subpath,
    get_english_ui_strings,
    get_ftl_translations_at_subpath,
    get_ui_translations,
)
from springfield.cms.models import ArticleDetailPage, ArticleIndexPage

ALL_LOCALE_CODES = [
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


def _get_locale_codes(stdout):
    """Return locale codes to translate, respecting DEBUG / ALL_LOCALES env var."""

    all_locales_env = os.environ.get("ALL_LOCALES", "").lower() in ("1", "true", "yes")
    if not settings.DEBUG or all_locales_env:
        return ALL_LOCALE_CODES
    stdout.write("  Development mode: translating es-ES only (set ALL_LOCALES=1 for all)\n")
    return ["es-ES"]


def _merge_ftl_strings(ftl_relative_paths: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """
    Merge English strings and build a text-to-msgid mapping for a list of FTL relative paths.

    Returns:
        (en_text_to_msgid, en_strings)  where en_text_to_msgid maps normalized English text
        to FTL message IDs and en_strings maps message IDs to English text.
    """

    en_strings: dict[str, str] = {}
    for path in ftl_relative_paths:
        en_strings.update(get_english_ftl_strings_at_subpath(path))
    return build_text_to_msgid_mapping(en_strings), en_strings


def _get_merged_translations(ftl_relative_paths: list[str], locale_code: str) -> dict[str, str]:
    """Merge FTL translations for a locale across multiple FTL files."""

    merged: dict[str, str] = {}
    for path in ftl_relative_paths:
        merged.update(get_ftl_translations_at_subpath(locale_code, path))
    return merged


def _get_translation_source(page, content_type):
    """Return the most recent TranslationSource for a page, or None."""

    return (
        TranslationSource.objects.filter(
            object_id=page.translation_key,
            specific_content_type=content_type,
        )
        .order_by("-created_at")
        .first()
    )


def _translate_page(page, ftl_files: list[str], target_locales, content_type, stdout):
    """Import FTL translations for all target locales for a single page.

    UI strings (ui.ftl) are always merged in so that shared fields like
    link_text ("Learn more") are translated even when not in the page FTL files.
    """

    en_text_to_msgid, _ = _merge_ftl_strings(ftl_files)
    # Merge UI strings so fields like link_text ("Learn more") are covered.
    en_text_to_msgid.update(build_text_to_msgid_mapping(get_english_ui_strings()))

    translation_source = _get_translation_source(page, content_type)
    if not translation_source:
        stdout.write(f"  WARNING: No TranslationSource found for {page.slug}, skipping\n")
        return 0

    imported = 0
    for target_locale in target_locales:
        translations = _get_merged_translations(ftl_files, target_locale.language_code)
        translations.update(get_ui_translations(target_locale.language_code))
        if not translations:
            continue

        translation, _ = Translation.objects.get_or_create(
            source=translation_source,
            target_locale=target_locale,
        )

        po = build_po_from_ftl(translation, en_text_to_msgid, translations)
        if po:
            translation.import_po(po, delete=False, translation_type="manual", tool_name="ftl_import")
            imported += len(po)
            translation.save_target(publish=False)

    return imported


class Command(BaseCommand):
    help = "Create Firefox compare and more CMS pages and import FTL translations."

    @transaction.atomic
    def handle(self, *args, **options):

        # ======================================================================
        # Phase 1: Create pages
        # ======================================================================
        self.stdout.write("Phase 1: Creating compare/more pages...\n")
        compare_index, more_index, compare_pages, more_pages = load_compare_more_page_fixtures(publish=False)
        # compare_pages / more_pages are lists ordered the same as COMPARE_PAGES / MORE_PAGES dicts
        compare_pages_by_slug = dict(zip(COMPARE_PAGES.keys(), compare_pages))
        more_pages_by_slug = dict(zip(MORE_PAGES.keys(), more_pages))

        self.stdout.write(f"  Compare index page: {compare_index.slug}\n")
        self.stdout.write(f"  More index page: {more_index.slug}\n")
        self.stdout.write(f"  Compare detail pages: {list(compare_pages_by_slug.keys())}\n")
        self.stdout.write(f"  More detail pages: {list(more_pages_by_slug.keys())}\n")

        # ======================================================================
        # Phase 2: Create TranslationSource records + fix schema_version
        # ======================================================================
        self.stdout.write("Phase 2: Creating TranslationSource records...\n")

        all_pages = [compare_index, more_index] + compare_pages + more_pages

        for page in all_pages:
            source, created = TranslationSource.get_or_create_from_instance(page)
            if created:
                self.stdout.write(f"  Created TranslationSource for: {page.slug}\n")
            else:
                source.update_from_db()
                source.refresh_segments()
                self.stdout.write(f"  Refreshed segments for: {page.slug}\n")

        # Fix schema_version: the latest migration name from disk is the correct value.
        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        migration_names = sorted(f.stem for f in migrations_dir.glob("0*.py"))
        latest_schema_version = migration_names[-1] if migration_names else ""

        all_translation_keys = [p.translation_key for p in all_pages]

        TranslationSource.objects.filter(
            object_id__in=all_translation_keys,
        ).update(schema_version=latest_schema_version)
        self.stdout.write(f"  Set schema_version={latest_schema_version} on {len(all_pages)} sources\n")

        # ======================================================================
        # Phase 3: Import FTL translations
        # ======================================================================
        self.stdout.write("Phase 3: Importing FTL translations...\n")

        locale_codes = _get_locale_codes(self.stdout)
        target_locales = []
        for code in locale_codes:
            locale, _ = Locale.objects.get_or_create(language_code=code)
            target_locales.append(locale)

        index_content_type = ContentType.objects.get_for_model(ArticleIndexPage)
        detail_content_type = ContentType.objects.get_for_model(ArticleDetailPage)

        total_imported = 0

        # Compare index page
        n = _translate_page(compare_index, COMPARE_INDEX_FTL_FILES, target_locales, index_content_type, self.stdout)
        total_imported += n
        self.stdout.write(f"  Translated compare index page ({n} strings)\n")

        # More index page
        n = _translate_page(more_index, MORE_INDEX_FTL_FILES, target_locales, index_content_type, self.stdout)
        total_imported += n
        self.stdout.write(f"  Translated more index page ({n} strings)\n")

        # Compare detail pages
        for slug, page in compare_pages_by_slug.items():
            ftl_files = COMPARE_PAGES[slug]["ftl_files"]
            if not ftl_files:
                self.stdout.write(f"  Skipping {slug} (no FTL files)\n")
                continue
            n = _translate_page(page, ftl_files, target_locales, detail_content_type, self.stdout)
            total_imported += n
            self.stdout.write(f"  Translated compare/{slug} ({n} strings)\n")

        # More detail pages
        for slug, page in more_pages_by_slug.items():
            ftl_files = MORE_PAGES[slug]["ftl_files"]
            if not ftl_files:
                self.stdout.write(f"  Skipping {slug} (no FTL files)\n")
                continue
            n = _translate_page(page, ftl_files, target_locales, detail_content_type, self.stdout)
            total_imported += n
            self.stdout.write(f"  Translated more/{slug} ({n} strings)\n")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Imported {total_imported} translations across {len(target_locales)} locales.\n"))
