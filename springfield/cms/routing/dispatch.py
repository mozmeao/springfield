# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The serve-path routing decision.

A pure function of flags — no request, no page, no Wagtail — so the highest-risk logic
is exhaustively testable and policy stays out of the ``serve()`` adapter.

``is_paused``, ``is_canonical``, ``has_live_rules`` and ``has_server_match`` arrive as
callables, consulted only if the order below reaches them. As values they would cost a
query each on every request to an adopted page, including while the switch is off.

The order is fixed and must not be reordered. Step 4 depends on where the page matches:

| Step | Param trigger (browser)          | Organic trigger (server)                   |
|------|----------------------------------|--------------------------------------------|
| 0    | Switch off → canonical           | same                                       |
| 1    | Loop-breaker present → canonical | same (before everything else, so a visitor |
|      |                                  | who has fallen through cannot re-enter)    |
| 2    | Preview param + admin → preview  | same                                       |
| 3    | Kill switch engaged → canonical  | same                                       |
| 4    | Triggered, canonical, ≥1 live    | Triggered, canonical, a rule matches on    |
|      | rule → resolver                  | the server → redirect                      |
| 5    | Otherwise → canonical            | same                                       |
"""

# The waffle switch name that gates the whole framework (ships off — dark).
USER_ROUTING_SWITCH = "user_routing"

# Decision outcomes.
SERVE_CANONICAL = "canonical"
SERVE_PREVIEW = "preview"
SERVE_RESOLVER = "resolver"
SERVE_REDIRECT = "redirect"


def decide_routing(
    *,
    routing_enabled,
    has_loop_breaker,
    is_preview_admin,
    is_paused,
    trigger_satisfied,
    is_canonical,
    has_live_rules,
    matches_on_server=False,
    has_server_match=None,
):
    """Return the serve-path branch for the given flags.

    Keyword-only args so the flag mapping is always explicit at the call site.
    ``is_paused``, ``is_canonical``, ``has_live_rules`` and ``has_server_match`` are
    callables — see the module docstring.
    """
    if not routing_enabled:
        return SERVE_CANONICAL
    if has_loop_breaker:
        return SERVE_CANONICAL
    if is_preview_admin:
        return SERVE_PREVIEW
    if is_paused():
        return SERVE_CANONICAL
    # `and` short-circuits, so an untriggered request never reaches is_canonical or the
    # rules, and a non-canonical page never reaches the rules.
    if matches_on_server:
        if trigger_satisfied and is_canonical() and has_server_match():
            return SERVE_REDIRECT
    elif trigger_satisfied and is_canonical() and has_live_rules():
        return SERVE_RESOLVER
    return SERVE_CANONICAL
