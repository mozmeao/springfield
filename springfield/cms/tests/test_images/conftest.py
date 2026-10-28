# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from unittest.mock import patch

from django.core.files.base import ContentFile

import pytest
from PIL import Image as PillowImage
from wagtail.models import Page

from springfield.cms.models.images import SpringfieldImage


@pytest.fixture
def make_image():
    """Build one saved SpringfieldImage, with the rendition pre-generation stubbed out."""

    def build(**fields):
        buffer = BytesIO()
        PillowImage.new("RGB", (400, 300), (117, 79, 224)).save(buffer, format="PNG")
        buffer.seek(0)
        with patch.object(SpringfieldImage, "_pre_generate_expected_renditions"):
            return SpringfieldImage.objects.create(
                file=ContentFile(buffer.read(), "placeholder.png"),
                **{"title": "Firefox logo", "description": "The Firefox logo", **fields},
            )

    return build


@pytest.fixture
def root_page(db):
    return Page.get_first_root_node()
