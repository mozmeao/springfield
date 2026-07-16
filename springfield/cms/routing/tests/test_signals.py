# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from django.test import RequestFactory

import pytest

from springfield.cms.routing import (
    ResolverType,
    Signal,
    SignalRegistrationError,
    SignalRegistry,
    registry,
)

# ---------------------------------------------------------------------------
# SignalRegistry — shape and validation
# ---------------------------------------------------------------------------


class TestSignalRegistry:
    def _make_registry(self):
        return SignalRegistry()

    def _server_signal(self, name="test_signal", **overrides):
        defaults = {
            "name": name,
            "description": "Test signal",
            "resolver_type": ResolverType.SERVER_SIDE,
            "supports_routing": True,
            "supports_in_page_swap": True,
            "server_resolver": lambda req, ctx: "value",
        }
        defaults.update(overrides)
        return Signal(**defaults)

    def _client_signal(self, name="client_signal", **overrides):
        defaults = {
            "name": name,
            "description": "Test client signal",
            "resolver_type": ResolverType.CLIENT_SIDE_STATE,
            "supports_routing": True,
            "supports_in_page_swap": True,
            "uitour_key": "appinfo",
            "uitour_extractor": "test_extractor",
        }
        defaults.update(overrides)
        return Signal(**defaults)

    def test_register_and_retrieve(self):
        reg = self._make_registry()
        signal = self._server_signal()
        reg.register(signal)
        assert reg.get("test_signal") is signal

    def test_get_returns_none_when_missing(self):
        assert self._make_registry().get("nope") is None

    def test_all_returns_registered_signals(self):
        reg = self._make_registry()
        reg.register(self._server_signal("a"))
        reg.register(self._server_signal("b"))
        assert {s.name for s in reg.all()} == {"a", "b"}

    def test_by_resolver_type_filters(self):
        reg = self._make_registry()
        reg.register(self._server_signal("s"))
        reg.register(self._client_signal("c"))
        assert [s.name for s in reg.by_resolver_type(ResolverType.SERVER_SIDE)] == ["s"]
        assert [s.name for s in reg.by_resolver_type(ResolverType.CLIENT_SIDE_STATE)] == ["c"]

    def test_duplicate_registration_rejected(self):
        reg = self._make_registry()
        reg.register(self._server_signal("dup"))
        with pytest.raises(SignalRegistrationError, match="already registered"):
            reg.register(self._server_signal("dup"))

    def test_server_side_signal_requires_resolver(self):
        reg = self._make_registry()
        signal = self._server_signal(server_resolver=None)
        with pytest.raises(SignalRegistrationError, match="server_resolver"):
            reg.register(signal)

    def test_client_side_signal_requires_uitour_key(self):
        reg = self._make_registry()
        signal = self._client_signal(uitour_key=None)
        with pytest.raises(SignalRegistrationError, match="uitour_key"):
            reg.register(signal)

    def test_client_side_signal_requires_extractor(self):
        reg = self._make_registry()
        signal = self._client_signal(uitour_extractor=None)
        with pytest.raises(SignalRegistrationError, match="uitour_extractor"):
            reg.register(signal)

    def test_signal_must_support_routing_or_swap(self):
        reg = self._make_registry()
        signal = self._server_signal(supports_routing=False, supports_in_page_swap=False)
        with pytest.raises(SignalRegistrationError, match="at least one"):
            reg.register(signal)

    def test_cache_safe_defaults_to_false(self):
        # cache_safe is an opt-in flag — signals that don't declare it get
        # the safe default of "not cache-safe", so a rule can't accidentally
        # use a server signal that isn't wired into the Fastly cache key.
        signal = self._server_signal()
        assert signal.cache_safe is False

    def test_cache_safe_can_be_set(self):
        signal = self._server_signal(cache_safe=True)
        assert signal.cache_safe is True


# ---------------------------------------------------------------------------
# resolve_server_signals — orchestrates all SERVER_SIDE resolvers
# ---------------------------------------------------------------------------


