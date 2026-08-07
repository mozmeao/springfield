# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The serve-path routing decision.

The decision order is expressed as a **pure function** of boolean flags — no request,
no page, no Wagtail. This is what makes the highest-risk logic exhaustively testable
without a mixin-bearing page and keeps routing *policy* separate from
Wagtail plumbing (the thin ``serve()`` adapter lives on ``RoutingMixin``).

The order is fixed and must not be reordered:

0. Global ``user_routing`` switch off  → canonical  (outermost operational gate)
1. Loop-breaker marker present         → canonical  (checked FIRST after the switch, so
                                                      a fallen-through user can never
                                                      re-enter routing)
2. Preview param + admin               → preview flow
3. Kill switch engaged                 → canonical
4. Trigger satisfied AND live canonical
   with >= 1 live rule                 → resolver page
5. Otherwise                           → canonical
"""

# The waffle switch name that gates the whole framework (ships off — dark).
USER_ROUTING_SWITCH = "user_routing"

# Decision outcomes.
SERVE_CANONICAL = "canonical"
SERVE_PREVIEW = "preview"
SERVE_RESOLVER = "resolver"


def decide_routing(
    *,
    routing_enabled,
    has_loop_breaker,
    is_preview_admin,
    is_paused,
    trigger_satisfied,
    is_canonical,
    has_live_rules,
):
    """Return the serve-path branch for the given flags.

    Keyword-only args so the flag mapping is always explicit at the call site.
    """
    if not routing_enabled:
        return SERVE_CANONICAL
    if has_loop_breaker:
        return SERVE_CANONICAL
    if is_preview_admin:
        return SERVE_PREVIEW
    if is_paused:
        return SERVE_CANONICAL
    if trigger_satisfied and is_canonical and has_live_rules:
        return SERVE_RESOLVER
    return SERVE_CANONICAL
