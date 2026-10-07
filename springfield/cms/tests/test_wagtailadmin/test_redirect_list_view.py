# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

import pytest
from bs4 import BeautifulSoup
from wagtail.contrib.redirects.models import Redirect

User = get_user_model()

BULK_DELETE_URL = reverse("wagtail_bulk_action", args=("wagtailredirects", "redirect", "delete"))


@pytest.mark.django_db
def test_redirect_listing_has_bulk_action_checkboxes(admin_client):
    redirect = Redirect.objects.create(old_path="/old-vpn", redirect_link="/vpn/")

    response = admin_client.get(reverse("wagtailredirects:index"))

    soup = BeautifulSoup(response.content, "html.parser")
    checkbox = soup.find("input", attrs={"data-bulk-action-checkbox": True, "data-object-id": str(redirect.pk)})
    assert checkbox is not None
    assert soup.find(id=checkbox["aria-describedby"]).get_text(strip=True) == "/old-vpn"
    assert soup.find(attrs={"data-bulk-action-footer": "REDIRECT"}) is not None


@pytest.mark.django_db
def test_bulk_delete_confirmation_lists_selected_redirects(admin_client):
    redirect = Redirect.objects.create(old_path="/old-vpn", redirect_link="/vpn/")

    response = admin_client.get(f"{BULK_DELETE_URL}?id={redirect.pk}")

    soup = BeautifulSoup(response.content, "html.parser")
    assert [item.get_text(strip=True) for item in soup.select(".nice-padding ul li")] == ["/old-vpn → /vpn/"]
    assert Redirect.objects.filter(pk=redirect.pk).exists()


@pytest.mark.django_db
def test_bulk_delete_removes_selected_redirects(admin_client):
    selected = [
        Redirect.objects.create(old_path="/old-vpn", redirect_link="/vpn/"),
        Redirect.objects.create(old_path="/old-vpn-pricing", redirect_link="/vpn/pricing/"),
    ]
    unselected = Redirect.objects.create(old_path="/old-features", redirect_link="/features/")
    query = "&".join(f"id={redirect.pk}" for redirect in selected)

    response = admin_client.post(f"{BULK_DELETE_URL}?{query}")

    assert response.status_code == 302
    assert not Redirect.objects.filter(pk__in=[redirect.pk for redirect in selected]).exists()
    assert Redirect.objects.filter(pk=unselected.pk).exists()


@pytest.mark.django_db
def test_bulk_delete_select_all_respects_search(admin_client):
    matching = [
        Redirect.objects.create(old_path="/old-vpn", redirect_link="/vpn/"),
        Redirect.objects.create(old_path="/old-vpn-pricing", redirect_link="/vpn/pricing/"),
    ]
    unmatched = Redirect.objects.create(old_path="/old-features", redirect_link="/features/")

    admin_client.post(f"{BULK_DELETE_URL}?id=all&q=vpn")

    assert not Redirect.objects.filter(pk__in=[redirect.pk for redirect in matching]).exists()
    assert Redirect.objects.filter(pk=unmatched.pk).exists()


@pytest.mark.django_db
def test_bulk_delete_requires_delete_permission(client):
    redirect = Redirect.objects.create(old_path="/old-vpn", redirect_link="/vpn/")
    editor = User.objects.create_user(username="editor", email="editor@example.com")
    editor.user_permissions.add(
        Permission.objects.get(codename="access_admin"),
        Permission.objects.get(codename="change_redirect"),
    )

    with override_settings(
        AUTHENTICATION_BACKENDS=("django.contrib.auth.backends.ModelBackend",),
        USE_SSO_AUTH=False,
    ):
        client.force_login(editor, backend="django.contrib.auth.backends.ModelBackend")
        client.post(f"{BULK_DELETE_URL}?id={redirect.pk}")

    assert Redirect.objects.filter(pk=redirect.pk).exists()
