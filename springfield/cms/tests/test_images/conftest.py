# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.base import ContentFile
from django.test import override_settings

import pytest
from PIL import Image as PillowImage
from wagtail.models import Collection, GroupCollectionPermission, Page

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


@pytest.fixture
def uploader_client(client):
    """A logged-in editor who can upload images but can only change their own."""
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        uploaders = Group.objects.create(name="Image uploaders")
        uploaders.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
        GroupCollectionPermission.objects.create(
            group=uploaders,
            collection=Collection.get_first_root_node(),
            permission=Permission.objects.get(content_type__app_label="wagtailimages", codename="add_image"),
        )
        uploader = get_user_model().objects.create_user(username="uploader", password="uploaderpass")
        uploader.groups.add(uploaders)
        client.force_login(uploader, backend="django.contrib.auth.backends.ModelBackend")
        yield client
