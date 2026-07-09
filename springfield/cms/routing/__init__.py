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
from .evaluator import EvaluationResult, evaluate_rules, rule_needs_client_side
from .signals import (
    ResolverType,
    Signal,
    SignalRegistrationError,
    SignalRegistry,
    registry,
)

__all__ = [
    "EvaluationResult",
    "ResolverType",
    "Signal",
    "SignalRegistrationError",
    "SignalRegistry",
    "evaluate_rules",
    "registry",
    "rule_needs_client_side",
]


# ---------------------------------------------------------------------------
# Initial signal set. Registered at import time so any consumer that imports
# ``springfield.cms.routing`` gets a populated registry.
# ---------------------------------------------------------------------------


def _register_default_signals() -> None:
    # --- Server-side (resolvable at request time, no client involvement) ---
    registry.register(
        Signal(
            name="country",
            description="ISO-3166 country code from the CDN geo header.",
            resolver_type=ResolverType.SERVER_SIDE,
            supports_routing=True,
            supports_in_page_swap=True,
            server_resolver=_sr.resolve_country,
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
        )
    )

    # --- Client-side (UITour) ---
    # Values are resolved by the client-side resolver library after page load.
    # ``uitour_extractor`` names a client-side extractor function; the JS-side
    # resolver library maintains the name → function mapping.
    registry.register(
        Signal(
            name="default_browser",
            description="True if Firefox is the default browser on this system.",
            resolver_type=ResolverType.CLIENT_SIDE_STATE,
            supports_routing=True,
            supports_in_page_swap=True,
            uitour_key="appinfo",
            uitour_extractor="default_browser",
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
        )
    )


_register_default_signals()
