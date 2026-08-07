# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Centralized routing query-param names.

Single source of truth for the query params the framework reads across the serve-path
dispatcher, the resolver, the loop-breaker, and the preview flows — so no later commit
hardcodes these string literals.
"""

# Default trigger param whose presence arms routing for a surface. A
# consumer supplies its own arming condition; this is the canonical param the
# query-param realization uses unless a consumer overrides it.
TRIGGER_PARAM = "routing"

# Loop-breaker marker. When the resolver falls through (no match / timeout)
# it navigates to the canonical URL with this param appended; the dispatcher serves
# canonical content on any non-empty value, so a fallen-through user cannot re-enter.
LOOP_BREAKER_PARAM = "routed"

# Preview flow params, both admin-authenticated only.
PREVIEW_RULE_PARAM = "preview_rule"
PREVIEW_SIGNAL_PARAM = "preview_signal"

# The framework's own control params, which must never be carried onto a destination: they
# would re-arm routing, re-enter the loop, or leak preview state. Anything else a visitor
# arrived with is attribution and rides along.
#
# ``RESERVED_ROUTING_PARAMS`` in ``resolver.es6.js`` mirrors this list by hand — the client
# has no way to read it — so a change here needs the same change there.
RESERVED_ROUTING_PARAMS = (TRIGGER_PARAM, LOOP_BREAKER_PARAM, PREVIEW_RULE_PARAM, PREVIEW_SIGNAL_PARAM)
