# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for the User Routing admin views."""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

import pytest

from springfield.cms.routing.admin_views import signals_reference


@pytest.mark.django_db
class TestSignalsReferenceView:
    """The signals reference view auto-generates a table from the live
    ``SignalRegistry``. Test the rendered content contains what marketing
    would need to look up value expectations for each signal.

    Marked ``django_db`` because Wagtail's admin base template pulls
    ``Locale`` / ``Site`` rows during render.
    """

    def _render(self):
        rf = RequestFactory()
        request = rf.get("/cms-admin/user-routing/signals/")
        request.user = AnonymousUser()  # some context processors touch this
        response = signals_reference(request)
        response.render()
        return response.content.decode("utf-8")

    def test_response_is_200(self):
        rf = RequestFactory()
        request = rf.get("/cms-admin/user-routing/signals/")
        request.user = AnonymousUser()
        response = signals_reference(request)
        assert response.status_code == 200

    def test_all_registered_signals_appear(self):
        body = self._render()
        # Sampling — full 12-signal check is in test_signals.py.
        for name in (
            "country",
            "locale",
            "lapsed_user",
            "platform",
            "os_version",
            "is_firefox",
            "firefox_version",
            "default_browser",
            "firefox_pinned",
            "profile_age_days",
            "fxa_signed_in",
            "ai_controls",
        ):
            assert name in body, f"Signal {name!r} missing from reference page"

    def test_country_enum_values_shown(self):
        body = self._render()
        # The 29-country allowlist should be visible so marketing can copy
        # exact codes.
        for code in ("US", "GB", "DE", "FR", "CA"):
            assert f">{code}<" in body, f"country enum value {code!r} not in reference"

    def test_ai_controls_enum_values_shown(self):
        body = self._render()
        for value in ("enabled", "available", "blocked"):
            assert f">{value}<" in body, f"ai_controls enum value {value!r} not in reference"

    def test_bool_signal_shows_true_false_hint(self):
        body = self._render()
        # Bool signals (lapsed_user, default_browser, etc.) get a "true or
        # false" hint rather than an enum list.
        assert "<code>true</code> or <code>false</code>" in body

    def test_server_vs_browser_badges(self):
        body = self._render()
        # Both kinds should appear in the resulting table.
        assert "user-routing-badge-server" in body
        assert "user-routing-badge-browser" in body

    def test_cache_safe_column_present(self):
        body = self._render()
        # The reference page includes a cache-safe column so authors can
        # see which server signals still need infra coordination before use.
        assert "Cache-safe" in body
        assert "user-routing-badge-cachesafe-yes" in body  # client signals
        assert "user-routing-badge-cachesafe-no" in body  # country et al.
