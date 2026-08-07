# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The concrete v1 routing signals.

Registering this module populates the framework-wide ``registry`` with
the v1 signals across the four live sources. It is imported once at app
startup (``CmsConfig.ready``) so the registry is populated before any admin surface
or resolver reads it.

Descriptions are short and editor-facing; where a signal's coverage is non-obvious it
says so plainly (e.g. ``is_firefox`` matches Firefox on desktop, iOS, and Android). All
author-facing strings are wrapped in ``gettext_lazy``.
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
# CDN geo header
# ---------------------------------------------------------------------------

# Country is a large, locale-dependent set (~270 regions sourced from
# product_details and localized per page), so it is modelled as a free-text string
# of ISO 3166-1 alpha-2 codes rather than a static enum — the enumerated-set and
# per-locale-label machinery does not fit a closed registry entry. Authors match it
# with `is` / `in` against uppercase codes.
registry.register(
    RoutingSignal(
        name="country",
        description=_("The visitor's country, as an uppercase ISO code (e.g. US, DE, GB)."),
        source=Source.CDN_GEO,
        value_type=ValueType.STRING,
    )
)


# ---------------------------------------------------------------------------
# User-Agent, via Mozilla.Client
# ---------------------------------------------------------------------------

registry.register(
    RoutingSignal(
        name="platform",
        description=_("The visitor's operating system."),
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
        description=_("The visitor's Firefox version."),
        source=Source.USER_AGENT,
        value_type=ValueType.VERSION,
    )
)

registry.register(
    RoutingSignal(
        name="is_firefox",
        description=_("Whether the browser is Firefox (desktop, iOS, or Android)."),
        source=Source.USER_AGENT,
        value_type=ValueType.BOOLEAN,
    )
)


# ---------------------------------------------------------------------------
# UITour — Firefox-only browser state, read via a per-key ping
# ---------------------------------------------------------------------------

registry.register(
    RoutingSignal(
        name="is_default_browser",
        description=_("Whether Firefox is the visitor's default browser."),
        source=Source.UITOUR,
        value_type=ValueType.BOOLEAN,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="profile_age",
        description=_("How old the visitor's Firefox profile is, in days."),
        source=Source.UITOUR,
        value_type=ValueType.INTEGER,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="fxa_signed_in",
        description=_("Whether the visitor is signed in to a Firefox Account."),
        source=Source.UITOUR,
        value_type=ValueType.BOOLEAN,
        browser_state_key="sync",
    )
)

registry.register(
    RoutingSignal(
        name="ai_controls",
        description=_("The state of the browser's AI controls."),
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
# URL query params — reuses the URL-reading machinery that already
# exists for the trigger, loop-breaker, and preview flows.
# ---------------------------------------------------------------------------

for _param in ("utm_source", "utm_medium", "utm_campaign"):
    registry.register(
        RoutingSignal(
            name=_param,
            description=format_lazy(_("The `{param}` query parameter on the visitor's URL."), param=_param),
            source=Source.URL,
            value_type=ValueType.STRING,
        )
    )

# The version the visitor is updating *from*, sent by Firefox's just-updated flow as
# `?oldversion=`. A version signal (not free text) so authors express "lapsed from an
# old release" with version-aware operators, e.g. `oldversion lte 151` on a canonical
# for 156 — replacing a dedicated `lapsed_user` signal.
registry.register(
    RoutingSignal(
        name="oldversion",
        description=_("The Firefox version the visitor updated from."),
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
        description=_("The visitor's page locale, including region (e.g. en-US, de, pt-BR). Use “language” to match every region at once."),
        source=Source.URL,
        value_type=ValueType.STRING,
    )
)

# The same locale with the region dropped, so one condition covers every regional variant
# of a language. Only four languages have variants (en, es, pt, zh), but hand-listing them
# goes stale the moment another is added.
registry.register(
    RoutingSignal(
        name="language",
        description=_("The visitor's page language, ignoring region — “en” matches en-US, en-GB and en-CA."),
        source=Source.URL,
        value_type=ValueType.STRING,
    )
)

# What the *browser* prefers, which is not always what the page is in: a visitor whose
# language has no translation is served the best available one, so `locale` alone cannot
# tell you what they actually read. Read client-side from `navigator.languages` — never
# from the Accept-Language header, which would fragment the cacheable resolver page.
#
# Only the *top* preference is read. Reading the whole ordered list would make targeting
# browser-dependent rather than visitor-dependent: Safari and Brave always report a single
# language, and Chrome does so in private windows, so the same rule would define a wider
# audience for some browsers than others. Anti-fingerprinting settings (Firefox's
# privacy.resistFingerprinting among them) can also replace the value outright — the
# description says so rather than letting authors assume it is always the truth.
registry.register(
    RoutingSignal(
        name="browser_language",
        description=_(
            "The visitor's top browser language preference, which may differ from the page they were served. Some privacy settings hide or change it."
        ),
        source=Source.USER_AGENT,
        value_type=ValueType.STRING,
    )
)
