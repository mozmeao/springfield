# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.fixtures.button_fixtures import get_button_variants
from springfield.cms.models import FreeFormPage2026

_IMAGE_VARIANTS = {
    "image": settings.PLACEHOLDER_IMAGE_ID,
    "settings": {
        "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
        "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
    },
}


def get_card_gallery_2026_variants() -> list[dict]:
    buttons = get_button_variants()
    return [
        {
            "type": "card_gallery",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="2026cg1h">Card Gallery</p>',
                    "subheading_text": "",
                },
                "main_card": {
                    "icon": "themes",
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg1mh">Main Card Headline</p>',
                    "description": '<ul><li data-block-key="2026cg1md1">Feature one with rich text</li>'
                    '<li data-block-key="2026cg1md2">Feature two in a list</li>'
                    '<li data-block-key="2026cg1md3">Feature three with more detail</li></ul>',
                    "buttons": [buttons["primary"]],
                    "image": _IMAGE_VARIANTS,
                },
                "secondary_card": {
                    "icon": "shield",
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg1sh">Secondary Card Headline</p>',
                    "description": '<p data-block-key="2026cg1sd">Secondary card description with supporting text.</p>',
                    "buttons": [buttons["primary"]],
                    "image": _IMAGE_VARIANTS,
                },
                "callout_card": {
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg1ch">Callout Card Headline</p>',
                    "description": '<p data-block-key="2026cg1cd">Callout card description text.</p>',
                },
                "cta": [],
            },
            "id": "2026cg01-0000-0000-0000-000000000001",
        },
        {
            "type": "card_gallery",
            "value": {
                "heading": {
                    "superheading_text": '<p data-block-key="2026cg2sp">Firefox 2026</p>',
                    "heading_text": '<p data-block-key="2026cg2h">Card Gallery with Superheadings</p>',
                    "subheading_text": '<p data-block-key="2026cg2sub">All cards have superheadings and there is a CTA button.</p>',
                },
                "main_card": {
                    "icon": "lock",
                    "superheading": '<p data-block-key="2026cg2ms">Privacy</p>',
                    "headline": '<p data-block-key="2026cg2mh">Main Card with Superheading</p>',
                    "description": '<p data-block-key="2026cg2md">Main card with superheading and CTA button.</p>',
                    "buttons": [buttons["secondary"]],
                    "image": _IMAGE_VARIANTS,
                },
                "secondary_card": {
                    "icon": "checkmark-circle-fill",
                    "superheading": '<p data-block-key="2026cg2ss">Security</p>',
                    "headline": '<p data-block-key="2026cg2sh">Secondary Card with Superheading</p>',
                    "description": '<p data-block-key="2026cg2sd">Secondary card with superheading and CTA button.</p>',
                    "buttons": [buttons["secondary"]],
                    "image": _IMAGE_VARIANTS,
                },
                "callout_card": {
                    "superheading": '<p data-block-key="2026cg2cs">Your choice</p>',
                    "headline": '<p data-block-key="2026cg2ch">Callout Card with Superheading</p>',
                    "description": '<p data-block-key="2026cg2cd">Callout card with superheading.</p>',
                },
                "cta": [buttons["ghost"]],
            },
            "id": "2026cg01-0000-0000-0000-000000000002",
        },
        {
            "type": "card_gallery",
            "value": {
                "heading": {
                    "superheading_text": "",
                    "heading_text": '<p data-block-key="2026cg3h">Card Gallery without Buttons</p>',
                    "subheading_text": "",
                },
                "main_card": {
                    "icon": "extension",
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg3mh">Main Card - No Button</p>',
                    "description": '<p data-block-key="2026cg3md">Main card without a CTA button.</p>',
                    "buttons": [],
                    "image": _IMAGE_VARIANTS,
                },
                "secondary_card": {
                    "icon": "bookmark",
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg3sh">Secondary Card - No Button</p>',
                    "description": '<p data-block-key="2026cg3sd">Secondary card without a CTA button.</p>',
                    "buttons": [],
                    "image": _IMAGE_VARIANTS,
                },
                "callout_card": {
                    "superheading": "",
                    "headline": '<p data-block-key="2026cg3ch">Callout Card - No Superheading</p>',
                    "description": '<p data-block-key="2026cg3cd">Callout card without superheading.</p>',
                },
                "cta": [],
            },
            "id": "2026cg01-0000-0000-0000-000000000003",
        },
    ]


def get_card_gallery_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-card-gallery-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Card Gallery 2026")
        index_page.add_child(instance=page)

    variants = get_card_gallery_2026_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
