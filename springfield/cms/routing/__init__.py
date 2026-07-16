# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Routing layer for CMS-driven conditional rendering.

The primitives here (:mod:`.signals`, :mod:`.server_resolvers`) are page-type
agnostic. WNP is the first customer; downloads / landings / SmartWindow can
adopt the same infrastructure by wiring their own canonical page type and
trigger. See ``.research/wnp-dynamic-rendering-plan.md`` for the full design.
"""

from . import server_resolvers as _sr
from .dispatcher import dispatch_for_canonical
from .evaluator import EvaluationResult, evaluate_rules, rule_needs_client_side
from .signals import (
    ResolverType,
    Signal,
    SignalRegistrationError,
    SignalRegistry,
    SignalValueType,
    registry,
)

__all__ = [
    "EvaluationResult",
    "ResolverType",
    "Signal",
    "SignalRegistrationError",
    "SignalRegistry",
    "SignalValueType",
    "dispatch_for_canonical",
    "evaluate_rules",
    "registry",
    "rule_needs_client_side",
]


# ---------------------------------------------------------------------------
# Initial signal set. Registered at import time so any consumer that imports
# ``springfield.cms.routing`` gets a populated registry.
# ---------------------------------------------------------------------------


def _register_default_signals() -> None:
    # Country enum matches the existing GEO_CHOICES allowlist so marketing
    # sees exactly the same country set they know from other blocks.
    # Local import avoids a circular reference at package init time.
    from springfield.cms.blocks import GEO_CHOICES

    country_enum = tuple(code for code, _label in GEO_CHOICES)

    # --- Server-side (resolvable at request time, no client involvement) ---
    registry.register(
        Signal(
            name="country",
            # Country is the highest-cardinality server-side signal in the
            # registry (~200 raw values, ~4-8 useful buckets). It is NOT
            # cache-safe by default: using it server-side without extending
            # the Fastly VCL cache key to include the (bucketed) country
            # would silently poison cached responses — a US visitor's cached
            # variant could be served to a UK visitor. Coordinate with the
            # Websites team on VCL changes before flipping cache_safe=True.
            description=(
                "ISO-3166 country code from the CDN geo header. Server-side use requires Fastly VCL cache-key extension — not cache-safe by default."
            ),
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_country,
            value_type=SignalValueType.STRING,
            enum_values=country_enum,
            cache_safe=False,
        )
    )
    registry.register(
        Signal(
            name="locale",
            description="Locale code the URL was routed under (e.g. en-US, pt-BR).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_locale,
            value_type=SignalValueType.STRING,
        )
    )
    registry.register(
        Signal(
            name="lapsed_user",
            description=("True if the user's oldversion (from the Balrog redirect) is at least 5 major versions behind the target version."),
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_lapsed_user,
            value_type=SignalValueType.BOOL,
        )
    )
    registry.register(
        Signal(
            name="platform",
            description="OS family from the User-Agent: osx, linux, windows, android, ios, other-os.",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_platform,
            value_type=SignalValueType.STRING,
            enum_values=("osx", "linux", "windows", "android", "ios", "other-os"),
        )
    )
    registry.register(
        Signal(
            name="os_version",
            description="OS-version refinement (currently: windows-10-plus).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_os_version,
            value_type=SignalValueType.STRING,
            enum_values=("windows-10-plus",),
        )
    )
    registry.register(
        Signal(
            name="is_firefox",
            description="True if the User-Agent identifies as Firefox (excluding derivatives).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_is_firefox,
            value_type=SignalValueType.BOOL,
        )
    )
    registry.register(
        Signal(
            name="firefox_version",
            description="Major Firefox version from the User-Agent (integer).",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_firefox_version,
            value_type=SignalValueType.INT,
        )
    )

    # --- Client-side (UITour) ---
    # Values are resolved by the client-side resolver library after page load.
    # ``uitour_extractor`` names a client-side extractor function; the JS-side
    # resolver library maintains the name → function mapping.
    #
    # Client-side signals are inherently ``cache_safe=True``: they don't
    # affect the Fastly cache key because they resolve AFTER the response
    # is served (in the browser, not by the CDN).
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
            cache_safe=True,
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
            cache_safe=True,
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
            cache_safe=True,
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
            cache_safe=True,
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
            cache_safe=True,
        )
    )


_register_default_signals()
