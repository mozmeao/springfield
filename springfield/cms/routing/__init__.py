# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Routing layer for CMS-driven conditional rendering.

Under the client-side architecture, all rule evaluation happens in the
browser via ``media/js/cms/user-routing-resolver.js``. The server-side
role is:

* Model + admin (:mod:`.models`, :mod:`.admin_views`) — marketing authors
  rules via the Wagtail admin.
* Dispatcher (:mod:`.dispatcher`) — for marker'd traffic, renders the
  resolver page with the live rule set. Server does no rule matching.
* Signal registry (:mod:`.signals`) — catalog of signal metadata (name,
  description, value type, admin dropdown choices, UITour key mapping).

WNP is the first consumer. Other page types (landing pages, downloads)
adopt the same infrastructure by wiring their own canonical page class,
their own request-marker gate, and the same dispatcher.
"""

from .dispatcher import dispatch_for_canonical
from .signals import (
    ResolverType,
    Signal,
    SignalRegistrationError,
    SignalRegistry,
    SignalValueType,
    registry,
)

__all__ = [
    "ResolverType",
    "Signal",
    "SignalRegistrationError",
    "SignalRegistry",
    "SignalValueType",
    "dispatch_for_canonical",
    "registry",
]


# ---------------------------------------------------------------------------
# Initial signal set. Registered at import time so any consumer that imports
# ``springfield.cms.routing`` gets a populated registry.
#
# ``resolver_type`` categorizes signals for the admin (server-side signals
# show as "server", UITour-resolved as "browser"). The client-side resolver
# JS has a hardcoded map of signal name → resolution mechanism; it doesn't
# read ``resolver_type`` from the registry. Adding a new signal requires
# registering it here AND adding the resolution logic in the resolver JS.
# ---------------------------------------------------------------------------


def _register_default_signals() -> None:
    # Country enum matches the existing GEO_CHOICES allowlist so marketing
    # sees exactly the same country set they know from other blocks.
    # Local import avoids a circular reference at package init time.
    from springfield.cms.blocks import GEO_CHOICES

    country_enum = tuple(code for code, _label in GEO_CHOICES)

    # --- Server-side (resolvable from the initial rendered response) ---
    # Under the client-side architecture, "server-side" means "the value
    # is either server-rendered onto the page (country via data-country-code)
    # or derivable from data available to any JS on load (URL, User-Agent)."
    # The client-side resolver reads these synchronously with no UITour ping.
    registry.register(
        Signal(
            name="country",
            description=("ISO-3166 country code from the CDN geo header. Server-rendered onto <html data-country-code>; client reads it directly."),
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.STRING,
            enum_values=country_enum,
            source="CDN geo header",
        )
    )
    registry.register(
        Signal(
            name="locale",
            description="Locale code from the URL / <html lang> (e.g. en-US, pt-BR).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.STRING,
            source="URL / <html lang>",
        )
    )
    registry.register(
        Signal(
            name="lapsed_user",
            description=(
                "True if the user's oldversion (from the Balrog redirect querystring) "
                "is at least 5 major versions behind the target version in the URL path."
            ),
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.BOOL,
            source="URL",
        )
    )
    registry.register(
        Signal(
            name="platform",
            description="OS family from the User-Agent: osx, linux, windows, android, ios, other-os.",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.STRING,
            enum_values=("osx", "linux", "windows", "android", "ios", "other-os"),
            source="User-Agent",
        )
    )
    registry.register(
        Signal(
            name="is_firefox",
            description="True if the User-Agent identifies as Firefox (excluding derivatives).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.BOOL,
            source="User-Agent",
        )
    )
    registry.register(
        Signal(
            name="firefox_version",
            description="Major Firefox version from the User-Agent (integer).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            value_type=SignalValueType.INT,
            source="User-Agent",
        )
    )

    # --- Client-side (UITour) ---
    # Values are resolved by the client-side resolver library after page load
    # via ``Mozilla.UITour.getConfiguration()``. ``uitour_extractor`` names a
    # client-side extractor function; the JS-side resolver library maintains
    # the name → function mapping.
    registry.register(
        Signal(
            name="default_browser",
            description="True if Firefox is the default browser on this system.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="appinfo",
            uitour_extractor="default_browser",
            value_type=SignalValueType.BOOL,
            source="UITour",
        )
    )
    registry.register(
        Signal(
            name="firefox_pinned",
            description="True if Firefox is pinned to the taskbar/dock.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="appinfo",
            uitour_extractor="firefox_pinned",
            value_type=SignalValueType.BOOL,
            source="UITour",
        )
    )
    registry.register(
        Signal(
            name="profile_age_days",
            description="Age of the Firefox profile in days.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="appinfo",
            uitour_extractor="profile_age_days",
            value_type=SignalValueType.INT,
            source="UITour",
        )
    )
    registry.register(
        Signal(
            name="fxa_signed_in",
            description="True if the user is signed in to a Firefox Account.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="fxa",
            uitour_extractor="fxa_signed_in",
            value_type=SignalValueType.BOOL,
            source="UITour",
        )
    )
    registry.register(
        Signal(
            name="ai_controls",
            description="AI Controls setting: enabled / available / blocked.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="aiControls",
            uitour_extractor="ai_controls",
            value_type=SignalValueType.STRING,
            enum_values=("enabled", "available", "blocked"),
            source="UITour",
        )
    )


_register_default_signals()