class TestResolveServerSignals:
    def test_returns_only_resolved_signals(self):
        reg = SignalRegistry()
        reg.register(
            Signal(
                name="always_true",
                description="always resolves",
                resolver_type=ResolverType.SERVER_SIDE,
                supports_routing=True,
                supports_in_page_swap=False,
                server_resolver=lambda req, ctx: True,
            )
        )
        reg.register(
            Signal(
                name="always_none",
                description="never resolves",
                resolver_type=ResolverType.SERVER_SIDE,
                supports_routing=True,
                supports_in_page_swap=False,
                server_resolver=lambda req, ctx: None,
            )
        )
        request = RequestFactory().get("/")
        resolved = reg.resolve_server_signals(request)
        assert resolved == {"always_true": True}

    def test_skips_client_side_signals(self):
        reg = SignalRegistry()
        reg.register(
            Signal(
                name="client_only",
                description="client",
                resolver_type=ResolverType.CLIENT_SIDE_STATE,
                supports_routing=True,
                supports_in_page_swap=True,
                uitour_key="appinfo",
                uitour_extractor="e",
            )
        )
        assert reg.resolve_server_signals(RequestFactory().get("/")) == {}

    def test_exception_in_resolver_is_swallowed(self):
        reg = SignalRegistry()

        def broken(_req, _ctx):
            raise RuntimeError("boom")

        reg.register(
            Signal(
                name="ok",
                description="ok",
                resolver_type=ResolverType.SERVER_SIDE,
                supports_routing=True,
                supports_in_page_swap=False,
                server_resolver=lambda r, c: "yes",
            )
        )
        reg.register(
            Signal(
                name="broken",
                description="broken",
                resolver_type=ResolverType.SERVER_SIDE,
                supports_routing=True,
                supports_in_page_swap=False,
                server_resolver=broken,
            )
        )
        # A broken resolver must not take down the whole resolution pass.
        resolved = reg.resolve_server_signals(RequestFactory().get("/"))
        assert resolved == {"ok": "yes"}

    def test_context_is_passed_through(self):
        seen = {}

        def resolver(_req, ctx):
            seen.update(ctx)
            return "ok"

        reg = SignalRegistry()
        reg.register(
            Signal(
                name="ctxsig",
                description="context checker",
                resolver_type=ResolverType.SERVER_SIDE,
                supports_routing=True,
                supports_in_page_swap=False,
                server_resolver=resolver,
            )
        )
        reg.resolve_server_signals(RequestFactory().get("/"), context={"target_version": "156"})
        assert seen == {"target_version": "156"}


# ---------------------------------------------------------------------------
# Default registrations — all 12 initial signals must register cleanly
# and be resolvable in principle.
# ---------------------------------------------------------------------------


