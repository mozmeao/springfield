# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

from springfield.cms.fixtures.base_fixtures import get_2026_test_index_page, get_placeholder_images
from springfield.cms.models import FreeFormPage2026

_IMAGE_MEDIA = [
    {
        "type": "image",
        "value": {
            "image": settings.PLACEHOLDER_IMAGE_ID,
            "settings": {
                "dark_mode_image": settings.PLACEHOLDER_DARK_IMAGE_ID,
                "mobile_image": settings.PLACEHOLDER_MOBILE_IMAGE_ID,
                "dark_mode_mobile_image": settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
            },
        },
        "id": "2026shm1-0000-0000-0000-000000000001",
    }
]


def get_showcase_2026_variants() -> list[dict]:
    return [
        {
            "type": "showcase",
            "value": {
                "settings": {"layout": "default"},
                "headline": '<p data-block-key="2026sh1h">Showcase - Default Layout</p>',
                "media": _IMAGE_MEDIA,
                "caption_title": '<p data-block-key="2026sh1t">With caption title.</p>',
                "caption_description": '<p data-block-key="2026sh1d">The default layout places the image on one side '
                "with caption text beside it.</p>",
            },
            "id": "2026sh01-0000-0000-0000-000000000001",
        },
        {
            "type": "showcase",
            "value": {
                "settings": {"layout": "expanded"},
                "headline": '<p data-block-key="2026sh2h">Showcase - Expanded Layout</p>',
                "media": _IMAGE_MEDIA,
                "caption_title": "",
                "caption_description": '<p data-block-key="2026sh2d">The expanded layout gives more space to the image. '
                "No caption title in this variant.</p>",
            },
            "id": "2026sh01-0000-0000-0000-000000000002",
        },
        {
            "type": "showcase",
            "value": {
                "settings": {"layout": "full"},
                "headline": '<p data-block-key="2026sh3h">Showcase - Full Width Layout</p>',
                "media": _IMAGE_MEDIA,
                "caption_title": '<p data-block-key="2026sh3t">Full width caption title.</p>',
                "caption_description": '<p data-block-key="2026sh3d">The full layout spans the entire width of the container.</p>',
            },
            "id": "2026sh01-0000-0000-0000-000000000003",
        },
    ]


def get_showcase_2026_test_page() -> FreeFormPage2026:
    get_placeholder_images()
    index_page = get_2026_test_index_page()

    slug = "test-showcase-2026"
    page = FreeFormPage2026.objects.filter(slug=slug).first()
    if not page:
        page = FreeFormPage2026(slug=slug, title="Test Showcase 2026")
        index_page.add_child(instance=page)

    variants = get_showcase_2026_variants()
    page.upper_content = variants
    page.content = variants
    page.save_revision().publish()
    return page
