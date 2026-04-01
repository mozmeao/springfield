# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to publish migrated WhatsNewPage2026 draft pages.

For each en-US WhatsNewPage2026 whose slug ends with '-new':
  1. Rename the corresponding legacy WhatsNewPage slug → slug+'-old'
  2. Rename the new page slug+'-new' → original slug
  3. Publish the new page (and all its translations)

Supports --dry-run to preview changes without making them.

Run this after migrate_whats_new_to_2026.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.models import Locale, Page

from springfield.cms.models import WhatsNewPage, WhatsNewPage2026


def _rename_page_slug(page, new_slug, dry_run=False, stdout=None, style=None):
    """Rename a page's slug using Wagtail's Page.save() which handles url_path updates."""
    if stdout:
        msg = f"    Renaming slug: '{page.slug}' → '{new_slug}' (locale={page.locale.language_code})"
        stdout.write(msg)
    if not dry_run:
        page_obj = Page.objects.get(pk=page.pk)
        page_obj.slug = new_slug
        page_obj.save()


class Command(BaseCommand):
    help = "Publish migrated WhatsNewPage2026 draft pages (created by migrate_whats_new_to_2026)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making any changes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made."))

        en_us_locale = Locale.objects.get(language_code="en-US")

        # Find all en-US new pages driven by their '-new' slug suffix.
        new_pages = WhatsNewPage2026.objects.filter(
            locale=en_us_locale,
            slug__endswith="-new",
        ).order_by("slug")

        total_published = 0
        total_skipped = 0

        for new_page in new_pages:
            new_slug = new_page.slug
            original_slug = new_slug.replace("-new", "")

            self.stdout.write(f"\nProcessing: '{new_slug}' → '{original_slug}'")

            # ----------------------------------------------------------------
            # Find and rename all locale variants of the new page.
            # We process en-US first (the loop driver), then translations.
            # ----------------------------------------------------------------
            all_new_locale_pages = [new_page] + list(new_page.get_translations(inclusive=False))

            for locale_new_page in all_new_locale_pages:
                locale_new_slug = locale_new_page.slug
                # Derive the original slug for this locale variant:
                # it ends with '-new', so strip that suffix.
                if not locale_new_slug.endswith("-new"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIPPED unexpected slug '{locale_new_slug}' "
                            f"(locale={locale_new_page.locale.language_code}) — does not end with '-new'."
                        )
                    )
                    total_skipped += 1
                    continue

                locale_original_slug = locale_new_slug.replace("-new", "")
                locale_old_slug = locale_original_slug + "-old"

                self.stdout.write(f"  Locale {locale_new_page.locale.language_code}: '{locale_new_slug}' → '{locale_original_slug}'")

                # Step 1: Find the legacy page for this locale+slug and rename it.
                try:
                    legacy_page = WhatsNewPage.objects.get(
                        slug=locale_original_slug,
                        locale=locale_new_page.locale,
                    )
                    _rename_page_slug(
                        legacy_page,
                        locale_old_slug,
                        dry_run=dry_run,
                        stdout=self.stdout,
                        style=self.style,
                    )
                except WhatsNewPage.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    No legacy WhatsNewPage found for slug='{locale_original_slug}', "
                            f"locale={locale_new_page.locale.language_code} — skipping rename of old page."
                        )
                    )

                # Step 2: Rename the new draft page to the original slug.
                _rename_page_slug(
                    locale_new_page,
                    locale_original_slug,
                    dry_run=dry_run,
                    stdout=self.stdout,
                    style=self.style,
                )

                # Step 3: Publish the new page.
                self.stdout.write(f"    Publishing: locale={locale_new_page.locale.language_code}, slug={locale_original_slug}")
                if not dry_run:
                    # Re-fetch after slug rename, save a fresh revision with the
                    # updated slug, then publish it. Publishing an old revision
                    # would restore the '-new' slug from its stored content.
                    locale_new_page.refresh_from_db()
                    locale_new_page.save_revision().publish()

                # Step 4: unpublish the old page
                if not dry_run and legacy_page:
                    self.stdout.write(f"    Unpublishing legacy page: locale={legacy_page.locale.language_code}, slug={locale_old_slug}")
                    legacy_page.refresh_from_db()
                    legacy_page.unpublish()

                total_published += 1

        self.stdout.write("")
        if total_skipped:
            self.stdout.write(self.style.WARNING(f"Skipped {total_skipped} page(s)."))

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would have published {total_published} page(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully published {total_published} WhatsNewPage2026 page(s)."))
