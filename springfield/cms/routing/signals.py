# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Signal registry — the catalog of every conditional signal the routing layer
knows about.

A signal is a named thing that rules reference by name (e.g. ``lapsed_user``,
``ai_controls``, ``country``). Under the client-side architecture, every
signal is resolved in the browser by ``media/js/cms/user-routing-resolver.js``.
The registry here declares metadata the admin needs (display name, value
type, admin dropdown choices) and — for UITour-resolved signals — the
UITour ``getConfiguration`` key the client should fetch.

``resolver_type`` categorizes signals by *where the value comes from*:

  * ``SERVER_SIDE`` — the value is either server-rendered onto the page
    (like ``country`` via the ``data-country-code`` attribute) or derived
    from data available to any JS on the page (URL, User-Agent). No UITour
    involvement, no async wait. Kept the name for backward compatibility
    with existing data (rules and admin listings).
  * ``CLIENT_SIDE_STATE`` — the value can only be obtained via
    ``Mozilla.UITour.getConfiguration()``. Declares the ``uitour_key`` the
    client should fetch and the ``uitour_extractor`` name that identifies
    which client-side extractor function converts the response.

Signals also declare where they may be used:

  * ``supports_routing`` — can drive a whole-page variant.
  * ``supports_in_page_swap`` — can gate a block inside a rendered page.

The registry is the single source of truth. The client's resolver JS has
a hardcoded map of signal name → resolution mechanism; the server-side
registry emits UITour metadata into the resolver page's JSON blob so the
client knows which UITour key to fetch per signal.
"""

from dataclasses import dataclass
from enum import Enum


class ResolverType(str, Enum):
    """How a signal's value is obtained (informational; the client-side
    resolver has the actual per-signal resolution logic)."""

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
        resolver_type: SERVER_SIDE (server-rendered / UA / URL) or
            CLIENT_SIDE_STATE (UITour-resolved). Informational only —
            client-side resolver JS decides how to actually fetch each signal.
        supports_routing: Whether this signal may gate a whole-page variant.
        supports_in_page_swap: Whether this signal may gate an in-page block.
        uitour_key: For CLIENT_SIDE_STATE signals: the ``Mozilla.UITour``
            ``getConfiguration`` key to fetch (e.g. ``"appinfo"``, ``"fxa"``).
            Emitted into the resolver page's ``signal_metadata`` JSON so the
            client knows which key to fetch per signal.
        uitour_extractor: For CLIENT_SIDE_STATE signals: the name of a
            client-side extractor that converts the UITour response into
            the signal's value. Purely for documentation / cross-reference
            — the client-side resolver library maps signal name to extractor
            function directly.
        value_type: The signal's value type. Drives the admin form widget
            and rule-value parsing.
        enum_values: For STRING-typed signals with a bounded set of legal
            values (e.g. ``ai_controls`` returns one of "enabled" /
            "available" / "blocked"). Used by the admin to render a
            dropdown instead of a free-text input.
        source: Human-readable source label surfaced in the Signals
            reference admin page — where the signal's value actually comes
            from (e.g. "UITour", "User-Agent", "URL", "CDN geo header").
            Authors read this to decide whether a signal will add a UITour
            delay for matched users.
    """

    name: str
    description: str
    resolver_type: ResolverType
    supports_routing: bool
    supports_in_page_swap: bool
    uitour_key: str | None = None
    uitour_extractor: str | None = None
    value_type: SignalValueType = SignalValueType.STRING
    enum_values: tuple[str, ...] | None = None
    source: str = ""


class SignalRegistrationError(ValueError):
    """Raised when a signal registration is invalid or duplicated."""


class SignalRegistry:
    """Catalog of registered signals. Consumed by the rule admin (for the
    signal-name dropdown), the resolver page (for the ``signal_metadata``
    JSON blob), and the signals reference admin view."""

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

        if signal.resolver_type == ResolverType.CLIENT_SIDE_STATE:
            if not signal.uitour_key or not signal.uitour_extractor:
                raise SignalRegistrationError(
                    f"client_side_state signal {signal.name!r} must declare uitour_key and uitour_extractor",
                )
        elif signal.resolver_type != ResolverType.SERVER_SIDE:
            raise SignalRegistrationError(f"Unknown resolver_type: {signal.resolver_type!r}")

        self._signals[signal.name] = signal

    def get(self, name: str) -> Signal | None:
        return self._signals.get(name)

    def all(self) -> list[Signal]:
        return list(self._signals.values())

    def clear(self) -> None:
        """Remove all registered signals. Intended for tests only."""
        self._signals.clear()


# The single, module-level registry. Import this from consumers:
#     from springfield.cms.routing import registry
registry = SignalRegistry()
