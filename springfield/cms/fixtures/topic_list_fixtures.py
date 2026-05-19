# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}


def _get_topics(anchor_prefix):
    buttons = get_button_variants()
    return [
        {
            "type": "item",
            "value": {
                "short_title": "Privacy Online",
                "anchor_id": f"{anchor_prefix}privacy-online",
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="tp01">Privacy Online</p>',
                    "subheading_text": "",
                },
                "content": '<p data-block-key="tp02">Firefox gives you more control over your online privacy. '
                "From tracking protection to enhanced private browsing, we keep your data yours.</p>",
                "buttons": [buttons["primary"], buttons["secondary"]],
            },
            "id": f"topic-{anchor_prefix}-0001",
        },
        {
            "type": "item",
            "value": {
                "short_title": "Speed & Performance",
                "anchor_id": f"{anchor_prefix}speed-performance",
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="tp03">Speed & Performance</p>',
                    "subheading_text": "",
                },
                "content": '<p data-block-key="tp04">Firefox is built to be fast where it matters most. '
                "A leaner memory footprint means your other programs can keep running smoothly.</p>",
                "buttons": [buttons["tertiary"]],
            },
            "id": f"topic-{anchor_prefix}-0002",
        },
        {
            "type": "item",
            "value": {
                "short_title": "Customization",
                "anchor_id": f"{anchor_prefix}customization",
                "image": settings.PLACEHOLDER_IMAGE_ID,
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="tp05">Customization</p>',
                    "subheading_text": "",
                },
                "content": '<p data-block-key="tp06">Make Firefox your own. '
                "Choose from thousands of extensions and themes to add features and change the look of your browser.</p>",
                "buttons": [],
            },
            "id": f"topic-{anchor_prefix}-0003",
        },
    ]


def get_topic_list_upper_variants():
    return [
        {
            "type": "topic_list",
            "value": {
                "topics": _get_topics("upper-"),
            },
            "id": "topic-list-upper-0001",
        },
    ]


def get_topic_list_lower_variants():
    return [
        {
            "type": "topic_list",
            "value": {
                "topics": _get_topics("lower-"),
            },
            "id": "topic-list-lower-0001",
        },
    ]


def get_topic_list_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    page = FreeFormPage2026.objects.filter(slug="test-topic-list-2026-page").first()
    if not page:
        page = FreeFormPage2026(
            slug="test-topic-list-2026-page",
            title="Test Topic List 2026 Page",
        )
        index_page.add_child(instance=page)

    page.upper_content = get_topic_list_upper_variants()
    page.content = get_topic_list_lower_variants()
    page.save_revision().publish()
    return page
