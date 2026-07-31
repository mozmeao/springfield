# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the browse-only User Routing rules listing (C12)."""

from django.urls import NoReverseMatch, reverse

import pytest
from wagtail.models import Site

from springfield.cms import wagtail_hooks
from springfield.cms.routing.models import RoutingRule
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]


def _rule_on(slug, title):
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug=slug, title=title, parent=site_root)
    target = SimpleRichTextPageFactory(slug=f"{slug}-t", title=f"{title} target", parent=canonical, live=True)
    return RoutingRule.objects.create(page=canonical, target=target)


def test_listing_renders_rules_from_multiple_pages(admin_client):
    _rule_on("c12-alpha", "Canonical Alpha")
    _rule_on("c12-beta", "Canonical Beta")

    response = admin_client.get(reverse("cms_routing_rules"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Canonical Alpha" in content
    assert "Canonical Beta" in content


def test_listing_handles_no_rules(admin_client):
    response = admin_client.get(reverse("cms_routing_rules"))
    assert response.status_code == 200
    assert "No routing rules" in response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# The listing is browse-only: no add affordance (spec §6.1).
# ---------------------------------------------------------------------------


def test_no_add_route_is_registered():
    with pytest.raises(NoReverseMatch):
        reverse("cms_routing_rules_add")


def test_listing_has_no_add_form_or_button(admin_client):
    content = admin_client.get(reverse("cms_routing_rules")).content.decode("utf-8").lower()
    # A read/browse aggregation: no create form, no "add rule" affordance.
    assert "<form" not in content
    assert "add rule" not in content


# ---------------------------------------------------------------------------
# The "User Routing" submenu is registered with the Rules item.
# ---------------------------------------------------------------------------


def test_user_routing_submenu_is_registered():
    submenu = wagtail_hooks.register_user_routing_menu()
    assert str(submenu.label) == "User Routing"
    assert submenu.menu is wagtail_hooks.user_routing_menu


def test_rules_item_is_in_the_submenu():
    labels = [str(item.label) for item in wagtail_hooks.user_routing_menu.registered_menu_items]
    assert "Rules" in labels
