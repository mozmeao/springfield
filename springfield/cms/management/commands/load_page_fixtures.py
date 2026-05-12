# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.cms.fixtures.article_page_fixtures import get_article_pages, get_article_theme_hub_page, get_article_theme_page
from springfield.cms.fixtures.banner_fixtures import get_banner_2026_test_page, get_banner_test_page
from springfield.cms.fixtures.base_fixtures import (
    get_2026_test_index_page,
    get_article_index_test_page,
    get_placeholder_images,
    get_test_index_page,
)
from springfield.cms.fixtures.button_fixtures import get_buttons_2026_test_page, get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import (
    get_filled_cards_test_page,
    get_icon_cards_test_page,
    get_illustration_cards_test_page,
    get_step_cards_test_page,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.card_gallery_2026_fixtures import get_card_gallery_2026_test_page
from springfield.cms.fixtures.cards_2026_fixtures import (
    get_illustration_cards_2026_test_page,
    get_outlined_cards_2026_test_page,
    get_step_cards_2026_test_page,
    get_sticker_cards_2026_test_page,
)
from springfield.cms.fixtures.carousel_2026_fixtures import get_carousel_2026_test_page
from springfield.cms.fixtures.download_page_fixtures import get_download_pages
from springfield.cms.fixtures.featured_image_section_fixtures import get_featured_image_section_test_page
from springfield.cms.fixtures.freeformpage_2026 import (
    get_freeform_page_2026_test_page,
    get_freeform_page_2026_with_floating_qr_snippet,
    get_freeform_page_2026_with_qr_snippet,
    get_freeform_page_2026_with_set_as_default_button,
    get_mobile_store_qr_code_test_page,
)
from springfield.cms.fixtures.homepage_fixtures import get_home_test_page
from springfield.cms.fixtures.icon_cards_2026_fixtures import get_icon_cards_2026_test_page
from springfield.cms.fixtures.icon_list_with_image_2026_fixtures import get_icon_list_with_image_test_page
from springfield.cms.fixtures.inline_notification_fixtures import (
    get_inline_notification_test_page,
)
from springfield.cms.fixtures.intro_2026_fixtures import get_intro_2026_test_page
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_2026_test_page, get_kit_banner_test_page
from springfield.cms.fixtures.kit_intro_2026_fixtures import get_kit_intro_2026_test_page
from springfield.cms.fixtures.line_cards_fixtures import get_line_cards_test_page
from springfield.cms.fixtures.media_content_2026_fixtures import get_media_content_2026_test_page
from springfield.cms.fixtures.media_content_fixtures import get_media_content_test_page
from springfield.cms.fixtures.notification_fixtures import get_notification_test_page
from springfield.cms.fixtures.showcase_2026_fixtures import get_showcase_2026_test_page
from springfield.cms.fixtures.sliding_carousel_fixtures import get_sliding_carousel_test_page
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import get_smart_window_explainer_test_page
from springfield.cms.fixtures.smart_window_page_fixtures import get_smart_window_test_page
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet
from springfield.cms.fixtures.subscription_fixtures import get_subscription_test_page
from springfield.cms.fixtures.testimonial_card_fixtures import get_testimonial_cards_2026_test_page
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page
from springfield.cms.fixtures.topic_list_fixtures import get_topic_list_2026_test_page
from springfield.cms.fixtures.whats_new_page_fixtures import (
    get_whats_new_page_2026_with_floating_qr_snippet,
    get_whats_new_page_2026_with_qr_snippet,
    get_whats_new_page_with_qr_snippet,
    get_whatsnew_index_page,
)


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

        mobile_store_qr_code_page = get_mobile_store_qr_code_test_page()
        self.stdout.write(self.style.SUCCESS(f"Mobile Store QR Code test page loaded: {mobile_store_qr_code_page.slug}"))

        freeform_2026_page = get_freeform_page_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Free Form 2026 test page loaded: {freeform_2026_page.slug}"))

        freeform_2026_with_qr_snippet_page = get_freeform_page_2026_with_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"Free Form 2026 with QR snippet test page loaded: {freeform_2026_with_qr_snippet_page.slug}"))

        freeform_2026_with_floating_qr_snippet_page = get_freeform_page_2026_with_floating_qr_snippet()
        self.stdout.write(
            self.style.SUCCESS(f"Free Form 2026 with Floating QR snippet test page loaded: {freeform_2026_with_floating_qr_snippet_page.slug}")
        )

        whats_new_page_2026_with_floating_qr_snippet = get_whats_new_page_2026_with_floating_qr_snippet()
        self.stdout.write(
            self.style.SUCCESS(f"What's New 2026 test page with Floating QR Code Snippet loaded: {whats_new_page_2026_with_floating_qr_snippet.slug}")
        )

        intro_2026_page = get_intro_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Intro 2026 test page loaded: {intro_2026_page.slug}"))

        sticker_cards_2026_page = get_sticker_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Sticker Cards 2026 test page loaded: {sticker_cards_2026_page.slug}"))

        illustration_cards_2026_page = get_illustration_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Illustration Cards 2026 test page loaded: {illustration_cards_2026_page.slug}"))

        outlined_cards_2026_page = get_outlined_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Outlined Cards 2026 test page loaded: {outlined_cards_2026_page.slug}"))

        icon_cards_2026_page = get_icon_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Icon Cards 2026 test page loaded: {icon_cards_2026_page.slug}"))

        testimonial_cards_2026_page = get_testimonial_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Testimonial Cards 2026 test page loaded: {testimonial_cards_2026_page.slug}"))

        step_cards_2026_page = get_step_cards_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Step Cards 2026 test page loaded: {step_cards_2026_page.slug}"))

        icon_list_with_image_page = get_icon_list_with_image_test_page()
        self.stdout.write(self.style.SUCCESS(f"Icon List with Image 2026 test page loaded: {icon_list_with_image_page.slug}"))

        line_cards_page = get_line_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Line Cards 2026 test page loaded: {line_cards_page.slug}"))

        showcase_2026_page = get_showcase_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Showcase 2026 test page loaded: {showcase_2026_page.slug}"))

        card_gallery_2026_page = get_card_gallery_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Card Gallery 2026 test page loaded: {card_gallery_2026_page.slug}"))

        notification_page = get_notification_test_page()
        self.stdout.write(self.style.SUCCESS(f"Notification test page loaded: {notification_page.slug}"))

        banner_2026_page = get_banner_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Banner 2026 test page loaded: {banner_2026_page.slug}"))

        kit_banner_2026_page = get_kit_banner_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Kit Banner 2026 test page loaded: {kit_banner_2026_page.slug}"))

        buttons_2026_page = get_buttons_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Buttons 2026 test page loaded: {buttons_2026_page.slug}"))

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

        article_theme_page = get_article_theme_page()
        self.stdout.write(self.style.SUCCESS(f"Article Theme test page loaded: {article_theme_page.slug}"))

        article_theme_hub_page = get_article_theme_hub_page()
        self.stdout.write(self.style.SUCCESS(f"Article Theme Hub test page loaded: {article_theme_hub_page.slug}"))

        whats_new_index_page = get_whatsnew_index_page()
        self.stdout.write(self.style.SUCCESS(f"What's New Index test page loaded: {whats_new_index_page.slug}"))

        whats_new_page_2026 = get_whats_new_page_2026_with_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"What's New 2026 with QR snippet test page loaded: {whats_new_page_2026.slug}"))

        topic_list_2026_page = get_topic_list_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Topic List 2026 test page loaded: {topic_list_2026_page.slug}"))

        set_as_default_page = get_freeform_page_2026_with_set_as_default_button()
        self.stdout.write(self.style.SUCCESS(f"Free Form 2026 with Set as Default Button test page loaded: {set_as_default_page.slug}"))

        carousel_page = get_carousel_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Carousel 2026 test page loaded: {carousel_page.slug}"))

        sliding_carousel_page = get_sliding_carousel_test_page()
        self.stdout.write(self.style.SUCCESS(f"Sliding Carousel 2026 test page loaded: {sliding_carousel_page.slug}"))

        smart_window_explainer_page = get_smart_window_explainer_test_page()
        self.stdout.write(self.style.SUCCESS(f"Smart Window Explainer test page loaded: {smart_window_explainer_page.slug}"))

        smart_window_page = get_smart_window_test_page()
        self.stdout.write(self.style.SUCCESS(f"Smart Window test page loaded: {smart_window_page.slug}"))

        kit_intro_page = get_kit_intro_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Kit Intro 2026 test page loaded: {kit_intro_page.slug}"))

        featured_image_section_page = get_featured_image_section_test_page()
        self.stdout.write(self.style.SUCCESS(f"Featured Image Section test page loaded: {featured_image_section_page.slug}"))

        media_content_page = get_media_content_2026_test_page()
        self.stdout.write(self.style.SUCCESS(f"Media Content 2026 test page loaded: {media_content_page.slug}"))

        # 2025 pages

        whats_new_page_2025 = get_whats_new_page_with_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"What's New with QR snippet test page loaded: {whats_new_page_2025.slug}"))

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
