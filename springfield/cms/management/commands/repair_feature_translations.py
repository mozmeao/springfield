# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
One-time management command to repair feature page translations after
block UUID changes.

When load_feature_page_fixtures() is re-run on an existing server,
StreamField blocks get new random UUIDs, which orphans existing
StringTranslation records (they reference the old context paths).

This command:
1. Updates TranslationSource records to sync with the current page content
   (picking up new block UUIDs)
2. Re-imports FTL translations by matching English text to FTL message IDs
"""

import importlib
import re

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale

from springfield.cms.ftl_parser import (
    get_english_ftl_strings,
    get_english_shared_strings,
    get_english_ui_strings,
    get_ftl_translations,
    get_shared_translations,
    get_ui_translations,
    normalize_text_for_matching,
)

_migration_0039 = importlib.import_module("springfield.cms.migrations.0039_create_feature_pages")
PAGE_FTL_MAPPING = _migration_0039.PAGE_FTL_MAPPING


class Command(BaseCommand):
    help = "Repair feature page translations after block UUID changes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes.",
        )
        parser.add_argument(
            "--locale",
            type=str,
            default=None,
            help="Limit to a single locale (e.g. 'es-ES'). Default: all configured locales.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        locale_filter = options["locale"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        from wagtail_localize.models import Translation, TranslationSource

        from springfield.cms.models import ArticleDetailPage, ArticleIndexPage

        source_locale = Locale.objects.get(language_code="en-US")

        # Determine target locales
        all_locale_codes = [
            "de",
            "fr",
            "es-ES",
            "es-MX",
            "zh-CN",
            "pt-BR",
            "ru",
            "pl",
            "it",
            "ja",
            "id",
            "nl",
            "tr",
        ]
        if locale_filter:
            if locale_filter not in all_locale_codes:
                self.stderr.write(self.style.ERROR(f"Unknown locale: {locale_filter}"))
                return
            locale_codes = [locale_filter]
        else:
            locale_codes = all_locale_codes

        target_locales = []
        for code in locale_codes:
            locale, _ = Locale.objects.get_or_create(language_code=code)
            target_locales.append(locale)

        # Get the feature index page
        from wagtail.models import Site

        site = Site.objects.get(is_default_site=True)
        root_page = site.root_page
        index_page = ArticleIndexPage.objects.get(
            slug="features",
            locale=source_locale,
            path__startswith=root_page.path,
            depth=root_page.depth + 1,
        )

        # ======================================================================
        # Step 1: Update TranslationSource records
        # ======================================================================
        self.stdout.write("Updating TranslationSource records...")

        # Update index page source
        index_source = (
            TranslationSource.objects.filter(
                object_id=index_page.translation_key,
                specific_content_type=ContentType.objects.get_for_model(ArticleIndexPage),
            )
            .order_by("-created_at")
            .first()
        )

        if index_source:
            if not dry_run:
                index_source.update_from_db()
            self.stdout.write(f"  Updated source for index page: {index_page.slug}")
        else:
            self.stdout.write(self.style.WARNING(f"  No TranslationSource for index page: {index_page.slug}"))

        # Update each detail page source
        detail_content_type = ContentType.objects.get_for_model(ArticleDetailPage)
        for slug in PAGE_FTL_MAPPING:
            page = ArticleDetailPage.objects.get(
                slug=slug,
                locale=source_locale,
                path__contains=index_page.path,
            )
            page_source = (
                TranslationSource.objects.filter(
                    object_id=page.translation_key,
                    specific_content_type=detail_content_type,
                )
                .order_by("-created_at")
                .first()
            )

            if page_source:
                if not dry_run:
                    page_source.update_from_db()
                self.stdout.write(f"  Updated source for: {slug}")
            else:
                self.stdout.write(self.style.WARNING(f"  No TranslationSource for: {slug}"))

        # ======================================================================
        # Step 2: Re-import FTL translations
        # ======================================================================
        self.stdout.write("Re-importing FTL translations...")

        total_imported = 0

        # Prepare English string mappings
        index_en_strings = get_english_ftl_strings("index-2023.ftl")
        shared_en_strings = get_english_shared_strings()
        ui_en_strings = get_english_ui_strings()

        # --- Index page translations ---
        index_content_type = ContentType.objects.get_for_model(ArticleIndexPage)
        index_en_text_to_msgid = {}
        for msgid, text in index_en_strings.items():
            index_en_text_to_msgid[normalize_text_for_matching(text)] = msgid
        for msgid, text in shared_en_strings.items():
            index_en_text_to_msgid[normalize_text_for_matching(text)] = msgid

        index_translation_source = (
            TranslationSource.objects.filter(
                object_id=index_page.translation_key,
                specific_content_type=index_content_type,
            )
            .order_by("-created_at")
            .first()
        )

        if index_translation_source:
            for target_locale in target_locales:
                index_translations = get_ftl_translations(target_locale.language_code, "index-2023.ftl")
                index_translations.update(get_shared_translations(target_locale.language_code))
                if not index_translations:
                    continue

                translation, _ = Translation.objects.get_or_create(
                    source=index_translation_source,
                    target_locale=target_locale,
                )

                po = _build_po_from_ftl(translation, index_en_text_to_msgid, index_translations)
                if po:
                    if not dry_run:
                        translation.import_po(
                            po,
                            delete=False,
                            translation_type="manual",
                            tool_name="ftl_import",
                        )
                        translation.save_target(publish=False)
                    total_imported += len(po)
                    self.stdout.write(f"  Index page -> {target_locale.language_code}: {len(po)} translations")

        # --- Detail page translations ---
        for page_slug, ftl_filename in PAGE_FTL_MAPPING.items():
            source_page = ArticleDetailPage.objects.get(
                slug=page_slug,
                locale=source_locale,
                path__contains=index_page.path,
            )

            en_ftl_strings = get_english_ftl_strings(ftl_filename)
            en_ftl_strings.update(index_en_strings)
            en_ftl_strings.update(ui_en_strings)

            en_text_to_msgid = {}
            for msgid, text in en_ftl_strings.items():
                en_text_to_msgid[normalize_text_for_matching(text)] = msgid

            translation_source = (
                TranslationSource.objects.filter(
                    object_id=source_page.translation_key,
                    specific_content_type=detail_content_type,
                )
                .order_by("-created_at")
                .first()
            )

            if not translation_source:
                self.stdout.write(self.style.WARNING(f"  No TranslationSource for: {page_slug}"))
                continue

            for target_locale in target_locales:
                translations = get_ftl_translations(target_locale.language_code, ftl_filename)
                index_translations = get_ftl_translations(target_locale.language_code, "index-2023.ftl")
                translations.update(index_translations)
                ui_translations = get_ui_translations(target_locale.language_code)
                translations.update(ui_translations)
                if not translations:
                    continue

                translation, _ = Translation.objects.get_or_create(
                    source=translation_source,
                    target_locale=target_locale,
                )

                po = _build_po_from_ftl(translation, en_text_to_msgid, translations)
                if po:
                    if not dry_run:
                        translation.import_po(
                            po,
                            delete=False,
                            translation_type="manual",
                            tool_name="ftl_import",
                        )
                        translation.save_target(publish=False)
                    total_imported += len(po)
                    self.stdout.write(f"  {page_slug} -> {target_locale.language_code}: {len(po)} translations")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would have imported {total_imported} translations."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {total_imported} translations."))


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

    string_segments = StringSegment.objects.filter(source=translation.source).select_related("string", "context")

    for segment in string_segments:
        source_text = segment.string.data
        normalized_source = normalize_text_for_matching(source_text)

        msgid = en_text_to_msgid.get(normalized_source)

        if msgid and msgid in translations:
            translated_text = translations[msgid]
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
    source_link_ids = re.findall(r'<a id="(a\d+)">', source)

    if not source_link_ids:
        return translated

    ftl_link_patterns = [
        r"<a\s*\{\s*\$[\w_]+\s*\}\s*>",
        r'<a\s+href="\{\s*\$[\w_]+\s*\}">',
    ]

    combined_pattern = "|".join(f"({p})" for p in ftl_link_patterns)

    result = translated
    for link_id in source_link_ids:
        result = re.sub(
            combined_pattern,
            f'<a id="{link_id}">',
            result,
            count=1,
        )

    return result
