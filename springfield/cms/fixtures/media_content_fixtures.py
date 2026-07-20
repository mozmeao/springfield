# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_flare_blocks_docs_page, get_or_create_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.fixtures.video_fixtures import get_video_variants
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


_TAGS = [
    {
        "type": "item",
        "value": {"title": "Privacy", "icon": "warning", "icon_position": "before", "color": "purple"},
        "id": "2026mct1-0000-0000-0000-000000000001",
    },
    {
        "type": "item",
        "value": {"title": "Security", "icon": "lock", "icon_position": "before", "color": "red"},
        "id": "2026mct1-0000-0000-0000-000000000002",
    },
    {
        "type": "item",
        "value": {"title": "Speed", "icon": "trending", "icon_position": "before", "color": "orange"},
        "id": "2026mct1-0000-0000-0000-000000000003",
    },
    {
        "type": "item",
        "value": {"title": "Open Source", "icon": "edit-active", "icon_position": "after", "color": "green"},
        "id": "2026mct1-0000-0000-0000-000000000004",
    },
    {
        "type": "item",
        "value": {"title": "Mobile", "icon": "android", "icon_position": "before", "color": "orange"},
        "id": "2026mct1-0000-0000-0000-000000000005",
    },
    {
        "type": "item",
        "value": {"title": "Desktop", "icon": "apple", "icon_position": "after", "color": "purple"},
        "id": "2026mct1-0000-0000-0000-000000000006",
    },
    {
        "type": "item",
        "value": {"title": "Sync", "icon": "translate", "icon_position": "before", "color": "green"},
        "id": "2026mct1-0000-0000-0000-000000000007",
    },
    {
        "type": "item",
        "value": {"title": "New", "icon": "trending", "icon_position": "after", "color": "red"},
        "id": "2026mct1-0000-0000-0000-000000000008",
    },
    {
        "type": "item",
        "value": {"title": "Ad-free", "icon": "bookmark", "icon_position": "before", "color": "purple"},
        "id": "2026mct1-0000-0000-0000-000000000009",
    },
]


def _section(heading_text, content_blocks, section_id, subheading_text=""):
    return {
        "type": "section",
        "value": {
            "settings": {
                "show_to": _SHOW_TO_ALL,
                "anchor_id": "",
            },
            "heading": {
                "superheading_text": "",
                "heading_text": f'<p data-block-key="mc2026h">{heading_text}</p>',
                "subheading_text": f'<p data-block-key="mc2026s">{subheading_text}</p>' if subheading_text else "",
            },
            "content": content_blocks,
            "cta": [],
        },
        "id": section_id,
    }


def get_media_content_variants() -> list[dict]:
    buttons = get_button_variants()
    videos = get_video_variants()
    return [
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "2026mc01-0000-0000-0000-000000000010",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="2026mc1e">Eyebrow</p>',
                    "heading_text": '<p data-block-key="2026mc1h">Media Content 2026 — Content Before</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "2026mc01-0000-0000-0000-000000000012", "value": _TAGS[:3]},
                    {
                        "type": "rich_text",
                        "id": "2026mc01-0000-0000-0000-000000000011",
                        "value": (
                            '<p data-block-key="2026mc1c">Media content block in the 2026 design system. Visit the'
                            ' <a href="https://www.mozilla.org"'
                            ' uid="20260001-aaaa-aaaa-aaaa-000000000001">Mozilla website</a> for more.</p>'
                        ),
                    },
                    {"type": "buttons", "id": "2026mc01-0000-0000-0000-000000000013", "value": [buttons["primary"]]},
                ],
            },
            "id": "2026mc01-0000-0000-0000-000000000001",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True},
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "2026mc01-0000-0000-0000-000000000020",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="2026mc2e">Eyebrow</p>',
                    "heading_text": '<p data-block-key="2026mc2h">Media Content 2026 — Media Before</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "2026mc01-0000-0000-0000-000000000022", "value": _TAGS[3:6]},
                    {
                        "type": "rich_text",
                        "id": "2026mc01-0000-0000-0000-000000000021",
                        "value": '<p data-block-key="2026mc2c">Media content block with media on the left side.</p>',
                    },
                    {"type": "buttons", "id": "2026mc01-0000-0000-0000-000000000023", "value": [buttons["secondary"]]},
                ],
            },
            "id": "2026mc01-0000-0000-0000-000000000002",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False},
                "media": [videos["youtube"]],
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="2026mc3h">Media Content 2026 — Video</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "2026mc01-0000-0000-0000-000000000032", "value": _TAGS[6:9]},
                    {
                        "type": "rich_text",
                        "id": "2026mc01-0000-0000-0000-000000000031",
                        "value": '<p data-block-key="2026mc3c">Media content block with a YouTube video.</p>',
                    },
                    {"type": "buttons", "id": "2026mc01-0000-0000-0000-000000000033", "value": [buttons["ghost"]]},
                ],
            },
            "id": "2026mc01-0000-0000-0000-000000000003",
        },
    ]


