# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.db import transaction

from springfield.cms.fixtures.article_page_fixtures import get_article_pages, get_article_theme_hub_page, get_article_theme_page
from springfield.cms.fixtures.banner_fixtures import get_banner_test_page
from springfield.cms.fixtures.base_fixtures import (
    get_article_index_test_page,
    get_placeholder_images,
    get_test_index_page,
)
from springfield.cms.fixtures.blog_fixtures import get_blog_index_page, get_blog_pages
from springfield.cms.fixtures.button_fixtures import get_buttons_test_page
from springfield.cms.fixtures.card_gallery_fixtures import get_card_gallery_test_page
from springfield.cms.fixtures.cards_fixtures import (
    get_illustration_cards_test_page,
    get_outlined_cards_test_page,
    get_step_cards_test_page,
    get_sticker_cards_test_page,
)
from springfield.cms.fixtures.carousel_fixtures import get_carousel_test_page
from springfield.cms.fixtures.conditional_display_fixtures import get_conditional_display_test_page
from springfield.cms.fixtures.download_page_fixtures import get_download_pages
from springfield.cms.fixtures.featured_image_section_fixtures import get_featured_image_section_test_page
from springfield.cms.fixtures.freeformpage import (
    get_freeform_page_test_page,
    get_freeform_page_with_floating_qr_snippet,
    get_freeform_page_with_qr_snippet,
    get_freeform_page_with_set_as_default_button,
    get_mobile_store_qr_code_test_page,
)
from springfield.cms.fixtures.homepage_fixtures import get_home_test_page
from springfield.cms.fixtures.icon_cards_fixtures import get_icon_cards_test_page
from springfield.cms.fixtures.icon_list_with_image_fixtures import get_icon_list_with_image_test_page
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page
from springfield.cms.fixtures.kit_intro_fixtures import get_kit_intro_test_page
from springfield.cms.fixtures.line_cards_fixtures import get_line_cards_test_page
from springfield.cms.fixtures.media_content_fixtures import get_media_content_test_page
from springfield.cms.fixtures.notification_fixtures import get_notification_test_page
from springfield.cms.fixtures.roadmap_list_fixtures import get_roadmap_list_test_page
from springfield.cms.fixtures.showcase_fixtures import get_showcase_test_page
from springfield.cms.fixtures.sliding_carousel_fixtures import get_sliding_carousel_test_page
from springfield.cms.fixtures.smart_window_explainer_page_fixtures import get_smart_window_explainer_test_page
from springfield.cms.fixtures.smart_window_page_fixtures import get_smart_window_test_page
from springfield.cms.fixtures.snippet_fixtures import get_pre_footer_cta_form_snippet, get_scroll_to_see_more_snippet
from springfield.cms.fixtures.testimonial_card_fixtures import get_testimonial_cards_test_page
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page
from springfield.cms.fixtures.topic_list_fixtures import get_topic_list_test_page
from springfield.cms.fixtures.two_column_cards_fixtures import get_two_column_cards_test_page
from springfield.cms.fixtures.whats_new_page_fixtures import (
    get_whats_new_page_with_floating_qr_snippet,
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

        image, dark_image, mobile_image, dark_mobile_image = get_placeholder_images()
        self.stdout.write(self.style.SUCCESS(f"Placeholder images loaded: {image.id}, {dark_image.id}, {mobile_image.id}, {dark_mobile_image.id}"))

        snippet = get_pre_footer_cta_form_snippet()
        self.stdout.write(self.style.SUCCESS(f"Pre-Footer CTA Form Snippet loaded: {snippet.id}"))

        scroll_to_see_more_snippet = get_scroll_to_see_more_snippet()
        self.stdout.write(self.style.SUCCESS(f"Scroll to See More Snippet loaded: {scroll_to_see_more_snippet.id}"))

        home_page = get_home_test_page()
        self.stdout.write(self.style.SUCCESS(f"Home test page loaded: {home_page.slug}"))

        mobile_store_qr_code_page = get_mobile_store_qr_code_test_page()
        self.stdout.write(self.style.SUCCESS(f"Mobile Store QR Code test page loaded: {mobile_store_qr_code_page.slug}"))

        freeform_page = get_freeform_page_test_page()
        self.stdout.write(self.style.SUCCESS(f"Free Form test page loaded: {freeform_page.slug}"))

        freeform_with_qr_snippet_page = get_freeform_page_with_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"Free Form with QR snippet test page loaded: {freeform_with_qr_snippet_page.slug}"))

        freeform_with_floating_qr_snippet_page = get_freeform_page_with_floating_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"Free Form with Floating QR snippet test page loaded: {freeform_with_floating_qr_snippet_page.slug}"))

        whats_new_page_with_floating_qr_snippet = get_whats_new_page_with_floating_qr_snippet()
        self.stdout.write(
            self.style.SUCCESS(f"What's New test page with Floating QR Code Snippet loaded: {whats_new_page_with_floating_qr_snippet.slug}")
        )

        intro_page = get_intro_test_page()
        self.stdout.write(self.style.SUCCESS(f"Intro test page loaded: {intro_page.slug}"))

        sticker_cards_page = get_sticker_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Sticker Cards test page loaded: {sticker_cards_page.slug}"))

        illustration_cards_page = get_illustration_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Illustration Cards test page loaded: {illustration_cards_page.slug}"))

        outlined_cards_page = get_outlined_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Outlined Cards test page loaded: {outlined_cards_page.slug}"))

        icon_cards_page = get_icon_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Icon Cards test page loaded: {icon_cards_page.slug}"))

        testimonial_cards_page = get_testimonial_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Testimonial Cards test page loaded: {testimonial_cards_page.slug}"))

        step_cards_page = get_step_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Step Cards test page loaded: {step_cards_page.slug}"))

        icon_list_with_image_page = get_icon_list_with_image_test_page()
        self.stdout.write(self.style.SUCCESS(f"Icon List with Image test page loaded: {icon_list_with_image_page.slug}"))

        line_cards_page = get_line_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Line Cards test page loaded: {line_cards_page.slug}"))

        roadmap_list_page = get_roadmap_list_test_page()
        self.stdout.write(self.style.SUCCESS(f"Roadmap List test page loaded: {roadmap_list_page.slug}"))

        showcase_page = get_showcase_test_page()
        self.stdout.write(self.style.SUCCESS(f"Showcase test page loaded: {showcase_page.slug}"))

        card_gallery_page = get_card_gallery_test_page()
        self.stdout.write(self.style.SUCCESS(f"Card Gallery test page loaded: {card_gallery_page.slug}"))

        notification_page = get_notification_test_page()
        self.stdout.write(self.style.SUCCESS(f"Notification test page loaded: {notification_page.slug}"))

        banner_page = get_banner_test_page()
        self.stdout.write(self.style.SUCCESS(f"Banner test page loaded: {banner_page.slug}"))

        conditional_display_page = get_conditional_display_test_page()
        self.stdout.write(self.style.SUCCESS(f"Conditional Display test page loaded: {conditional_display_page.slug}"))

        kit_banner_page = get_kit_banner_test_page()
        self.stdout.write(self.style.SUCCESS(f"Kit Banner test page loaded: {kit_banner_page.slug}"))

        buttons_page = get_buttons_test_page()
        self.stdout.write(self.style.SUCCESS(f"Buttons test page loaded: {buttons_page.slug}"))

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

        blog_index_page = get_blog_index_page()
        self.stdout.write(self.style.SUCCESS(f"Blog Index test page loaded: {blog_index_page.slug}"))

        blog_pages = get_blog_pages()
        for page in blog_pages:
            self.stdout.write(self.style.SUCCESS(f"Blog Article test page loaded: {page.slug}"))

        whats_new_index_page = get_whatsnew_index_page()
        self.stdout.write(self.style.SUCCESS(f"What's New Index test page loaded: {whats_new_index_page.slug}"))

        whats_new_page = get_whats_new_page_with_qr_snippet()
        self.stdout.write(self.style.SUCCESS(f"What's New with QR snippet test page loaded: {whats_new_page.slug}"))

        topic_list_page = get_topic_list_test_page()
        self.stdout.write(self.style.SUCCESS(f"Topic List test page loaded: {topic_list_page.slug}"))

        two_column_cards_page = get_two_column_cards_test_page()
        self.stdout.write(self.style.SUCCESS(f"Two Column Cards test page loaded: {two_column_cards_page.slug}"))

        set_as_default_page = get_freeform_page_with_set_as_default_button()
        self.stdout.write(self.style.SUCCESS(f"Free Form with Set as Default Button test page loaded: {set_as_default_page.slug}"))

        carousel_page = get_carousel_test_page()
        self.stdout.write(self.style.SUCCESS(f"Carousel test page loaded: {carousel_page.slug}"))

        sliding_carousel_page = get_sliding_carousel_test_page()
        self.stdout.write(self.style.SUCCESS(f"Sliding Carousel test page loaded: {sliding_carousel_page.slug}"))

        smart_window_explainer_page = get_smart_window_explainer_test_page()
        self.stdout.write(self.style.SUCCESS(f"Smart Window Explainer test page loaded: {smart_window_explainer_page.slug}"))

        smart_window_page = get_smart_window_test_page()
        self.stdout.write(self.style.SUCCESS(f"Smart Window test page loaded: {smart_window_page.slug}"))

        kit_intro_page = get_kit_intro_test_page()
        self.stdout.write(self.style.SUCCESS(f"Kit Intro test page loaded: {kit_intro_page.slug}"))

        featured_image_section_page = get_featured_image_section_test_page()
        self.stdout.write(self.style.SUCCESS(f"Featured Image Section test page loaded: {featured_image_section_page.slug}"))

        media_content_page = get_media_content_test_page()
        self.stdout.write(self.style.SUCCESS(f"Media Content test page loaded: {media_content_page.slug}"))

        self.stdout.write(self.style.SUCCESS("Successfully loaded page fixtures."))
