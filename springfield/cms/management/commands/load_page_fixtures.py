# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from springfield.cms.fixtures.banner_fixtures import get_banner_test_page
from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.button_fixtures import get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import (
    get_filled_cards_test_page,
    get_icon_cards_test_page,
    get_illustration_cards_test_page,
    get_step_cards_test_page,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.inline_notification_fixtures import get_inline_notification_test_page
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page
from springfield.cms.fixtures.media_content_fixtures import get_media_content_test_page
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page


class Command(BaseCommand):
    help = "Load page fixtures for testing."

    def handle(self, *args, **options):
        image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
        self.stdout.write(self.style.SUCCESS(f"Placeholder images loaded: {image.id}, {dark_image.id}, {mobile_image.id}, {dark_mobile_image.id}"))

        index_page = get_test_index_page()
        self.stdout.write(self.style.SUCCESS(f"Test index page loaded: {index_page.slug}"))

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
