# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

from PIL import Image
from wagtail.models import Site

from springfield.cms.models import SpringfieldImage, StructuralPage


def get_placeholder_images():
    image = Image.new("RGB", (800, 450), (117, 79, 224))
    dark_image = Image.new("RGB", (800, 450), (255, 138, 80))
    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    dark_image_buffer = BytesIO()
    dark_image.save(dark_image_buffer, format="PNG")
    dark_image_buffer.seek(0)
    image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_IMAGE_ID,
        defaults={
            "title": "Placeholder Image for Testing",
            "file": ContentFile(image_buffer.read(), "placeholder_image.png"),
            "description": "An placeholder image used for testing purposes.",
        },
    )
    dark_image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_DARK_IMAGE_ID,
        defaults={
            "title": "Dark Mode Placeholder Image for Testing",
            "file": ContentFile(dark_image_buffer.read(), "dark_placeholder_image.png"),
            "description": "A dark mode placeholder image used for testing purposes.",
        },
    )

    return image, dark_image


def get_test_index_page():
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = StructuralPage.objects.filter(slug="tests-index-page").first()
    if not index_page:
        index_page = StructuralPage(
            slug="tests-index-page",
            title="Tests Index Page",
        )
        root_page.add_child(instance=index_page)
        index_page.save_revision().publish()
    return index_page
