# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The concrete v1 routing signals.

Registering this module populates the framework-wide ``registry`` (spec §4) with
the v1 signals across the four live sources (spec §4.2). It is imported once at app
startup (``CmsConfig.ready``) so the registry is populated before any admin surface
or resolver reads it.

Descriptions are deliberately honest about edge cases (spec §4.4): the ``is_firefox``
signal documents its FxiOS match, and ``firefox_version`` documents version-string
normalization. All author-facing strings are wrapped in ``gettext_lazy``.
"""

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from springfield.cms.routing.signals import (
    EnumValue,
    RoutingSignal,
    Source,
    ValueType,
    registry,
)

# ---------------------------------------------------------------------------
# CDN geo header (spec §4.2)
# ---------------------------------------------------------------------------

# Country is a large, locale-dependent set (~270 regions sourced from
# product_details and localized per page), so it is modelled as a free-text string
# of ISO 3166-1 alpha-2 codes rather than a static enum — the enumerated-set and
# per-locale-label machinery does not fit a closed registry entry. Authors match it
# with `is` / `in` against uppercase codes.
registry.register(
    RoutingSignal(
        name="country",
        description=_(
            "The visitor's country, as an uppercase ISO 3166-1 alpha-2 code (e.g. US, DE, GB). "
            "Derived from the CDN geo header, which the client cannot read directly, so it is "
            "server-rendered into a DOM attribute the resolver reads."
        ),
        source=Source.CDN_GEO,
        value_type=ValueType.STRING,
    )
)


# ---------------------------------------------------------------------------
# User-Agent, via Mozilla.Client (spec §4.2)
# ---------------------------------------------------------------------------

registry.register(
    RoutingSignal(
        name="platform",
        description=_(
            "The visitor's operating-system platform, derived from the User-Agent via Mozilla.Client. "
            "The resolver never parses the raw User-Agent itself."
        ),
        source=Source.USER_AGENT,
        value_type=ValueType.ENUM,
        enum_values=(
            EnumValue("windows", _("Windows")),
            EnumValue("osx", _("macOS")),
            EnumValue("linux", _("Linux")),
            EnumValue("android", _("Android")),
            EnumValue("ios", _("iOS")),
            EnumValue("other", _("Other")),
        ),
    )
)

registry.register(
    RoutingSignal(
        name="firefox_version",
        description=_(
            "The visitor's Firefox version, read from the User-Agent via Mozilla.Client and compared "
            "with version-aware comparison (not string comparison). The incoming value is normalized "
            "first: it may arrive bare (129), prefixed (rv:129), or fully qualified (129.0.1), and all "
            "three normalize to the same version before comparison."
        ),
        source=Source.USER_AGENT,
        value_type=ValueType.VERSION,
    )
)

registry.register(
    RoutingSignal(
        name="is_firefox",
        description=_(
            "Whether the browser is Firefox on any platform, as reported by Mozilla.Client.isFirefox. "
            "Note: this also matches Firefox for iOS (FxiOS), which is built on WebKit. To exclude iOS, "
            "combine this with the `platform` signal (platform is not ios)."
        ),
        source=Source.USER_AGENT,
        value_type=ValueType.BOOLEAN,
    )
)


# ---------------------------------------------------------------------------
# UITour — Firefox-only browser state, read via a per-key ping (spec §4.2)
# ---------------------------------------------------------------------------

registry.register(
    RoutingSignal(
        name="is_default_browser",
        description=_(
            "Whether Firefox is the visitor's default browser. Read via UITour, so it is only available "
            "in Firefox and is subject to the per-key ping timeout."
        ),
        source=Source.UITOUR,
        value_type=ValueType.BOOLEAN,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="profile_age",
        description=_(
            "The age of the visitor's Firefox profile, in days. Read via UITour, so it is only available "
            "in Firefox and is subject to the per-key ping timeout."
        ),
        source=Source.UITOUR,
        value_type=ValueType.INTEGER,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="fxa_signed_in",
        description=_(
            "Whether the visitor is signed in to a Firefox Account. Read via UITour, so it is only "
            "available in Firefox and is subject to the per-key ping timeout."
        ),
        source=Source.UITOUR,
        value_type=ValueType.BOOLEAN,
        browser_state_key="sync",
    )
)

registry.register(
    RoutingSignal(
        name="ai_controls",
        description=_(
            "The state of the browser's AI controls configuration. Read via UITour, so it is only "
            "available in Firefox and is subject to the per-key ping timeout."
        ),
        source=Source.UITOUR,
        value_type=ValueType.ENUM,
        enum_values=(
            EnumValue("enabled", _("Enabled")),
            EnumValue("available", _("Available")),
            EnumValue("blocked", _("Blocked")),
        ),
        browser_state_key="aiControls",
    )
)


# ---------------------------------------------------------------------------
# URL query params (spec §4.2) — reuses the URL-reading machinery that already
# exists for the trigger, loop-breaker, and preview flows.
# ---------------------------------------------------------------------------

for _param in ("utm_source", "utm_medium", "utm_campaign"):
    registry.register(
        RoutingSignal(
            name=_param,
            description=format_lazy(
                _("The value of the `{param}` query parameter on the current URL. Free text; matched with `is` / `in` against expected values."),
                param=_param,
            ),
            source=Source.URL,
            value_type=ValueType.STRING,
        )
    )

# The version the visitor is updating *from*, sent by Balrog's just-updated flow as
# `?oldversion=`. A version signal (not free text) so authors express "lapsed from an
# old release" with version-aware operators, e.g. `oldversion lte 151` on a canonical
# for 156 — the plan's replacement for a dedicated `lapsed_user` signal.
registry.register(
    RoutingSignal(
        name="oldversion",
        description=_(
            "The Firefox version the visitor updated from, read from the `oldversion` query parameter "
            "(sent by the just-updated flow). Compared with version-aware comparison (not string "
            "comparison); the value is normalized first, so it may arrive bare (129), prefixed (rv:129), "
            "or fully qualified (129.0.1). Express lapsing as e.g. `oldversion lte 151`."
        ),
        source=Source.URL,
        value_type=ValueType.VERSION,
    )
)

# The page locale, read from the URL (an explicit `?locale=` override) and falling back
# to the page's `<html lang>`. Free text (not a static enum): the locale set is lazy and
# DB/product-details-backed, so surfacing it as a closed enum would reintroduce the
# app-init DB access the framework avoids. Authors match with `is` / `in`.
registry.register(
    RoutingSignal(
        name="locale",
        description=_(
            "The visitor's page locale, e.g. en-US, de, pt-BR. Read from the URL, falling back to the "
            "page's <html lang>. Free text; matched with `is` / `in` against expected locale codes."
        ),
        source=Source.URL,
        value_type=ValueType.STRING,
    )
)
