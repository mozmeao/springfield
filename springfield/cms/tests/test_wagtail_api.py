# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from django.contrib.auth.models import Group, Permission, User
from django.test import Client

import pytest
from waffle.testutils import override_switch
from wagtail.models import APIToken, GroupPagePermission

from springfield.cms.fixtures.snippet_fixtures import get_pencil_banner_snippet
from springfield.cms.models import FreeFormPage2026
from springfield.cms.tests.factories import FreeFormPage2026Factory
from springfield.cms.wagtail_api import WAGTAIL_API_SWITCH

pytestmark = [pytest.mark.django_db]

API_ROOT = "/api/v3-preview/"
FREEFORM_TYPE = "cms.FreeFormPage2026"
NEVER_CACHE = "max-age=0, no-cache, no-store, must-revalidate, private"


def rich_text_block(block_id, text):
    return {"type": "rich_text", "id": block_id, "value": f'<p data-block-key="{block_id}">{text}</p>'}


def token_headers(user):
    _, token = APIToken.create_token(user=user, name="test token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_headers():
    editor = User.objects.create_superuser(username="api-admin", email="api-admin@example.com", password="unused")
    return token_headers(editor)


@pytest.fixture
def draft_only_headers(minimal_site):
    """A token whose owner can add and edit pages but not publish them."""
    group = Group.objects.create(name="API editors")
    for codename in ("add_page", "change_page"):
        GroupPagePermission.objects.create(
            group=group,
            page=minimal_site.root_page,
            permission=Permission.objects.get(content_type__app_label="wagtailcore", codename=codename),
        )
    editor = User.objects.create_user(username="api-editor", email="api-editor@example.com", password="unused")
    editor.groups.add(group)
    return token_headers(editor)


@pytest.fixture
def live_freeform_page(minimal_site):
    return FreeFormPage2026Factory(
        parent=minimal_site.root_page,
        slug="live-freeform",
        content=[rich_text_block("live1", "Live copy")],
    )


# Django's LocaleMiddleware redirects a 404 to its /en-US/ form first, so this follows redirects.
@pytest.mark.parametrize("switch_state", [None, False])
def test_api_is_not_served_unless_switch_is_on(client, api_headers, switch_state):
    if switch_state is None:
        response = client.get(f"{API_ROOT}pages/", headers=api_headers, follow=True)
    else:
        with override_switch(WAGTAIL_API_SWITCH, active=switch_state):
            response = client.get(f"{API_ROOT}pages/", headers=api_headers, follow=True)

    assert response.status_code == 404


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_api_is_served_when_switch_is_on(client, api_headers):
    response = client.get(f"{API_ROOT}pages/", headers=api_headers)

    assert response.status_code == 200
    assert response["Cache-Control"] == NEVER_CACHE


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_draft_read_is_never_cached(client, api_headers, live_freeform_page):
    response = client.get(f"{API_ROOT}pages/{live_freeform_page.id}/?version=draft", headers=api_headers)

    assert response.status_code == 200
    assert response["Cache-Control"] == NEVER_CACHE


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_docs_and_schema_are_not_served(client):
    for path in ("docs/", "openapi.json"):
        assert client.get(f"{API_ROOT}{path}", follow=True).status_code == 404


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_write_without_token_is_rejected(client, minimal_site):
    payload = {"meta": {"type": FREEFORM_TYPE, "parent_id": minimal_site.root_page.id}, "title": "No token"}

    response = client.post(f"{API_ROOT}pages/", data=json.dumps(payload), content_type="application/json")

    assert response.status_code == 401
    assert not FreeFormPage2026.objects.filter(title="No token").exists()


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_create_saves_freeform_page_as_draft(draft_only_headers, minimal_site):
    client = Client(enforce_csrf_checks=True, headers=draft_only_headers)
    snippet = get_pencil_banner_snippet()
    payload = {
        "meta": {"type": FREEFORM_TYPE, "parent_id": minimal_site.root_page.id},
        "title": "API draft",
        "slug": "api-draft",
        "show_pre_footer": False,
        "upper_content": [],
        "content": [rich_text_block("draft1", "Draft copy")],
        "pencil_banner_placements": [{"snippet_id": snippet.id}],
    }

    response = client.post(f"{API_ROOT}pages/", data=json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    page = FreeFormPage2026.objects.get(id=response.json()["id"])
    assert page.live is False
    draft = page.get_latest_revision_as_object()
    assert draft.show_pre_footer is False
    assert "Draft copy" in draft.content[0].value.source
    assert [placement.snippet_id for placement in draft.pencil_banner_placements.all()] == [snippet.id]


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_update_adds_draft_revision_without_changing_live_page(client, draft_only_headers, live_freeform_page):
    payload = {"meta": {"type": FREEFORM_TYPE}, "content": [rich_text_block("new1", "New copy")]}

    response = client.patch(
        f"{API_ROOT}pages/{live_freeform_page.id}/",
        data=json.dumps(payload),
        content_type="application/json",
        headers=draft_only_headers,
    )

    assert response.status_code == 200
    live_freeform_page.refresh_from_db()
    assert live_freeform_page.has_unpublished_changes is True
    assert "Live copy" in live_freeform_page.content[0].value.source
    assert "New copy" in live_freeform_page.get_latest_revision_as_object().content[0].value.source


@override_switch(WAGTAIL_API_SWITCH, active=True)
def test_draft_only_token_cannot_publish(client, draft_only_headers, live_freeform_page):
    publish_with_update = {"meta": {"type": FREEFORM_TYPE, "action": "publish"}, "content": [rich_text_block("pub1", "Published?")]}

    update_response = client.patch(
        f"{API_ROOT}pages/{live_freeform_page.id}/",
        data=json.dumps(publish_with_update),
        content_type="application/json",
        headers=draft_only_headers,
    )
    publish_response = client.post(f"{API_ROOT}pages/{live_freeform_page.id}/actions/publish/", headers=draft_only_headers)
    unpublish_response = client.post(
        f"{API_ROOT}pages/{live_freeform_page.id}/actions/unpublish/",
        data="{}",
        content_type="application/json",
        headers=draft_only_headers,
    )

    assert update_response.status_code == 403
    assert publish_response.status_code == 403
    assert unpublish_response.status_code == 403
    live_freeform_page.refresh_from_db()
    assert live_freeform_page.live is True
    assert "Live copy" in live_freeform_page.content[0].value.source
