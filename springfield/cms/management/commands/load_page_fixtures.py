# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.cms.fixtures.article_page_fixtures import get_article_pages
from springfield.cms.fixtures.banner_fixtures import get_banner_test_page
from springfield.cms.fixtures.base_fixtures import (
    get_2026_test_index_page,
    get_article_index_test_page,
    get_placeholder_images,
    get_test_index_page,
)
from springfield.cms.fixtures.button_fixtures import get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import (
    get_filled_cards_test_page,
    get_icon_cards_test_page,
    get_illustration_cards_test_page,
    get_step_cards_test_page,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.download_page_fixtures import get_download_pages
from springfield.cms.fixtures.homepage_fixtures import get_home_test_page
from springfield.cms.fixtures.inline_notification_fixtures import (
    get_inline_notification_test_page,
)
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page
from springfield.cms.fixtures.media_content_fixtures import get_media_content_test_page
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page


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

        index_page = get_test_index_page()
        if not no_refresh:
            index_page.get_children().delete()
            self.stdout.write(self.style.SUCCESS("Existing index page children deleted."))
        self.stdout.write(self.style.SUCCESS(f"Test index page loaded: {index_page.slug}"))

        index_page_2026 = get_2026_test_index_page()
        if not no_refresh:
            index_page_2026.get_children().delete()
            self.stdout.write(self.style.SUCCESS("Existing index page children deleted."))
        self.stdout.write(self.style.SUCCESS(f"2026 test index page loaded: {index_page_2026.slug}"))

        image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
        self.stdout.write(self.style.SUCCESS(f"Placeholder images loaded: {image.id}, {dark_image.id}, {mobile_image.id}, {dark_mobile_image.id}"))

        # 2026 pages

        snippet = get_pre_footer_cta_form_snippet()
        self.stdout.write(self.style.SUCCESS(f"Pre-Footer CTA Form Snippet loaded: {snippet.id}"))

        home_page = get_home_test_page()
        self.stdout.write(self.style.SUCCESS(f"Home test page loaded: {home_page.slug}"))

        download_pages = get_download_pages()
        for download_page in download_pages.values():
            self.stdout.write(self.style.SUCCESS(f"Download test page loaded: {download_page.slug}"))

        thanks_page = get_thanks_page()
        self.stdout.write(self.style.SUCCESS(f"Thanks test page loaded: {thanks_page.slug}"))

        article_index_page = get_article_index_test_page()
        self.stdout.write(self.style.SUCCESS(f"Article Index test page loaded: {article_index_page.slug}"))

        article_pages = get_article_pages()
        for page in article_pages:
            self.stdout.write(self.style.SUCCESS(f"Article test page loaded: {page.slug}"))

        # 2025 pages

        inline_notification_page = get_inline_notification_test_page()
        self.stdout.write(self.style.SUCCESS(f"Inline Notification test page loaded: {inline_notification_page.slug}"))

        intro_page = get_intro_test_page()
        self.stdout.write(self.style.SUCCESS(f"Intro test page loaded: {intro_page.slug}"))

        subscription_page = get_subscription_test_page()
        self.stdout.write(self.style.SUCCESS(f"Subscription test page loaded: {subscription_page.slug}"))

        media_content_page = get_media_content_test_page()
        self.stdout.write(self.style.SUCCESS(f"Media Content test page loaded: {media_content_page.slug}"))

        icon_cards_page = get_icon_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Icon Cards test page loaded: {icon_cards_page.slug}"))

        illustration_cards_page = get_illustration_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Illustration Cards test page loaded: {illustration_cards_page.slug}"))

        step_cards_page = get_step_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Step Cards test page loaded: {step_cards_page.slug}"))

        sticker_cards_page = get_sticker_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Sticker Cards test page loaded: {sticker_cards_page.slug}"))

        filled_cards_page = get_filled_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Filled Cards test page loaded: {filled_cards_page.slug}"))

        buttons_page = get_buttons_test_page()
        self.stdout.write(self.style.SUCCESS(f"Buttons test page loaded: {buttons_page.slug}"))

        banner_page = get_banner_test_page()
        self.stdout.write(self.style.SUCCESS(f"Banner test page loaded: {banner_page.slug}"))

        kit_banner_page = get_kit_banner_test_page()
        self.stdout.write(self.style.SUCCESS(f"Kit Banner test page loaded: {kit_banner_page.slug}"))

        self.stdout.write(self.style.SUCCESS("Successfully loaded page fixtures."))
