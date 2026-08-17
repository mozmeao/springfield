# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The query params routing reads, named in one place."""

# The default arming param. A consumer can supply its own arming condition instead.
TRIGGER_PARAM = "routing"

# Appended to the canonical URL when the resolver falls through, so a visitor who has
# already fallen through cannot re-enter routing. Any non-empty value counts.
LOOP_BREAKER_PARAM = "routed"

# Preview flow params, both admin-authenticated only.
PREVIEW_RULE_PARAM = "preview_rule"
PREVIEW_SIGNAL_PARAM = "preview_signal"

# Never carried onto a destination: they would re-arm routing, re-enter the loop, or leak
# preview state. Anything else the visitor arrived with is attribution and rides along.
# Mirrored by hand in resolver.es6.js, which cannot read this — change both together.
RESERVED_ROUTING_PARAMS = (TRIGGER_PARAM, LOOP_BREAKER_PARAM, PREVIEW_RULE_PARAM, PREVIEW_SIGNAL_PARAM)
