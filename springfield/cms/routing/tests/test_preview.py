# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the admin-only preview flows (C9)."""

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

import pytest
from wagtail.models import Site

from springfield.cms.routing.models import RoutingCondition, RoutingConfig, RoutingRule
from springfield.cms.routing.preview import get_preview_response, parse_fake_signals
from springfield.cms.tests.factories import SimpleRichTextPageFactory

pytestmark = [pytest.mark.django_db]

rf = RequestFactory()
User = get_user_model()


@pytest.fixture
def routed_page():
    site_root = Site.objects.get(is_default_site=True).root_page
    canonical = SimpleRichTextPageFactory(slug="c9-canonical", parent=site_root)
    target = SimpleRichTextPageFactory(slug="c9-variant", parent=canonical, live=True)
    rule = RoutingRule.objects.create(page=canonical, target=target)
    RoutingCondition.objects.create(rule=rule, signal="platform", operator="is", expected_value="windows", sort_order=0)
    return SimpleNamespace(canonical=canonical, target=target, rule=rule)


@pytest.fixture
def staff_user():
    return User.objects.create(username="staff", is_staff=True, is_active=True)


def _request(path, user):
    request = rf.get(path)
    request.user = user
    return request


def _content(response):
    if hasattr(response, "render"):
        response.render()
    return response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# Auth gating — non-admins fall through to normal serve (spec §8).
# ---------------------------------------------------------------------------


def test_unauthenticated_preview_params_are_ignored(routed_page):
    request = _request(f"/?preview_rule={routed_page.rule.pk}", AnonymousUser())
    assert get_preview_response(request, routed_page.canonical) is None


def test_non_staff_user_is_ignored(routed_page):
    user = User.objects.create(username="viewer", is_staff=False, is_active=True)
    request = _request(f"/?preview_rule={routed_page.rule.pk}", user)
    assert get_preview_response(request, routed_page.canonical) is None


def test_admin_without_preview_params_gets_no_preview(routed_page, staff_user):
    request = _request("/", staff_user)
    assert get_preview_response(request, routed_page.canonical) is None


# ---------------------------------------------------------------------------
# preview_rule — server-side 302, no-store, bypasses the kill switch (spec §8).
# ---------------------------------------------------------------------------


def test_preview_rule_302s_to_target(routed_page, staff_user):
    request = _request(f"/?preview_rule={routed_page.rule.pk}", staff_user)
    response = get_preview_response(request, routed_page.canonical)
    assert response.status_code == 302
    assert response["Location"] == routed_page.target.get_url(request)
    assert response["Cache-Control"] == "no-store"


def test_preview_rule_bypasses_kill_switch(routed_page, staff_user):
    RoutingConfig.objects.create(page=routed_page.canonical, routing_paused=True)
    request = _request(f"/?preview_rule={routed_page.rule.pk}", staff_user)
    response = get_preview_response(request, routed_page.canonical)
    # Previews deliberately ignore routing_paused.
    assert response.status_code == 302


def test_preview_rule_with_invalid_id_falls_through(routed_page, staff_user):
    for value in ("99999", "not-a-number"):
        request = _request(f"/?preview_rule={value}", staff_user)
        assert get_preview_response(request, routed_page.canonical) is None


# ---------------------------------------------------------------------------
# preview_signal — fake-signal blob, real evaluation path, no-store (spec §8).
# ---------------------------------------------------------------------------


def test_preview_signal_injects_fake_blob(routed_page, staff_user):
    # The resolver renders under a locale prefix, as it does in production.
    request = _request("/en-US/whatsnew/?preview_signal=platform:windows", staff_user)
    response = get_preview_response(request, routed_page.canonical)
    assert response["Cache-Control"] == "no-store"
    html = _content(response)
    # Faked signal rides the same data-* attribute convention.
    assert "data-routing-fake-signals=" in html
    assert "platform" in html
    assert "windows" in html
    # Un-faked signals still ship in the manifest so the client reads them live.
    assert "data-routing-manifest=" in html


def test_preview_signal_ignores_unknown_and_malformed(routed_page, staff_user):
    request = _request("/?preview_signal=platform:windows&preview_signal=bogus:x&preview_signal=malformed", staff_user)
    fakes = parse_fake_signals(request.GET.getlist("preview_signal"))
    assert fakes == {"platform": "windows"}


def test_parse_fake_signals_keeps_colons_in_value():
    # Only the first colon separates name from value.
    assert parse_fake_signals(["firefox_version:129:beta"]) == {"firefox_version": "129:beta"}
