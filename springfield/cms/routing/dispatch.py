# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The serve-path routing decision.

A pure function of flags — no request, no page, no Wagtail — so the highest-risk logic
is exhaustively testable and policy stays out of the ``serve()`` adapter.

``is_paused``, ``is_canonical``, and ``has_live_rules`` arrive as callables, consulted
only if the order below reaches them. As values they would cost a query each on every
request to an adopted page, including while the switch is off.

The order is fixed and must not be reordered:

0. Switch off              → canonical
1. Loop-breaker present    → canonical  (before everything else, so a visitor who has
                                         fallen through cannot re-enter)
2. Preview param + admin   → preview
3. Kill switch engaged     → canonical
4. Triggered, canonical, ≥1 live rule → resolver
5. Otherwise               → canonical
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
    ``is_paused``, ``is_canonical``, and ``has_live_rules`` are callables — see the
    module docstring.
    """
    if not routing_enabled:
        return SERVE_CANONICAL
    if has_loop_breaker:
        return SERVE_CANONICAL
    if is_preview_admin:
        return SERVE_PREVIEW
    if is_paused():
        return SERVE_CANONICAL
    # `and` short-circuits, so an untriggered request never reaches is_canonical/
    # has_live_rules — which is every organic request to an adopted page.
    if trigger_satisfied and is_canonical() and has_live_rules():
        return SERVE_RESOLVER
    return SERVE_CANONICAL
