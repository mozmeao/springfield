# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The concrete v1 routing signals.

Importing this module registers them, once, at app startup (``CmsConfig.ready``) — before
any admin surface or resolver reads the registry.

Descriptions are editor-facing and localized; where a signal's coverage is non-obvious it
says so (e.g. ``is_firefox`` matches desktop, iOS and Android).
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

# A string, not an enum: ~270 regions sourced from product_details and localized per page
# do not fit a static registry enum. Validated against the full list in value_lists.
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
        name="profile_age_weeks",
        # Weeks, not days: UITour reports whole weeks since the profile was created, so
        # day-level targeting is not available to express. A profile created this week reads 0.
        description=_("How many whole weeks old the visitor's Firefox profile is. A profile created this week reads 0."),
        source=Source.UITOUR,
        value_type=ValueType.INTEGER,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="fxa_signed_in",
        # Reads the `fxa` key, not the deprecated `sync` key: `sync.setup` only reports
        # that Sync has been configured, which is not the same as being signed in.
        description=_("Whether the visitor is signed in to a Firefox Account."),
        source=Source.UITOUR,
        value_type=ValueType.BOOLEAN,
        browser_state_key="fxa",
    )
)

registry.register(
    RoutingSignal(
        name="days_since_last_session",
        # `previousSessionEnd` is written only when Firefox fully quits, so this measures
        # days since the browser was last *closed*, not since the visitor was last active —
        # a long-running session that never restarts reads as lapsed until it does. Landed
        # in Firefox 155 (2026-08-05); reads unavailable on older releases and for a
        # profile with no recorded previous session.
        description=_("How many whole days since the visitor's previous Firefox session ended (i.e. since Firefox was last closed)."),
        source=Source.UITOUR,
        value_type=ValueType.INTEGER,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="profile_reset_weeks_ago",
        # Whole weeks, reported directly, mirroring profile_age_weeks. Unavailable if the
        # visitor has never reset (refreshed) their profile.
        description=_("How many whole weeks since the visitor last reset (refreshed) their Firefox profile."),
        source=Source.UITOUR,
        value_type=ValueType.INTEGER,
        browser_state_key="appinfo",
    )
)

registry.register(
    RoutingSignal(
        name="ai_controls",
        # Firefox reports a state per AI feature with no overall summary, and the set of
        # features grows with each release. The client collapses them into the posture
        # below so a rule never has to name individual features, and so a new Firefox
        # feature does not need a new signal here.
        description=_("What the visitor has chosen in Firefox's AI controls, summarised across all AI features."),
        source=Source.UITOUR,
        value_type=ValueType.ENUM,
        enum_values=(
            EnumValue("neutral", _("No choice made")),
            EnumValue("enabled_some", _("Turned some AI features on")),
            EnumValue("blocked_some", _("Blocked some AI features")),
            EnumValue("blocked_all", _("Blocked all AI features")),
            EnumValue("mixed", _("Turned some on and blocked others")),
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

# Sent by Firefox's just-updated flow as `?oldversion=`. A version signal, not free text, so
# "lapsed from an old release" is expressible: `oldversion lte 151` on a canonical for 156.
registry.register(
    RoutingSignal(
        name="oldversion",
        description=_("The Firefox version the visitor updated from."),
        source=Source.URL,
        value_type=ValueType.VERSION,
    )
)

# Read from the page's `<html lang>`, never from a query param — a visitor must not be able to
# choose their own locale. A string, not an enum, for the reason in value_lists: the set is lazy
# and data-backed.
registry.register(
    RoutingSignal(
        name="locale",
        description=_("The visitor's page locale, including region (e.g. en-US, de, pt-BR). Use “language” to match every region at once."),
        source=Source.URL,
        value_type=ValueType.STRING,
    )
)

# The same locale with the region dropped, so one condition covers every regional variant.
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

# Coarse user-agent detection, matching the browsers our own comparison tables name
# (TabBlock's "Detected browser" field). Works off Firefox too, unlike the UITour
# signals above. Brave ships Chrome's user agent verbatim, so it is only distinguished
# from Chrome by an extra, best-effort browser API check.
registry.register(
    RoutingSignal(
        name="browser_name",
        description=_("The visitor's browser (Firefox, Chrome, Edge, Opera, Safari, or Brave), or “other” for anything else."),
        source=Source.USER_AGENT,
        value_type=ValueType.ENUM,
        enum_values=(
            EnumValue("firefox", _("Firefox")),
            EnumValue("chrome", _("Chrome")),
            EnumValue("edge", _("Edge")),
            EnumValue("opera", _("Opera")),
            EnumValue("safari", _("Safari")),
            EnumValue("brave", _("Brave")),
            EnumValue("other", _("Other")),
        ),
    )
)
