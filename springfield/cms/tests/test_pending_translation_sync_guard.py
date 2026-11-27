# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Syncing translated pages is refused for non-superusers while a page has content at Smartling."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import override_settings
from django.urls import reverse

import pytest
from wagtail.models import GroupPagePermission, Page
from wagtail_localize.models import TranslationSource

from springfield.cms.tests.test_pending_translation_lock import make_pending_job

pytestmark = [pytest.mark.django_db]

User = get_user_model()


@pytest.fixture
def syncer():
    """A staff user who *can* sync: they hold wagtail_localize.submit_translation.

    Without it UpdateTranslationsView.dispatch() raises PermissionDenied, which the
    admin turns into a redirect (the same behaviour as the guard's own refusal), so the
    assertions below could not tell the two apart.
    """
    group = Group.objects.create(name="WT-1854 syncers")
    for root in Page.objects.filter(depth=1):
        for codename in ("change_page", "publish_page"):
            GroupPagePermission.objects.create(
                group=group,
                page=root,
                permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
            )
    group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
    group.permissions.add(Permission.objects.get(content_type__app_label="wagtail_localize", codename="submit_translation"))
    user = User.objects.create_user(
        username="syncer",
        email="syncer@example.com",
        password="pass",
        is_staff=True,
    )
    user.groups.add(group)
    return user


@pytest.fixture
def syncer_client(client, syncer):
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        client.force_login(syncer, backend="django.contrib.auth.backends.ModelBackend")
        yield client


def get_queued_messages(response):
    """
    The messages a redirect leaves in the cookie, which nothing has rendered yet.

    Reading them back is the only way to see a message on a response that redirects.
    """
    cookie = response.cookies.get("messages")
    if cookie is None or not cookie.value:
        return []
    return CookieStorage(response.wsgi_request)._decode(cookie.value) or []


def sync_url(source_page):
    source = TranslationSource.objects.get_for_instance(source_page)
    return reverse("wagtail_localize:update_translations", args=[source.id])


def test_syncer_without_an_outstanding_job_is_not_blocked(translated_page, syncer_client):
    response = syncer_client.get(sync_url(translated_page.source_page))
    assert response.status_code == 200


def test_get_is_refused_while_a_job_is_outstanding(translated_page, syncer, syncer_client):
    make_pending_job(translated_page.source_page, [translated_page.locale], syncer)

    response = syncer_client.get(sync_url(translated_page.source_page))

    assert response.status_code == 302
    assert reverse("wagtailadmin_pages:edit", args=[translated_page.source_page.id]) in response["Location"]


def test_post_is_refused_while_a_job_is_outstanding(translated_page, syncer, syncer_client):
    make_pending_job(translated_page.source_page, [translated_page.locale], syncer)
    source = TranslationSource.objects.get_for_instance(translated_page.source_page)
    last_updated_at = source.last_updated_at

    response = syncer_client.post(sync_url(translated_page.source_page), {})

    # The edit URL, not just any 302: a successful sync redirects too, to the explorer.
    assert response.status_code == 302
    assert reverse("wagtailadmin_pages:edit", args=[translated_page.source_page.id]) in response["Location"]
    # The warning message is queued in a cookie.
    expected_message_text = (
        "This page is being translated in Smartling. Changing a field now would "
        "create a mismatch between the changed text, and the text translated in "
        "Smartling."
    )
    matching_messages = [message for message in get_queued_messages(response) if str(message) == expected_message_text]
    assert len(matching_messages) == 1
    assert matching_messages[0].level == messages.ERROR
    # Re-snapshotting stamps last_updated_at, so an unchanged stamp means the source
    # still holds the text Smartling was given.
    source.refresh_from_db()
    assert source.last_updated_at == last_updated_at


def test_the_refusal_explains_itself(translated_page, syncer, syncer_client):
    make_pending_job(translated_page.source_page, [translated_page.locale], syncer)

    response = syncer_client.get(sync_url(translated_page.source_page), follow=True)

    expected_message_text = (
        "This page is being translated in Smartling. Changing a field now would create "
        "a mismatch between the changed text, and the text translated in Smartling."
    )
    matching_messages = [message for message in response.context["messages"] if str(message) == expected_message_text]
    assert len(matching_messages) == 1
    assert matching_messages[0].level == messages.ERROR


def test_superuser_get_sync_is_not_blocked(translated_page, admin_client):
    superuser = User.objects.get(username="admin")
    assert superuser.is_superuser

    make_pending_job(translated_page.source_page, [translated_page.locale], superuser)

    response = admin_client.get(sync_url(translated_page.source_page))

    assert response.status_code == 200
    # The superuser sees a warning about syncing the page while it is being
    # translated in Smartling.
    expected_message_text = (
        "This page is being translated in Smartling into French. Syncing now "
        "would create a mismatch between the changed text, and the text "
        "translated in Smartling."
    )
    matching_messages = [message for message in response.context["messages"] if str(message) == expected_message_text]
    assert len(matching_messages) == 1
    assert matching_messages[0].level == messages.WARNING


def test_superuser_post_sync_is_not_warned_after_the_fact(translated_page, admin_client):
    """The POST redirects onwards, so a message queued here would surface on the next
    page, after the sync it was meant to warn about has already run."""
    superuser = User.objects.get(username="admin")
    make_pending_job(translated_page.source_page, [translated_page.locale], superuser)

    response = admin_client.post(sync_url(translated_page.source_page), {})

    # The view queues its own success message here, so this has to look at the levels
    # rather than at whether anything was queued at all.
    assert not [message for message in get_queued_messages(response) if message.level == messages.WARNING]


def test_superuser_get_sync_is_not_warned_when_nothing_is_in_flight(translated_page, admin_client):
    response = admin_client.get(sync_url(translated_page.source_page))
    assert not [message for message in response.context["messages"] if message.level == messages.WARNING]


def test_superuser_post_sync_is_not_blocked(translated_page, admin_client, mocker):
    superuser = User.objects.get(username="admin")
    assert superuser.is_superuser
    make_pending_job(translated_page.source_page, [translated_page.locale], superuser)
    spy = mocker.spy(TranslationSource, "update_from_db")

    response = admin_client.post(sync_url(translated_page.source_page), {})

    # Sent onwards by the view, not bounced back to the page by the guard.
    assert response.status_code == 302
    assert reverse("wagtailadmin_pages:edit", args=[translated_page.source_page.id]) not in response["Location"]
    assert spy.call_count == 1


def test_the_source_is_not_resnapshotted_when_the_guard_fires(translated_page, syncer, syncer_client, mocker):
    make_pending_job(translated_page.source_page, [translated_page.locale], syncer)
    spy = mocker.spy(TranslationSource, "update_from_db")

    response = syncer_client.post(sync_url(translated_page.source_page), {})

    assert response.status_code == 302
    assert reverse("wagtailadmin_pages:edit", args=[translated_page.source_page.id]) in response["Location"]
    assert spy.call_count == 0


def test_an_unknown_translation_source_falls_through_to_the_view(syncer_client):
    """A stale bookmark must reach the view's own 404 rather than raise out of the guard."""
    # follow=True because reverse() has no locale prefix here and the locale
    # middleware redirects once before the view is reached.
    response = syncer_client.get(reverse("wagtail_localize:update_translations", args=[999999]), follow=True)

    assert response.status_code == 404
