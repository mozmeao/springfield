# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to create PretranslatedPhrase records and bootstrap FTL translations.

Runs three phases:
1. Create (or update) the English PretranslatedPhrase records using stable translation_key UUIDs.
2. Register TranslationSource records and fix schema_version.
3. Import FTL translations for all configured Wagtail locales.

All three phases are idempotent: re-running after a snapshot restore or adding a new
locale is safe.
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

# Local string identifier for snippet metadata. The translation_key UUIDs are stable;
# do not change them — wagtail_localize uses translation_key to link English
# source rows to their translated copies across locales.
PHRASES = {
    "get_firefox": {
        "translation_key": "f25078fd-50e4-4a73-acbc-6355bfa7de6e",
        "label": "Get Firefox",
        "ftl_subpath": "navigation-firefox.ftl",
    },
    "download_firefox": {
        "translation_key": "e13dc0ed-aa51-4077-b011-fb20958ffefd",
        "label": "Download Firefox",
        "ftl_subpath": "download_button.ftl",
    },
}


class Command(BaseCommand):
    help = "Create PretranslatedPhrase records and bootstrap FTL translations."

    @transaction.atomic
    def handle(self, *args, **options):
        from wagtail.models import Locale
        from wagtail_localize.models import Translation, TranslationSource

        from springfield.cms.ftl_parser import (
            build_po_from_ftl,
            build_text_to_msgid_mapping,
            get_english_ftl_strings_at_subpath,
            get_ftl_translations_at_subpath,
        )
        from springfield.cms.models import PretranslatedPhrase

        # ======================================================================
        # Phase 1: Create English base records
        # ======================================================================
        self.stdout.write("Phase 1: Creating PretranslatedPhrase records...\n")

        locale_en_us = Locale.objects.get(language_code="en-US")

        snippets = {}
        for key, info in PHRASES.items():
            snippet, _ = PretranslatedPhrase.objects.update_or_create(
                translation_key=info["translation_key"],
                locale=locale_en_us,
                defaults={"label": info["label"], "live": True},
            )
            snippets[key] = snippet
            self.stdout.write(f"  {snippet} (id={snippet.pk})\n")

        # ======================================================================
        # Phase 2: Register TranslationSources and fix schema_version
        # ======================================================================
        self.stdout.write("Phase 2: Registering TranslationSources...\n")

        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        migration_names = sorted(f.stem for f in migrations_dir.glob("0*.py"))
        latest_schema_version = migration_names[-1] if migration_names else ""

        sources = {}
        for key, snippet in snippets.items():
            source, created = TranslationSource.get_or_create_from_instance(snippet)
            if created:
                self.stdout.write(f"  Created TranslationSource for {key}\n")
            else:
                source.update_from_db()
                source.refresh_segments()
                self.stdout.write(f"  Refreshed TranslationSource for {key}\n")
            source.schema_version = latest_schema_version
            source.save(update_fields=["schema_version"])
            sources[key] = source

        self.stdout.write(f"  Set schema_version={latest_schema_version}\n")

        # ======================================================================
        # Phase 3: Bootstrap FTL translations
        # ======================================================================
        self.stdout.write("Phase 3: Bootstrapping FTL translations...\n")

        for key, snippet in snippets.items():
            source = sources[key]
            ftl_subpath = PHRASES[key]["ftl_subpath"]

            en_strings = get_english_ftl_strings_at_subpath(ftl_subpath)
            text_to_msgid = build_text_to_msgid_mapping(en_strings)
            imported = 0

            for target_locale in Locale.objects.exclude(language_code="en-US"):
                ftl_translations = get_ftl_translations_at_subpath(target_locale.language_code, ftl_subpath)
                if not ftl_translations:
                    continue

                translation, _ = Translation.objects.get_or_create(
                    source=source,
                    target_locale=target_locale,
                )
                po = build_po_from_ftl(translation, text_to_msgid, ftl_translations)
                # build_po_from_ftl always returns a polib.POFile (never None).
                # An empty file (no FTL coverage for this locale) is falsy because
                # POFile is a list subclass. Check truthiness, not None-ness.
                if po:
                    translation.import_po(
                        po,
                        delete=False,  # idempotent: don't wipe existing translations
                        translation_type="manual",
                        tool_name="ftl_import",
                    )
                    translation.save_target(publish=True)  # snippets must be live immediately
                    imported += len(po)

            self.stdout.write(f"  {key}: {imported} strings imported\n")

        self.stdout.write(self.style.SUCCESS("\nDone.\n"))
