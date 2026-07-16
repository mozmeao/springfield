# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Central registry of the fixture functions that create CMS pages.

Each entry is a zero-argument callable that returns the page (or a list/dict of
pages) it creates. Used by the translate-all regression test and the
``load_page_fixtures`` command to avoid a duplicated call list.
"""

from springfield.cms.fixtures.article_page_fixtures import get_article_pages, get_article_theme_hub_page, get_article_theme_page
from springfield.cms.fixtures.banner_fixtures import get_banner_test_page
from springfield.cms.fixtures.base_fixtures import get_article_index_test_page
from springfield.cms.fixtures.blog_fixtures import get_blog_index_page, get_blog_pages
from springfield.cms.fixtures.button_fixtures import get_buttons_test_page
from springfield.cms.fixtures.card_fixtures import get_card_test_page
from springfield.cms.fixtures.card_gallery_fixtures import get_card_gallery_test_page
from springfield.cms.fixtures.cards_fixtures import (
    get_illustration_cards_test_page,
    get_outlined_cards_test_page,
    get_pictogram_cards_test_page,
    get_step_cards_test_page,
)
from springfield.cms.fixtures.carousel_fixtures import get_carousel_test_page
from springfield.cms.fixtures.conditional_display_fixtures import get_conditional_display_test_page
from springfield.cms.fixtures.contact_page_fixtures import get_contact_test_page
from springfield.cms.fixtures.download_page_fixtures import get_download_pages
from springfield.cms.fixtures.featured_image_section_fixtures import get_featured_image_section_test_page
from springfield.cms.fixtures.freeformpage import (
    get_banner_snippet_test_page,
    get_freeform_page_test_page,
    get_freeform_page_with_floating_qr_snippet,
    get_freeform_page_with_qr_snippet,
    get_freeform_page_with_set_as_default_button,
    get_mobile_store_qr_code_test_page,
    get_pencil_banner_snippet_test_page,
    get_pre_footer_cta_snippet_test_page,
    get_scroll_to_see_more_snippet_test_page,
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
from springfield.cms.fixtures.testimonial_card_fixtures import get_testimonial_cards_test_page
from springfield.cms.fixtures.thanks_page_fixtures import get_thanks_page
from springfield.cms.fixtures.topic_list_fixtures import get_topic_list_test_page
from springfield.cms.fixtures.two_column_cards_fixtures import get_two_column_cards_test_page
from springfield.cms.fixtures.whats_new_page_fixtures import (
    get_whats_new_page_with_floating_qr_snippet,
    get_whats_new_page_with_qr_snippet,
    get_whatsnew_index_page,
)

PAGE_FIXTURES = [
    get_home_test_page,
    get_mobile_store_qr_code_test_page,
    get_freeform_page_test_page,
    get_freeform_page_with_qr_snippet,
    get_freeform_page_with_floating_qr_snippet,
    get_freeform_page_with_set_as_default_button,
    get_whats_new_page_with_floating_qr_snippet,
    get_whats_new_page_with_qr_snippet,
    get_whatsnew_index_page,
    get_intro_test_page,
    get_kit_intro_test_page,
    get_card_test_page,
    get_pictogram_cards_test_page,
    get_illustration_cards_test_page,
    get_outlined_cards_test_page,
    get_icon_cards_test_page,
    get_testimonial_cards_test_page,
    get_step_cards_test_page,
    get_icon_list_with_image_test_page,
    get_line_cards_test_page,
    get_two_column_cards_test_page,
    get_roadmap_list_test_page,
    get_showcase_test_page,
    get_card_gallery_test_page,
    get_notification_test_page,
    get_banner_test_page,
    get_kit_banner_test_page,
    get_conditional_display_test_page,
    get_buttons_test_page,
    get_carousel_test_page,
    get_sliding_carousel_test_page,
    get_featured_image_section_test_page,
    get_media_content_test_page,
    get_topic_list_test_page,
    get_download_pages,
    get_thanks_page,
    get_contact_test_page,
    get_article_index_test_page,
    get_article_pages,
    get_article_theme_page,
    get_article_theme_hub_page,
    get_blog_index_page,
    get_blog_pages,
    get_smart_window_explainer_test_page,
    get_smart_window_test_page,
    get_banner_snippet_test_page,
    get_pencil_banner_snippet_test_page,
    get_pre_footer_cta_snippet_test_page,
    get_scroll_to_see_more_snippet_test_page,
]