class TestDefaultRegistrations:
    EXPECTED_SIGNALS = {
        # Server-side
        "country",
        "locale",
        "lapsed_user",
        "platform",
        "os_version",
        "is_firefox",
        "firefox_version",
        # Client-side (UITour)
        "default_browser",
        "firefox_pinned",
        "profile_age_days",
        "fxa_signed_in",
        "ai_controls",
    }

    def test_all_expected_signals_registered(self):
        registered = {s.name for s in registry.all()}
        assert self.EXPECTED_SIGNALS.issubset(registered)

    def test_server_side_signals_have_resolvers(self):
        for signal in registry.by_resolver_type(ResolverType.SERVER_SIDE):
            assert signal.server_resolver is not None, signal.name

    def test_client_side_signals_have_uitour_metadata(self):
        for signal in registry.by_resolver_type(ResolverType.CLIENT_SIDE_STATE):
            assert signal.uitour_key, signal.name
            assert signal.uitour_extractor, signal.name

    @mock.patch("springfield.cms.routing.server_resolvers.get_country_from_request")
    def test_country_resolves_from_geo_header(self, mock_geo):
        mock_geo.return_value = "DE"
        request = RequestFactory().get("/")
        resolved = registry.resolve_server_signals(request)
        assert resolved.get("country") == "DE"

    def test_lapsed_user_resolves_true_for_wide_gap(self):
        request = RequestFactory().get("/", data={"oldversion": "149"})
        resolved = registry.resolve_server_signals(request, context={"target_version": "156"})
        assert resolved.get("lapsed_user") is True

    def test_lapsed_user_resolves_false_for_narrow_gap(self):
        request = RequestFactory().get("/", data={"oldversion": "155"})
        resolved = registry.resolve_server_signals(request, context={"target_version": "156"})
        assert resolved.get("lapsed_user") is False

    def test_lapsed_user_absent_without_target_version(self):
        request = RequestFactory().get("/", data={"oldversion": "149"})
        resolved = registry.resolve_server_signals(request, context={})
        assert "lapsed_user" not in resolved

    def test_lapsed_user_absent_without_oldversion(self):
        request = RequestFactory().get("/")
        resolved = registry.resolve_server_signals(request, context={"target_version": "156"})
        assert "lapsed_user" not in resolved

    def test_platform_resolves_from_ua(self):
        rf = RequestFactory()
        cases = [
            ("Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0", "linux"),
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/151.0", "windows"),
            ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) Gecko/20100101 Firefox/151.0", "osx"),
            ("Mozilla/5.0 (Linux; Android 14) Gecko/151.0 Firefox/151.0", "android"),
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) FxiOS/151.0", "ios"),
        ]
        for ua, expected in cases:
            request = rf.get("/", HTTP_USER_AGENT=ua)
            resolved = registry.resolve_server_signals(request)
            assert resolved.get("platform") == expected, f"UA={ua!r}"

    def test_os_version_windows_10_plus(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/151.0"
        request = RequestFactory().get("/", HTTP_USER_AGENT=ua)
        resolved = registry.resolve_server_signals(request)
        assert resolved.get("os_version") == "windows-10-plus"

    def test_os_version_absent_on_older_windows(self):
        ua = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) Gecko/20100101 Firefox/151.0"
        request = RequestFactory().get("/", HTTP_USER_AGENT=ua)
        resolved = registry.resolve_server_signals(request)
        assert "os_version" not in resolved

    def test_firefox_version_parses_from_ua(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/151.0"
        request = RequestFactory().get("/", HTTP_USER_AGENT=ua)
        resolved = registry.resolve_server_signals(request)
        assert resolved.get("firefox_version") == 151
        assert resolved.get("is_firefox") is True

    def test_is_firefox_false_on_chrome_ua(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        request = RequestFactory().get("/", HTTP_USER_AGENT=ua)
        resolved = registry.resolve_server_signals(request)
        assert resolved.get("is_firefox") is False
        assert "firefox_version" not in resolved

    def test_is_firefox_false_on_seamonkey_ua(self):
        ua = "Mozilla/5.0 SeaMonkey/2.53 Firefox/68.0"
        request = RequestFactory().get("/", HTTP_USER_AGENT=ua)
        resolved = registry.resolve_server_signals(request)
        assert resolved.get("is_firefox") is False

    def test_all_client_side_signals_are_cache_safe(self):
        # Client-side signals resolve after the response is served — they
        # never affect what Fastly caches, so they're inherently cache-safe.
        # Every CLIENT_SIDE_STATE default registration must be marked as such.
        for signal in registry.by_resolver_type(ResolverType.CLIENT_SIDE_STATE):
            assert signal.cache_safe is True, f"Client-side signal {signal.name!r} should be cache_safe"

    def test_country_is_not_cache_safe_by_default(self):
        # Country is the highest-cardinality server signal (200 raw values).
        # Server-side use requires Fastly VCL cache-key extension —
        # coordinate with Websites team before flipping to cache_safe=True.
        country = registry.get("country")
        assert country is not None
        assert country.cache_safe is False

    def test_server_side_signals_default_to_not_cache_safe(self):
        # In V1, all server-side signals are cache_safe=False until Websites
        # team's Fastly VCL work lands. This is the safe default.
        for signal in registry.by_resolver_type(ResolverType.SERVER_SIDE):
            assert signal.cache_safe is False, (
                f"Server signal {signal.name!r} is unexpectedly cache_safe — confirm VCL is in place before flipping this."
            )
