# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Centralized routing query-param names.

Single source of truth for the query params the framework reads across the serve-path
dispatcher, the resolver, the loop-breaker, and the preview flows — so no later commit
hardcodes these string literals.
"""

# Default trigger param whose presence arms routing for a surface (spec §2.2). A
# consumer supplies its own arming condition (C14); this is the canonical param the
# query-param realization uses unless a consumer overrides it.
TRIGGER_PARAM = "routing"

# Loop-breaker marker (spec §7.4). When the resolver falls through (no match / timeout)
# it navigates to the canonical URL with this param appended; the dispatcher serves
# canonical content on any non-empty value, so a fallen-through user cannot re-enter.
LOOP_BREAKER_PARAM = "routed"

# Preview flow params (spec §8), both admin-authenticated only.
PREVIEW_RULE_PARAM = "preview_rule"
PREVIEW_SIGNAL_PARAM = "preview_signal"
