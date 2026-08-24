# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Tests for the `cms_translation_draftsharing_create` view

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

import pytest
from wagtail.models import Revision
from wagtail_localize.models import StringSegment, StringTranslation
from wagtaildraftsharing.models import WagtaildraftsharingLink

from springfield.cms.tests.factories import WagtailUserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def editor():
    return WagtailUserFactory(is_superuser=True)


@pytest.fixture
def url():

    def _url(translation_id):
        return reverse("cms_translation_draftsharing_create", args=[translation_id])

    return _url


@pytest.fixture
def post(client, editor, translated_page_with_pending_edit, url):
    translation_id = translated_page_with_pending_edit.translation.pk

    def _post():
        client.force_login(editor)
        return client.post(url(translation_id))

    return _post


def test_url(url):
    assert url(123) == "/cms-admin/translation-draftsharing/123/"


def test_anonymous_user_not_permitted(client, translated_page_with_pending_edit, url):
    response = client.post(url(translated_page_with_pending_edit.translation.pk))

    assert response.status_code == 302
    assert response.url.startswith("/cms-admin/login/")
    assert WagtaildraftsharingLink.objects.exists() is False


def test_user_without_edit_permission_not_permitted(client, translated_page_with_pending_edit, url):
    no_access = WagtailUserFactory(username="no-access", is_superuser=False)
    client.force_login(no_access)

    response = client.post(url(translated_page_with_pending_edit.translation.pk))

    assert response.status_code == 302
    assert response.url.startswith("/cms-admin/login/")
    assert WagtaildraftsharingLink.objects.exists() is False


def test_get_is_rejected(client, editor, translated_page_with_pending_edit, url):
    client.force_login(editor)

    response = client.get(url(translated_page_with_pending_edit.translation.pk))

    assert response.status_code == 405


def test_unknown_translation_returns_404(client, editor, url):
    client.force_login(editor)

    response = client.post(url(999999), follow=True)

    assert response.status_code == 404
    assert WagtaildraftsharingLink.objects.exists() is False


def test_returns_sharing_url_without_changing_page(client, post, translated_page_with_pending_edit):
    response = post()

    assert response.status_code == 200

    sharing_link = WagtaildraftsharingLink.objects.get()
    revision = Revision.objects.for_instance(translated_page_with_pending_edit.page).order_by("-created_at").first()
    assert sharing_link.revision == revision
    expected_url = reverse("wagtaildraftsharing:view", args=[sharing_link.key])
    assert sharing_link.url == expected_url
    data = response.json()
    assert data["url"] == sharing_link.url

    client.logout()
    unpublished_text = "Passer à Firefox"

    # Shared page preview shows unpublished translation
    shared_response = client.get(sharing_link.url)

    assert shared_response.status_code == 200
    assert shared_response["X-Robots-Tag"] == "noindex, nofollow"
    assert unpublished_text in shared_response.content.decode()

    # Change to public page is not published
    public_response = client.get(translated_page_with_pending_edit.page.url)

    assert public_response.status_code == 200
    assert unpublished_text not in public_response.content.decode()


@pytest.fixture
def existing_sharing_link(editor, translated_page_with_pending_edit):
    """
    Sharing link for the `translated_page_with_pending_edit` fixture.
    """
    page = translated_page_with_pending_edit.page
    revision = Revision.objects.create(
        content_object=page,
        base_content_type=page.get_base_content_type(),
        user=editor,
        content=page.serializable_data(),
        object_str=str(page),
    )
    return WagtaildraftsharingLink.objects.create_for_revision(revision=revision, user=editor)


@pytest.fixture
def existing_sharing_url(existing_sharing_link):
    return existing_sharing_link.url


def test_reuses_existing_sharing_link(existing_sharing_url, post):
    existing_revision_count = Revision.objects.count()

    response = post()

    assert response.status_code == 200

    url = response.json()["url"]
    assert url == existing_sharing_url
    assert Revision.objects.count() == existing_revision_count
    assert WagtaildraftsharingLink.objects.count() == 1


