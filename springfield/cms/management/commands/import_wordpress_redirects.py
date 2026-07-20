# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Page, Site


class Command(BaseCommand):
    help = (
        "Creates wagtail.contrib.redirects Redirect records from the CSV produced by "
        "import_wordpress_blog_posts (columns: wp_id, old_permalink, new_page_id, new_page_path)."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the redirects CSV.")
        parser.add_argument(
            "--site",
            default=None,
            help="Hostname of the wagtailcore.Site these redirects apply to (default: applies to all sites).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report what would be created without writing anything.")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        site = None
        if options["site"]:
            site = Site.objects.filter(hostname=options["site"]).first()
            if site is None:
                raise CommandError(f"No Site found with hostname {options['site']!r}")

        dry_run = options["dry_run"]
        created = skipped = missing_page = 0

        with open(csv_path, newline="") as fh:
            for row in csv.DictReader(fh):
                old_path = row["old_permalink"]
                page = Page.objects.filter(pk=row["new_page_id"]).first()
                if page is None:
                    self.stderr.write(f"  ! page id {row['new_page_id']} not found, skipping redirect for {old_path}")
                    missing_page += 1
                    continue

                normalised = Redirect.normalise_path(old_path)
                if Redirect.objects.filter(old_path=normalised, site=site).exists():
                    self.stdout.write(f"  skip (already exists): {old_path}")
                    skipped += 1
                    continue

                self.stdout.write(f"  {'[dry-run] ' if dry_run else ''}{old_path} -> {page}")
                if not dry_run:
                    Redirect.add_redirect(
                        old_path=old_path,
                        redirect_to=page,
                        site=site,
                        is_permanent=True,
                        automatically_created=True,
                    )
                created += 1

        self.stdout.write(f"Done. {created} created, {skipped} already existed, {missing_page} referenced a missing page.")
