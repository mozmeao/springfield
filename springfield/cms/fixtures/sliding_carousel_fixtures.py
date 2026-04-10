# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026

_SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": ""}


def _image(image_id, dark_mode_image_id=None):
    return {
        "type": "image",
        "value": {
            "image": image_id,
            "settings": {
                "dark_mode_image": dark_mode_image_id,
                "mobile_image": None,
                "dark_mode_mobile_image": None,
            },
        },
        "id": None,
    }


def _heading(heading_text, superheading_text="", subheading_text=""):
    return {
        "superheading_text": f'<p data-block-key="slcah">{superheading_text}</p>',
        "heading_text": f'<p data-block-key="slcahh">{heading_text}</p>',
        "subheading_text": f'<p data-block-key="slcahs">{subheading_text}</p>',
    }


def get_sliding_carousel_slides() -> list[dict]:
    img = settings.PLACEHOLDER_IMAGE_ID
    dark = settings.PLACEHOLDER_DARK_IMAGE_ID
    return [
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Protect your privacy across the web",
                    superheading_text="Privacy",
                    subheading_text="Control who can see your browsing activity.",
                ),
                "media": [_image(img, dark)],
            },
            "id": "2026sc01-0000-0000-0000-000000000001",
        },
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Block trackers and ads automatically",
                    superheading_text="Security",
                    subheading_text="Enhanced Tracking Protection works out of the box.",
                ),
                "media": [_image(dark, img)],
            },
            "id": "2026sc01-0000-0000-0000-000000000002",
        },
        {
            "type": "item",
            "value": {
                "heading": _heading(
                    "Sync your data across all your devices",
                    superheading_text="Sync",
                    subheading_text="Bookmarks, passwords, and tabs — always with you.",
                ),
                "media": [_image(img)],
            },
            "id": "2026sc01-0000-0000-0000-000000000003",
        },
    ]


def get_sliding_carousel_variants() -> list[dict]:
    slides = get_sliding_carousel_slides()
    return [
        {
            "type": "sliding_carousel",
            "value": {
                "settings": {"show_to": _SHOW_TO_ALL},
                "slides": slides,
            },
            "id": "2026sc01-0000-0000-0000-000000000010",
        },
    ]


def get_sliding_carousel_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-sliding-carousel-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Sliding Carousel 2026")
        index_page.add_child(instance=page)

    variants = get_sliding_carousel_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
