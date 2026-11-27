# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from PIL import Image as PillowImage
from wagtail.models import Collection

from springfield.cms.models.images import SpringfieldImage

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def stub_rendition_pre_generation():
    with patch.object(SpringfieldImage, "_pre_generate_expected_renditions"):
        yield


def png_upload(width, height):
    buffer = BytesIO()
    PillowImage.new("RGB", (width, height), (117, 79, 224)).save(buffer, format="PNG")
    return SimpleUploadedFile("upload.png", buffer.getvalue(), content_type="image/png")


def test_add_view_tags_the_uploaded_image(admin_client):
    admin_client.post(
        reverse("wagtailimages:add"),
        {"title": "Hero", "description": "A hero", "file": png_upload(1920, 1080)},
    )

    assert list(SpringfieldImage.objects.get(title="Hero").tags.names()) == ["16:9"]


def test_edit_view_replacing_the_file_swaps_the_ratio_tag(admin_client, make_image):
    image = make_image()
    image.tags.add("4:3", "brand")

    admin_client.post(
        reverse("wagtailimages:edit", args=[image.pk]),
        {"title": image.title, "description": image.description, "tags": "4:3, brand", "file": png_upload(1080, 1920)},
    )

    assert sorted(image.tags.names()) == ["9:16", "brand"]


def test_multiple_upload_tags_the_image_once_its_details_are_filled_in(admin_client):
    # The model rejects a filename title and a missing description, so the upload step alone
    # never saves an image: it is stored as an UploadedFile until the editor fills in the card.
    upload_response = admin_client.post(
        reverse("wagtailimages:add_multiple"),
        {"files[]": png_upload(1500, 1000), "collection": Collection.get_first_root_node().pk},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    uploaded_file_id = upload_response.json()["uploaded_file_id"]
    prefix = f"uploaded-image-{uploaded_file_id}"

    admin_client.post(
        reverse("wagtailimages:create_multiple_from_uploaded_image", args=[uploaded_file_id]),
        {
            f"{prefix}-title": "Wide photo",
            f"{prefix}-description": "A wide photo",
            f"{prefix}-collection": Collection.get_first_root_node().pk,
        },
    )

    assert list(SpringfieldImage.objects.get().tags.names()) == ["3:2"]


def test_inline_edit_restores_a_removed_ratio_tag(admin_client, make_image):
    image = make_image()
    image.tags.add("4:3")

    response = admin_client.post(
        reverse("cms_image_inline_edit", args=[image.pk]),
        {
            f"image-{image.pk}-title": image.title,
            f"image-{image.pk}-description": image.description,
            f"image-{image.pk}-tags": "",
        },
    )

    assert list(image.tags.names()) == ["4:3"]
    tags_input = BeautifulSoup(response.content, "html.parser").select_one(f"input[name='image-{image.pk}-tags']")
    assert tags_input["value"] == "4:3"


def test_edit_page_warns_when_close_to_a_ratio(admin_client, make_image):
    image = make_image()
    SpringfieldImage.objects.filter(pk=image.pk).update(width=1920, height=1050)

    response = admin_client.get(reverse("wagtailimages:edit", args=[image.pk]))

    content = response.content.decode()
    assert "This image is close to 16:9 (1920×1050) but not exact. Check the cropping." in content
    assert "Supported formats" in content


def test_edit_page_has_no_warning_for_an_exact_ratio(admin_client, make_image):
    image = make_image()

    response = admin_client.get(reverse("wagtailimages:edit", args=[image.pk]))

    assert "but not exact" not in response.content.decode()
