# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pages are locked against non-superuser edits while their content is at Smartling."""

from urllib.parse import urlencode
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

import pytest
from wagtail.models import GroupPagePermission, Page, Site
from wagtail.test.utils.form_data import rich_text
from wagtail_localize.models import StringSegment, StringTranslation, Translation, TranslationSource
from wagtail_localize_smartling import locks
from wagtail_localize_smartling.api.types import JobStatus
from wagtail_localize_smartling.models import Job, Project

from springfield.cms.models.base import AbstractSpringfieldCMSPage
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]

User = get_user_model()


def make_project():
    """The one test Project, reused: Project is unique on environment/account/project id,
    and make_pending_job() needs one for every job."""
    project, _ = Project.objects.get_or_create(
        environment="production",
        account_uid="test-account",
        project_id="test-project",
        defaults={
            "archived": False,
            "name": "Test project",
            "type_code": "APPLICATION_RESOURCES",
            "source_locale_description": "English (United States) [en-US]",
            "source_locale_id": "en-US",
        },
    )
    return project


def make_pending_job(source_page, locales, user, status=JobStatus.IN_PROGRESS):
    """A Smartling job sitting at `status` with nothing imported yet."""
    source, _ = TranslationSource.get_or_create_from_instance(source_page)
    translations = [Translation.objects.get_or_create(source=source, target_locale=locale)[0] for locale in locales]
    synced = status != JobStatus.UNSYNCED
    now = timezone.now()
    job = Job.objects.create(
        project=make_project(),
        translation_source=source,
        user=user,
        name="Test job",
        status=status,
        first_synced_at=now if synced else None,
        last_synced_at=now if synced else None,
        translation_job_uid=f"test-job-{uuid4().hex}" if synced else "",
    )
    job.translations.set(translations)
    return job


@pytest.fixture
def editor_publisher():
    """A staff user with change + publish across the whole page tree."""
    group = Group.objects.create(name="WT-1854 editors")
    for root in Page.objects.filter(depth=1):
        for codename in ("change_page", "publish_page"):
            GroupPagePermission.objects.create(
                group=group,
                page=root,
                permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
            )
    group.permissions.add(Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin"))
    user = User.objects.create_user(
        username="editor",
        email="editor@example.com",
        password="pass",
        is_staff=True,
    )
    user.groups.add(group)
    return user


@pytest.fixture
def editor_publisher_client(client, editor_publisher):
    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        client.force_login(editor_publisher, backend="django.contrib.auth.backends.ModelBackend")
        yield client


def edit_post_data(page, title="Edited while pending"):
    """A complete page-edit POST for SimpleRichTextPage, whose only required field
    beyond the Wagtail basics is `content`.
    """
    return {
        "title": title,
        "slug": page.slug,
        "content": rich_text("<p>Edited while pending</p>"),
        "comments-TOTAL_FORMS": "0",
        "comments-INITIAL_FORMS": "0",
        "comments-MIN_NUM_FORMS": "0",
        "comments-MAX_NUM_FORMS": "1000",
        "action-save-draft": "Save draft",
    }


def post_edit(http_client, page, **kwargs):
    return http_client.post(reverse("wagtailadmin_pages:edit", args=[page.id]), edit_post_data(page, **kwargs))


# --- the source page ------------------------------------------------------


def test_editor_cannot_create_a_revision_while_a_job_is_outstanding(translated_page, editor_publisher, editor_publisher_client):
    page = translated_page.source_page
    make_pending_job(page, [translated_page.locale], editor_publisher)
    before = page.revisions.count()

    post_edit(editor_publisher_client, page)

    assert page.revisions.count() == before


def test_editor_can_create_a_revision_when_no_job_is_outstanding(translated_page, editor_publisher_client):
    page = translated_page.source_page
    before = page.revisions.count()

    post_edit(editor_publisher_client, page)

    assert page.revisions.count() == before + 1


def test_superuser_can_create_a_revision_while_a_job_is_outstanding(translated_page, admin_client):
    page = translated_page.source_page
    superuser = User.objects.get(username="admin")
    make_pending_job(page, [translated_page.locale], superuser)
    before = page.revisions.count()

    post_edit(admin_client, page)

    assert page.revisions.count() == before + 1


def test_superuser_sees_warning_banner(translated_page, admin_client):
    page = translated_page.source_page
    superuser = User.objects.get(username="admin")
    make_pending_job(page, [translated_page.locale], superuser)

    response = admin_client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))

    assert response.status_code == 200
    assert b"being translated in Smartling into French" in response.content
    # The banner looks like a warning
    banners = [message for message in response.context["messages"] if "being translated in Smartling" in str(message)]
    assert len(banners) == 1
    assert banners[0].level == messages.WARNING


