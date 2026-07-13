# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.cms.fixtures.base_fixtures import get_flare_docs_index_page, get_placeholder_images
from springfield.cms.fixtures.navigation_fixtures import get_navigation_snippet
from springfield.cms.fixtures.registry import PAGE_FIXTURES
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet, get_scroll_to_see_more_snippet


def _as_pages(result):
    """Normalise a fixture's return value (a page, list, or dict of pages) to a list of pages."""
    if isinstance(result, dict):
        return list(result.values())
    if isinstance(result, (list, tuple)):
        return list(result)
    return [result]


class Command(BaseCommand):
    help = "Load page fixtures for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-refresh",
            action="store_true",
            help="Do not delete existing images and pages.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        no_refresh = options["no_refresh"]

        index_page = get_flare_docs_index_page()
        if not no_refresh:
            index_page.get_children().delete()
            self.stdout.write(self.style.SUCCESS("Existing index page children deleted."))
        self.stdout.write(self.style.SUCCESS(f"Test index page loaded: {index_page.slug}"))

        image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
        self.stdout.write(self.style.SUCCESS(f"Placeholder images loaded: {image.id}, {dark_image.id}, {mobile_image.id}, {dark_mobile_image.id}"))

        snippet = get_pre_footer_cta_form_snippet()
        self.stdout.write(self.style.SUCCESS(f"Pre-Footer CTA Form Snippet loaded: {snippet.id}"))

        scroll_to_see_more_snippet = get_scroll_to_see_more_snippet()
        self.stdout.write(self.style.SUCCESS(f"Scroll to See More Snippet loaded: {scroll_to_see_more_snippet.id}"))

        navigation_snippet = get_navigation_snippet()
        self.stdout.write(self.style.SUCCESS(f"Navigation Snippet loaded: {navigation_snippet.id}"))

        for fixture in PAGE_FIXTURES:
            for page in _as_pages(fixture()):
                self.stdout.write(self.style.SUCCESS(f"{fixture.__name__} loaded: {page.slug}"))

        self.stdout.write(self.style.SUCCESS("Successfully loaded page fixtures."))
