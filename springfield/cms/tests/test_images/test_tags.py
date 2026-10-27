# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.base import ContentFile
from django.test import RequestFactory, override_settings
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from taggit.models import Tag
from wagtail.admin.menu import settings_menu
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.models import Collection, GroupCollectionPermission
from wagtail.search import index as search_index

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def image_editor_client(client):
    """Build a client logged in as a user who can change the images in one collection."""

    def build(collection):
        with override_settings(
            AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
            USE_SSO_AUTH=False,
        ):
            image_editors = Group.objects.create(name="Image editors")
            image_editors.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
            GroupCollectionPermission.objects.create(
                group=image_editors,
                collection=collection,
                permission=Permission.objects.get(content_type__app_label="wagtailimages", codename="change_image"),
            )
            image_editor = get_user_model().objects.create_user(username="image-editor", password="editorpass")
            image_editor.groups.add(image_editors)
            client.force_login(image_editor, backend="django.contrib.auth.backends.ModelBackend")
        return client

    return build


@pytest.fixture
def document_only_tag():
    document = get_document_model().objects.create(title="Brand guide", file=ContentFile(b"guide", "guide.txt"))
    document.tags.add("brand")
    return Tag.objects.get(name="brand")


def test_settings_menu_links_to_the_image_tags_listing(admin_user):
    # Resolving a URL loads the admin URLs, which is when viewsets register their menu items.
    listing_url = reverse("image_tags:index")
    request = RequestFactory().get("/")
    request.user = admin_user

    menu_items = {item.label: item.url for item in settings_menu.menu_items_for_request(request)}

    assert menu_items["Image tags"] == listing_url


def test_listing_shows_every_tag_alphabetically_with_its_image_count(admin_client, make_image):
    for image_number in range(2):
        make_image(title=f"Dark image {image_number}").tags.add("Dark Mode")
    make_image(title="Apple image").tags.add("apple")
    unused_tag = Tag.objects.create(name="unused")

    response = admin_client.get(reverse("image_tags:index"))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    rows = soup.select("#listing-results tbody tr")
    assert [row.select_one("td[data-inline-cell='name'] input")["value"] for row in rows] == ["apple", "Dark Mode", "unused"]
    apple_row, dark_mode_row, unused_row = rows

    apple_count_link = apple_row.select_one("td[data-inline-cell='image_count'] a")
    assert apple_count_link.get_text(strip=True) == "1"
    assert apple_count_link["href"] == f"{reverse('wagtailimages:index')}?tag=apple"

    dark_mode_count_link = dark_mode_row.select_one("td[data-inline-cell='image_count'] a")
    assert dark_mode_count_link.get_text(strip=True) == "2"
    assert dark_mode_count_link["href"] == f"{reverse('wagtailimages:index')}?tag=Dark%20Mode"

    unused_count_cell = unused_row.select_one("td[data-inline-cell='image_count']")
    assert unused_count_cell.get_text(strip=True) == "0"
    assert unused_count_cell.select_one("a") is None

    assert unused_row.select_one("td[data-inline-cell='save'] form")["action"] == reverse("image_tags:inline_edit", args=[unused_tag.pk])
    assert unused_row.select_one("td[data-inline-cell='save'] a")["href"] == reverse("image_tags:delete", args=[unused_tag.pk])


def test_listing_leaves_out_tags_used_only_by_other_models(admin_client, make_image, document_only_tag):
    make_image().tags.add("dark")

    response = admin_client.get(reverse("image_tags:index"))

    soup = BeautifulSoup(response.content, "html.parser")
    tag_names = [row.select_one("td[data-inline-cell='name'] input")["value"] for row in soup.select("#listing-results tbody tr")]
    assert tag_names == ["dark"]


