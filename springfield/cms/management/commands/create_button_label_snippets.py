# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to create ButtonLabelSnippet records and bootstrap FTL translations.

Runs three phases:
1. Create (or update) the two English ButtonLabelSnippet records at their fixed IDs,
   then advance the PostgreSQL sequence so auto-generated IDs don't collide.
2. Register TranslationSource records and fix schema_version.
3. Import FTL translations for all configured Wagtail locales.

All three phases are idempotent: re-running after a snapshot restore or adding a new
locale is safe.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Create ButtonLabelSnippet records and bootstrap FTL translations."

    @transaction.atomic
    def handle(self, *args, **options):
        from django.db import connection

        from wagtail.models import Locale
        from wagtail_localize.models import Translation, TranslationSource

        from springfield.cms.ftl_parser import (
            build_po_from_ftl,
            build_text_to_msgid_mapping,
            get_english_ftl_strings_at_subpath,
            get_ftl_translations_at_subpath,
        )
        from springfield.cms.models import ButtonLabelSnippet

        # ======================================================================
        # Phase 1: Create English base records
        # ======================================================================
        self.stdout.write("Phase 1: Creating English ButtonLabelSnippet records...\n")

        locale = Locale.objects.get(language_code="en-US")
        get_firefox, _ = ButtonLabelSnippet.objects.update_or_create(
            id=settings.BUTTON_LABEL_GET_FIREFOX_SNIPPET_ID,
            defaults={"locale": locale, "key": "get_firefox", "label": "Get Firefox", "live": True},
        )
        download_firefox, _ = ButtonLabelSnippet.objects.update_or_create(
            id=settings.BUTTON_LABEL_DOWNLOAD_FIREFOX_SNIPPET_ID,
            defaults={"locale": locale, "key": "download_firefox", "label": "Download Firefox", "live": True},
        )
        self.stdout.write(f"  {get_firefox} (id={get_firefox.pk})\n")
        self.stdout.write(f"  {download_firefox} (id={download_firefox.pk})\n")

        # Advance the PostgreSQL sequence past the highest explicitly inserted ID so
        # that auto-generated IDs (used by Wagtail-Localize for locale copies) don't
        # collide with the fixed IDs.
        if connection.vendor == "postgresql":
            from django.core.management.color import no_style

            for sql in connection.ops.sequence_reset_sql(no_style(), [ButtonLabelSnippet]):
                with connection.cursor() as cursor:
                    cursor.execute(sql)
            self.stdout.write("  Advanced PostgreSQL sequence.\n")

        # ======================================================================
        # Phase 2: Register TranslationSources and fix schema_version
        # ======================================================================
        self.stdout.write("Phase 2: Registering TranslationSources...\n")

        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        migration_names = sorted(f.stem for f in migrations_dir.glob("0*.py"))
        latest_schema_version = migration_names[-1] if migration_names else ""

        sources = {}
        for snippet, name in [(get_firefox, "get_firefox"), (download_firefox, "download_firefox")]:
            source, created = TranslationSource.get_or_create_from_instance(snippet)
            if created:
                self.stdout.write(f"  Created TranslationSource for {name}\n")
            else:
                source.update_from_db()
                source.refresh_segments()
                self.stdout.write(f"  Refreshed TranslationSource for {name}\n")
            source.schema_version = latest_schema_version
            source.save(update_fields=["schema_version"])
            sources[name] = source

        self.stdout.write(f"  Set schema_version={latest_schema_version}\n")

        # ======================================================================
        # Phase 3: Bootstrap FTL translations
        # ======================================================================
        self.stdout.write("Phase 3: Bootstrapping FTL translations...\n")

        for snippet, source, ftl_subpath in [
            (get_firefox, sources["get_firefox"], "navigation-firefox.ftl"),
            (download_firefox, sources["download_firefox"], "download_button.ftl"),
        ]:
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

            self.stdout.write(f"  {snippet.key}: {imported} strings imported\n")

        self.stdout.write(self.style.SUCCESS("\nDone.\n"))
