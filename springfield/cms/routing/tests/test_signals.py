# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
#
# Under the client-side architecture the registry is a metadata catalog only:
# the actual resolution happens in the browser (user-routing-resolver.js).
# These tests exercise the invariants the admin form and dispatcher rely on.
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

    def test_duplicate_registration_rejected(self):
        reg = self._make_registry()
        reg.register(self._server_signal("dup"))
        with pytest.raises(SignalRegistrationError, match="already registered"):
            reg.register(self._server_signal("dup"))

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

    def test_unknown_resolver_type_rejected(self):
        # Guard against typos in future signal registrations.
        reg = self._make_registry()
        with pytest.raises(SignalRegistrationError, match="Unknown resolver_type"):
            reg.register(
                Signal(
                    name="weird",
                    description="",
                    resolver_type="not-a-real-type",  # type: ignore[arg-type]
                    supports_routing=True,
                    supports_in_page_swap=False,
                )
            )

    def test_cache_safe_defaults_to_false(self):
        signal = self._server_signal()
        assert signal.cache_safe is False

    def test_cache_safe_can_be_set(self):
        signal = self._server_signal(cache_safe=True)
        assert signal.cache_safe is True

    def test_clear_empties_registry(self):
        reg = self._make_registry()
        reg.register(self._server_signal("a"))
        reg.clear()
        assert reg.all() == []


# ---------------------------------------------------------------------------
# Default registrations — the 12 initial signals must all register cleanly
# and carry the metadata the admin form + resolver JS need.
# ---------------------------------------------------------------------------


class TestDefaultRegistrations:
    EXPECTED_SERVER_SIDE = {
        "country",
        "locale",
        "lapsed_user",
        "platform",
        "os_version",
        "is_firefox",
        "firefox_version",
    }
    EXPECTED_CLIENT_SIDE = {
        "default_browser",
        "firefox_pinned",
        "profile_age_days",
        "fxa_signed_in",
        "ai_controls",
    }
    EXPECTED_SIGNALS = EXPECTED_SERVER_SIDE | EXPECTED_CLIENT_SIDE

    def test_all_expected_signals_registered(self):
        registered = {s.name for s in registry.all()}
        assert self.EXPECTED_SIGNALS.issubset(registered)

    def test_server_side_signals_categorized(self):
        for name in self.EXPECTED_SERVER_SIDE:
            signal = registry.get(name)
            assert signal is not None, name
            assert signal.resolver_type == ResolverType.SERVER_SIDE, name

    def test_client_side_signals_have_uitour_metadata(self):
        for name in self.EXPECTED_CLIENT_SIDE:
            signal = registry.get(name)
            assert signal is not None, name
            assert signal.resolver_type == ResolverType.CLIENT_SIDE_STATE, name
            assert signal.uitour_key, name
            assert signal.uitour_extractor, name

    def test_all_client_side_signals_are_cache_safe(self):
        # Client-side signals resolve after the response is served — they
        # never affect what Fastly caches, so they're inherently cache-safe.
        for name in self.EXPECTED_CLIENT_SIDE:
            signal = registry.get(name)
            assert signal is not None and signal.cache_safe is True, name

    def test_country_is_not_cache_safe(self):
        # Country is the highest-cardinality server signal. Server-side use
        # of geo requires Fastly VCL cache-key extension — keep the flag
        # opt-in even under the client-side architecture so a future consumer
        # doesn't accidentally mark it cache_safe without VCL work.
        country = registry.get("country")
        assert country is not None
        assert country.cache_safe is False
