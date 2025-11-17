# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from springfield.cms.fixtures.base_fixtures import get_placeholder_images, get_test_index_page
from springfield.cms.fixtures.card_fixtures import get_cards_test_page
from springfield.cms.fixtures.inline_notification_fixtures import get_inline_notification_test_page
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.media_content_fixtures import get_media_content_test_page
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page


class Command(BaseCommand):
    help = "Load page fixtures for testing."

    def handle(self, *args, **options):
        image, dark_image = get_placeholder_images()
        self.stdout.write(self.style.SUCCESS(f"Placeholder images loaded: {image.id}, {dark_image.id}"))

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

        cards_page = get_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Cards test page loaded: {cards_page.slug}"))

        self.stdout.write(self.style.SUCCESS("Successfully loaded page fixtures."))
