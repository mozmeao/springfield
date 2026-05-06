# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.icon_cards_2026_fixtures import get_icon_card_2026_variants
from springfield.cms.models import FreeFormPage2026

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


def get_featured_image_section_variants() -> list[dict]:
    icon_cards = get_icon_card_2026_variants()
    return [
        {
            "type": "featured_image_section",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="fis1s">Featured</p>',
                    "heading_text": '<p data-block-key="fis1h">Featured Image Section with Cards</p>',
                    "subheading_text": '<p data-block-key="fis1sub">A featured image section with a card list below.</p>',
                },
                "media": [
                    {
                        "type": "image",
                        "value": _IMAGE_VARIANTS,
                        "id": "fis00001-0000-0000-0000-000000000010",
                    }
                ],
                "content": [
                    {
                        "type": "cards_list",
                        "value": {
                            "settings": {"scroll": False},
                            "cards": icon_cards[:3],
                        },
                        "id": "fis00001-0000-0000-0000-000000000020",
                    }
                ],
            },
            "id": "fis00001-0000-0000-0000-000000000001",
        },
    ]


def get_featured_image_section_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-featured-image-section"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Featured Image Section")
        index_page.add_child(instance=page)

    variants = get_featured_image_section_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