def get_media_content_narrow_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": False, "narrow": True},
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "2026mcn1-0000-0000-0000-000000000010",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="2026mcn1e">Narrow Layout</p>',
                    "heading_text": '<p data-block-key="2026mcn1h">Narrow — Media Right</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "2026mcn1-0000-0000-0000-000000000012", "value": _TAGS[:2]},
                    {
                        "type": "rich_text",
                        "id": "2026mcn1-0000-0000-0000-000000000011",
                        "value": '<p data-block-key="2026mcn1c">Narrow layout narrows the media column, giving more space to the content.</p>',
                    },
                    {"type": "buttons", "id": "2026mcn1-0000-0000-0000-000000000013", "value": [buttons["primary"]]},
                ],
            },
            "id": "2026mcn1-0000-0000-0000-000000000001",
        },
        {
            "type": "media_content",
            "value": {
                "settings": {"media_after": True, "narrow": True},
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "2026mcn2-0000-0000-0000-000000000020",
                    }
                ],
                "heading": {
                    "superheading_text": '<p data-block-key="2026mcn2e">Narrow Layout</p>',
                    "heading_text": '<p data-block-key="2026mcn2h">Narrow — Media Left</p>',
                    "subheading_text": "",
                },
                "content": [
                    {"type": "tags", "id": "2026mcn2-0000-0000-0000-000000000022", "value": _TAGS[3:5]},
                    {
                        "type": "rich_text",
                        "id": "2026mcn2-0000-0000-0000-000000000021",
                        "value": '<p data-block-key="2026mcn2c">Narrow layout with media on the left side.</p>',
                    },
                    {"type": "buttons", "id": "2026mcn2-0000-0000-0000-000000000023", "value": [buttons["secondary"]]},
                ],
            },
            "id": "2026mcn2-0000-0000-0000-000000000002",
        },
    ]


def get_media_content_sections() -> list[dict]:
    return [
        _section(
            heading_text="Media + Content 2026",
            subheading_text="Media content blocks in the 2026 design system.",
            content_blocks=get_media_content_variants(),
            section_id="2026mcs1-0000-0000-0000-000000000001",
        ),
        _section(
            heading_text="Media + Content 2026 — Narrow",
            subheading_text="Narrow layout narrows the media element relative to the content.",
            content_blocks=get_media_content_narrow_variants(),
            section_id="2026mcs1-0000-0000-0000-000000000002",
        ),
    ]


def get_media_content_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_flare_blocks_docs_page()

    slug = "test-media-content"
    page = get_or_create_page(
        FreeFormPage2026,
        slug=slug,
        parent=index_page,
        defaults={
            "title": "Media Content",
        },
    )

    sections = get_media_content_sections()
    page.upper_content = sections
    page.content = sections
    page.docs = (
        "<p>The Media Content block places a media element (image or video) alongside a content column (heading, body, buttons). "
        "It&rsquo;s the building block for alternating media-text sections that make up product feature pages.</p>"
        "<p>Alternate the media position (left / right) across consecutive blocks to keep the page rhythm engaging. Provide alt "
        "text on every image; for video, set the autoplay variant only when sound is not required.</p>"
    )
    page.save_revision().publish()
    return page