def test_blocked_editor_sees_the_page_and_the_reason(translated_page, editor_publisher, editor_publisher_client):
    page = translated_page.source_page
    make_pending_job(page, [translated_page.locale], editor_publisher)

    response = editor_publisher_client.get(reverse("wagtailadmin_pages:edit", args=[page.id]))

    assert response.status_code == 200
    assert b"being translated in Smartling into French" in response.content
    assert b"until that translation comes back" in response.content


def test_a_page_locks_from_submission_before_the_first_sync(translated_page, editor_publisher, editor_publisher_client):
    page = translated_page.source_page
    make_pending_job(page, [translated_page.locale], editor_publisher, status=JobStatus.UNSYNCED)
    before = page.revisions.count()

    response = post_edit(editor_publisher_client, page)

    assert response.status_code == 200
    assert b"The page could not be saved as it is locked." in response.content
    assert page.revisions.count() == before


# --- the translated page --------------------------------------------------


def test_translated_page_is_locked_for_its_own_locale(translated_page, editor_publisher):
    """
    Asserted on the model rather than through the page editor, because
    wagtail-localize overrides the edit view for a page that is the enabled target
    of a translation.
    """
    make_pending_job(translated_page.source_page, [translated_page.locale], editor_publisher)

    lock = translated_page.page.get_lock()

    assert lock is not None
    assert lock.is_target is True
    assert lock.for_user(editor_publisher) is True


def test_translated_page_is_unlocked_when_no_job_is_outstanding(translated_page):
    assert not Job.objects.filter(translation_source__object_id=translated_page.page.translation_key).exists()
    assert translated_page.page.get_lock() is None


# --- springfield's own policy --------------------------------------------


def test_springfield_states_its_own_bypass_rule():
    assert "can_bypass_pending_translation_lock" in AbstractSpringfieldCMSPage.__dict__


def test_springfield_lets_only_superusers_through_the_lock(translated_page, editor_publisher):
    page = translated_page.source_page
    superuser = User.objects.create_superuser(username="super_user", email="super_user@example.com", password="pass")

    assert page.can_bypass_pending_translation_lock(superuser) is True
    assert page.can_bypass_pending_translation_lock(editor_publisher) is False


def test_the_explorer_costs_at_most_one_extra_query_per_row(db, admin_client, monkeypatch):
    site_root = Site.objects.get(is_default_site=True).root_page
    parent = SimpleRichTextPageFactory(parent=site_root, title="Budget parent", slug="budget-parent")
    rows = 10
    for index in range(rows):
        SimpleRichTextPageFactory(parent=parent, title=f"Budget page {index}", slug=f"budget-page-{index}")
    url = reverse("wagtailadmin_explore", args=[parent.id])

    admin_client.get(url)  # warm the permission and content-type caches

    monkeypatch.setattr(
        locks,
        "get_pending_translation_state",
        lambda instance: locks.PendingTranslationState(is_target=False, locales=[]),
    )
    with CaptureQueriesContext(connection) as without_mixin:
        admin_client.get(url)
    monkeypatch.undo()

    with CaptureQueriesContext(connection) as with_mixin:
        response = admin_client.get(url)

    # rows + 1: the Unpublish button is yielded both per row and once for the parent
    # page in the header. Measured at 11 lock consultations for 10 rows.
    expected = rows + 1

    assert response.status_code == 200
    assert len(with_mixin) - len(without_mixin) == expected


def test_the_translation_editor_writes_when_nothing_is_in_flight(translated_page, editor_publisher, editor_publisher_client):
    segment = StringSegment.objects.filter(source=translated_page.translation.source).first()

    response = editor_publisher_client.put(
        reverse(
            "wagtail_localize:edit_string_translation",
            args=[translated_page.translation.id, segment.id],
        ),
        urlencode({"value": "Written with no job outstanding"}),
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code in (200, 201)
    assert StringTranslation.objects.filter(translation_of_id=segment.string_id, locale=translated_page.locale).exists()