def test_tags_used_only_by_other_models_cannot_be_renamed_or_deleted(admin_client, document_only_tag):
    admin_client.post(
        reverse("image_tags:inline_edit", args=[document_only_tag.pk]),
        {f"tag-{document_only_tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    admin_client.post(reverse("image_tags:delete", args=[document_only_tag.pk]))

    document_only_tag.refresh_from_db()
    assert document_only_tag.name == "brand"


def test_rename_saves_the_tag_and_reindexes_its_images(admin_client, make_image):
    image = make_image()
    image.tags.add("dark")
    tag = Tag.objects.get(name="dark")

    response = admin_client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    tag.refresh_from_db()
    assert tag.name == "midnight"
    assert tag.slug == "midnight"
    assert list(get_image_model().objects.search("midnight")) == [image]
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.select_one(f"input[name='tag-{tag.pk}-name']")["value"] == "midnight"
    assert soup.select_one("[role='status']").get_text(strip=True) == "Saved"
    image_count_link = soup.select_one("td[data-inline-cell='image_count'] a")
    assert image_count_link.get_text(strip=True) == "1"
    assert image_count_link["href"] == f"{reverse('wagtailimages:index')}?tag=midnight"


def test_rename_to_a_name_whose_slug_is_taken_suffixes_the_slug(admin_client, make_image):
    make_image().tags.add("dark", "Midnight")
    tag = Tag.objects.get(name="dark")

    admin_client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    tag.refresh_from_db()
    assert tag.name == "midnight"
    assert tag.slug == "midnight_1"


def test_rename_to_an_existing_tag_name_is_refused(admin_client, make_image):
    make_image().tags.add("desktop", "Desktop")
    tag = Tag.objects.get(name="Desktop")

    response = admin_client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "desktop"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    tag.refresh_from_db()
    assert tag.name == "Desktop"
    soup = BeautifulSoup(response.content, "html.parser")
    assert "already exists" in soup.select_one("td[data-inline-cell='name'] .error-message").get_text()
    assert soup.select_one("[role='status']").get_text(strip=True) == "Not saved"


def test_delete_removes_the_tag_from_its_images_and_reindexes_them(admin_client, make_image):
    image = make_image()
    image.tags.add("dark")
    search_index.insert_or_update_object(image)
    assert list(get_image_model().objects.search("dark")) == [image]
    tag = Tag.objects.get(name="dark")

    response = admin_client.post(reverse("image_tags:delete", args=[tag.pk]))

    assert response.status_code == 302
    assert not Tag.objects.filter(name="dark").exists()
    assert list(image.tags.all()) == []
    assert list(get_image_model().objects.search("dark")) == []


def test_users_who_can_only_add_images_cannot_rename_tags(uploader_client, make_image):
    make_image().tags.add("dark")
    tag = Tag.objects.get(name="dark")

    response = uploader_client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403
    tag.refresh_from_db()
    assert tag.name == "dark"


def test_users_who_can_only_add_images_cannot_delete_tags(uploader_client, make_image):
    make_image().tags.add("dark")
    tag = Tag.objects.get(name="dark")

    delete_response = uploader_client.post(reverse("image_tags:delete", args=[tag.pk]))

    assert delete_response.status_code == 302
    assert delete_response["Location"] == reverse("wagtailadmin_home")
    assert Tag.objects.filter(name="dark").exists()


def test_users_who_can_change_every_image_can_rename_tags(image_editor_client, make_image):
    make_image().tags.add("dark")
    tag = Tag.objects.get(name="dark")
    client = image_editor_client(Collection.get_first_root_node())

    response = client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    tag.refresh_from_db()
    assert tag.name == "midnight"


def test_users_who_can_change_images_in_one_sub_collection_cannot_rename_tags(image_editor_client, make_image):
    make_image().tags.add("dark")
    tag = Tag.objects.get(name="dark")
    client = image_editor_client(Collection.get_first_root_node().add_child(name="Campaigns"))

    response = client.post(
        reverse("image_tags:inline_edit", args=[tag.pk]),
        {f"tag-{tag.pk}-name": "midnight"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403
    tag.refresh_from_db()
    assert tag.name == "dark"


def test_delete_confirmation_shows_how_many_images_have_the_tag(admin_client, make_image):
    for image_number in range(2):
        make_image(title=f"Dark image {image_number}").tags.add("Dark Mode")
    tag = Tag.objects.get(name="Dark Mode")

    response = admin_client.get(reverse("image_tags:delete", args=[tag.pk]))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    usage_link = soup.select_one("main p a")
    assert usage_link.get_text(strip=True) == "This tag is used in 2 images."
    assert usage_link["href"] == f"{reverse('wagtailimages:index')}?tag=Dark%20Mode"
