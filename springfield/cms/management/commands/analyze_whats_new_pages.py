# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Management command to analyze published WhatsNewPage instances and write a
summary to a markdown file for use in migration planning.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand

from wagtail.models import Locale


class Command(BaseCommand):
    help = "Analyze published WhatsNewPage instances and write a summary markdown file."

    def handle(self, *args, **options):
        from springfield.cms.models import WhatsNewPage

        en_us_locale = Locale.objects.get(language_code="en-US")
        pages = WhatsNewPage.objects.filter(locale=en_us_locale, live=True).order_by("slug")

        output_path = os.path.join(settings.ROOT_PATH, "whats_new_pages.md")

        lines = ["# Published WhatsNewPage Instances", ""]

        for page in pages:
            lines.append(f"## {page.title}")
            lines.append("")
            lines.append(f"- **Slug:** {page.slug}")
            lines.append(f"- **Version:** {page.version}")
            lines.append(f"- **Full URL:** {page.full_url}")
            lines.append("")

            translations = page.get_translations(inclusive=False)
            if translations.exists():
                lines.append("### Translations")
                lines.append("")
                for translation in translations.order_by("locale__language_code"):
                    lines.append(f"- **{translation.locale.language_code}**, live: {translation.live}")
                lines.append("")
            else:
                lines.append("_No translations found._")
                lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        self.stdout.write(self.style.SUCCESS(f"Successfully wrote {output_path}"))
