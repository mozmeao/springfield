# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Collection, GroupCollectionPermission, ModelLogEntry

pytestmark = [pytest.mark.django_db]


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


def test_valid_post_saves_and_returns_the_row_cells(admin_client, make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    response = admin_client.post(
        reverse("cms_image_inline_edit", args=[image.pk]),
        {
            f"{prefix}-title": "Firefox logo on purple",
            f"{prefix}-description": "The Firefox logo on a purple background",
            f"{prefix}-tags": "brand, logo",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    image.refresh_from_db()
    assert image.title == "Firefox logo on purple"
    assert image.description == "The Firefox logo on a purple background"
    assert image.is_decorative is False
    assert set(image.tags.names()) == {"brand", "logo"}
    assert ModelLogEntry.objects.filter(object_id=str(image.pk), action="wagtail.edit").count() == 1
    soup = BeautifulSoup(response.content, "html.parser")
    assert [cell["data-inline-cell"] for cell in soup.select("td[data-inline-cell]")] == [
        "title",
        "description",
        "is_decorative",
        "tags",
        "save",
    ]
    assert soup.select_one(f"input[name='{prefix}-title']")["value"] == "Firefox logo on purple"
    assert soup.select_one(f"input[name='{prefix}-title']")["form"] == f"image-inline-{image.pk}"
    row_form = soup.select_one(f"form#image-inline-{image.pk}[data-inline-image-form]")
    assert row_form["action"] == reverse("cms_image_inline_edit", args=[image.pk])
    assert row_form.select_one("[role='status']").get_text(strip=True) == "Saved"
    assert image.filename in soup.select_one("td[data-inline-cell='title'] .filename-wrapper").get_text()


def test_invalid_post_returns_400_and_saves_nothing(admin_client, make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    response = admin_client.post(
        reverse("cms_image_inline_edit", args=[image.pk]),
        {f"{prefix}-title": "firefox_logo.png", f"{prefix}-description": "", f"{prefix}-tags": ""},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    image.refresh_from_db()
    assert image.title == "Firefox logo"
    assert image.description == "The Firefox logo"
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.select_one(f"input[name='{prefix}-title']")["value"] == "firefox_logo.png"
    assert "This looks like a file name" in soup.select_one("td[data-inline-cell='title'] .error-message").get_text()
    assert "Describe what this image shows" in soup.select_one("td[data-inline-cell='description'] .error-message").get_text()
    assert soup.select_one("[role='status']").get_text(strip=True) == "Not saved"


def test_overlong_title_is_a_field_error(admin_client, make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    response = admin_client.post(
        reverse("cms_image_inline_edit", args=[image.pk]),
        {f"{prefix}-title": "A" * 256, f"{prefix}-description": "The Firefox logo", f"{prefix}-tags": ""},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.select_one("td[data-inline-cell='title'] .error-message") is not None


def test_post_without_change_permission_is_forbidden(uploader_client, make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    response = uploader_client.post(
        reverse("cms_image_inline_edit", args=[image.pk]),
        {f"{prefix}-title": "Changed", f"{prefix}-description": "Changed", f"{prefix}-tags": ""},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403
    image.refresh_from_db()
    assert image.title == "Firefox logo"


def test_get_is_not_allowed(admin_client, make_image):
    image = make_image()

    response = admin_client.get(reverse("cms_image_inline_edit", args=[image.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 405


def test_missing_image_is_not_found(admin_client):
    response = admin_client.post(reverse("cms_image_inline_edit", args=[999999]), {}, follow=True, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 404