def test_creates_new_sharing_link_for_edits(existing_sharing_url, post, translated_page_with_pending_edit):
    segment = StringSegment.objects.filter(source=translated_page_with_pending_edit.translation.source).first()
    StringTranslation.objects.filter(
        translation_of_id=segment.string_id,
        locale=translated_page_with_pending_edit.locale,
        context_id=segment.context_id,
    ).update(data="Encore changé", updated_at=timezone.now() + timedelta(minutes=5))

    response = post()

    assert response.status_code == 200

    url = response.json()["url"]
    assert url != existing_sharing_url
    assert WagtaildraftsharingLink.objects.count() == 2


def test_deactivated_sharing_link_is_not_reused(existing_sharing_url, post):
    WagtaildraftsharingLink.objects.update(is_active=False)

    response = post()

    assert response.status_code == 200

    url = response.json()["url"]
    assert url != existing_sharing_url


def test_expired_sharing_link_is_not_reused(existing_sharing_url, post):
    WagtaildraftsharingLink.objects.update(active_until=timezone.now() - timedelta(days=1))

    response = post()

    assert response.status_code == 200

    url = response.json()["url"]
    assert url != existing_sharing_url


def test_different_page_sharing_link_is_not_reused(editor, post, translated_page_with_pending_edit):
    source = translated_page_with_pending_edit.source_page.specific
    source_revision = Revision.objects.create(
        content_object=source,
        base_content_type=source.get_base_content_type(),
        user=editor,
        content=source.serializable_data(),
        object_str=str(source),
    )
    source_link = WagtaildraftsharingLink.objects.create_for_revision(revision=source_revision, user=editor)
    source_sharing_url = source_link.url

    response = post()

    assert response.status_code == 200

    url = response.json()["url"]
    assert url != source_sharing_url


def test_deletes_revision_whose_only_link_expired(existing_sharing_link, post):
    existing_sharing_link.active_until = timezone.now() - timedelta(days=1)
    existing_sharing_link.save(update_fields=["active_until"])
    # `existing_sharing_link` is now expired
    revision_with_expired_link = existing_sharing_link.revision

    response = post()

    assert response.status_code == 200
    with pytest.raises(Revision.DoesNotExist):
        revision_with_expired_link.refresh_from_db()
    with pytest.raises(WagtaildraftsharingLink.DoesNotExist):
        existing_sharing_link.refresh_from_db()


def test_deletes_revision_whose_only_link_is_inactive(existing_sharing_link, post):
    existing_sharing_link.is_active = False
    existing_sharing_link.save(update_fields=["is_active"])
    # `existing_sharing_link` is now inactive
    revision_with_expired_link = existing_sharing_link.revision

    response = post()

    assert response.status_code == 200
    with pytest.raises(Revision.DoesNotExist):
        revision_with_expired_link.refresh_from_db()
    with pytest.raises(WagtaildraftsharingLink.DoesNotExist):
        existing_sharing_link.refresh_from_db()


def test_does_not_delete_revision_with_one_active_link(editor, existing_sharing_link, post, translated_page_with_pending_edit):
    revision = existing_sharing_link.revision
    expired_sharing_link = WagtaildraftsharingLink.objects.create_for_revision(revision=revision, user=editor)
    expired_sharing_link.active_until = timezone.now() - timedelta(days=1)
    expired_sharing_link.save(update_fields=["active_until"])

    response = post()

    assert response.status_code == 200
    # No revisions or links deleted
    revision.refresh_from_db()
    existing_sharing_link.refresh_from_db()
    expired_sharing_link.refresh_from_db()


def test_does_not_delete_expired_link_revision_from_other_page(editor, existing_sharing_link, post, translated_page_with_pending_edit):
    source = translated_page_with_pending_edit.source_page.specific
    source_revision = Revision.objects.create(
        content_object=source,
        base_content_type=source.get_base_content_type(),
        user=editor,
        content=source.serializable_data(),
        object_str=str(source),
    )
    source_link = WagtaildraftsharingLink.objects.create_for_revision(revision=source_revision, user=editor)
    source_link.is_active = False
    source_link.save(update_fields=["is_active"])
    existing_revision_count = Revision.objects.count()

    response = post()

    assert response.status_code == 200
    # No revisions or links deleted
    assert Revision.objects.count() == existing_revision_count
    existing_sharing_link.refresh_from_db()
    source_link.refresh_from_db()
