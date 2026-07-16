# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Signal registry — the catalog of every conditional signal the routing layer
knows about.

A signal is a named thing that rules reference by name (e.g. ``lapsed_user``,
``ai_controls``, ``country``). Each signal declares how it can be resolved:

  * ``SERVER_SIDE`` — computable from the incoming HTTP request (URL, headers,
    User-Agent, CDN geo). Callable via ``server_resolver(request, context)``.
    Available before any HTML is sent, so it can drive whole-page routing at
    a 302 without any client involvement.
  * ``CLIENT_SIDE_STATE`` — knowable only after the page has loaded, via a
    ``Mozilla.UITour.getConfiguration()`` call. Declares the ``uitour_key`` to
    fetch and the ``uitour_extractor`` name that the client-side resolver
    library uses to derive the signal from the returned data.

Signals also declare where they may be used:

  * ``supports_routing`` — can drive a whole-page variant (server- or resolver-
    page-mediated).
  * ``supports_in_page_swap`` — can gate a block inside a rendered page.

Consumers (rule builder UI, resolver page, in-page swap components) read the
metadata and behave accordingly. The registry is the single interface —
sources are swappable underneath without any consumer change.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResolverType(str, Enum):
    """How a signal's value is obtained."""

    SERVER_SIDE = "server_side"
    CLIENT_SIDE_STATE = "client_side_state"


class SignalValueType(str, Enum):
    """The type a signal's value is expected to have.

    Used by the admin form to render a value-appropriate widget (checkbox
    for BOOL, dropdown for enum-like STRINGs, number input for INT) and by
    the rule model to parse the operator's expected value from admin input.
    """

    BOOL = "bool"
    STRING = "string"
    INT = "int"


@dataclass(frozen=True)
class Signal:
    """A registered conditional signal.

    Attributes:
        name: The unique identifier rules reference (e.g. ``"lapsed_user"``).
        description: Human-readable summary shown in the CMS admin.
        resolver_type: SERVER_SIDE or CLIENT_SIDE_STATE.
        supports_routing: Whether this signal may gate a whole-page variant.
        supports_in_page_swap: Whether this signal may gate an in-page block.
        server_resolver: For SERVER_SIDE signals: ``(request, context) -> value | None``.
            ``None`` means the signal could not be resolved for this request
            and the rule evaluator will treat it as "unknown".
        uitour_key: For CLIENT_SIDE_STATE signals: the ``Mozilla.UITour``
            ``getConfiguration`` key to fetch (e.g. ``"appinfo"``, ``"sync"``).
        uitour_extractor: For CLIENT_SIDE_STATE signals: the name of a
            client-side extractor that converts the UITour response into the
            signal's value. The client-side resolver library maps this name
            to a function.
        cache_safe: Whether the signal's projection is wired into the Fastly
            cache key via VCL. Only meaningful for SERVER_SIDE signals — a
            server-side rule referencing a signal that is NOT in the cache
            key risks silent cache poisoning (one user's variant response
            gets served to another). CLIENT_SIDE_STATE signals are inherently
            cache-safe because they resolve after the response is served, so
            they never affect what Fastly caches. Default is ``False`` —
            explicit opt-in required for server-side signals, coordinated
            with Websites team VCL changes.
    """

    name: str
    description: str
    resolver_type: ResolverType
    supports_routing: bool
    supports_in_page_swap: bool
    server_resolver: Callable[[Any, dict[str, Any]], Any] | None = None
    uitour_key: str | None = None
    uitour_extractor: str | None = None
    value_type: SignalValueType = SignalValueType.STRING
    # For STRING-typed signals with a bounded set of legal values (e.g.
    # ``ai_controls`` returns one of "enabled" / "available" / "blocked").
    # Used by the admin to render a dropdown instead of a free-text input.
    enum_values: tuple[str, ...] | None = None
    cache_safe: bool = False


class SignalRegistrationError(ValueError):
    """Raised when a signal registration is invalid or duplicated."""


class SignalRegistry:
    """Holds the registered signals and knows how to resolve the server-side ones."""

    def __init__(self) -> None:
        self._signals: dict[str, Signal] = {}

    def register(self, signal: Signal) -> None:
        """Register a signal. Raises if the name is taken or config is invalid."""
        if signal.name in self._signals:
            raise SignalRegistrationError(f"Signal {signal.name!r} is already registered")

        if not signal.supports_routing and not signal.supports_in_page_swap:
            raise SignalRegistrationError(
                f"Signal {signal.name!r} must support at least one of routing / in-page swap",
            )

        if signal.resolver_type == ResolverType.SERVER_SIDE:
            if signal.server_resolver is None:
                raise SignalRegistrationError(
                    f"server_side signal {signal.name!r} must declare a server_resolver",
                )
        elif signal.resolver_type == ResolverType.CLIENT_SIDE_STATE:
            if not signal.uitour_key or not signal.uitour_extractor:
                raise SignalRegistrationError(
                    f"client_side_state signal {signal.name!r} must declare uitour_key and uitour_extractor",
                )
        else:
            raise SignalRegistrationError(f"Unknown resolver_type: {signal.resolver_type!r}")

        self._signals[signal.name] = signal

    def get(self, name: str) -> Signal | None:
        return self._signals.get(name)

    def all(self) -> list[Signal]:
        return list(self._signals.values())

    def by_resolver_type(self, resolver_type: ResolverType) -> list[Signal]:
        return [s for s in self._signals.values() if s.resolver_type == resolver_type]

    def resolve_server_signals(
        self,
        request: Any,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve every SERVER_SIDE signal for this request.

        Returns a dict of ``{signal_name: value}``. Signals whose resolver
        returns ``None`` are omitted — absence means "unknown" to the rule
        evaluator, which is different from ``False``.
        """
        context = context or {}
        resolved: dict[str, Any] = {}
        for signal in self._signals.values():
            if signal.resolver_type != ResolverType.SERVER_SIDE:
                continue
            try:
                value = signal.server_resolver(request, context)
            except Exception:
                logger.exception("Signal resolver failed for %r", signal.name)
                continue
            if value is not None:
                resolved[signal.name] = value
        return resolved

    def clear(self) -> None:
        """Remove all registered signals. Intended for tests only."""
        self._signals.clear()


# The single, module-level registry. Import this from consumers:
#     from springfield.cms.routing import registry
registry = SignalRegistry()
