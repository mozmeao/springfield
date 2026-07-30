# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Exhaustive tests for the pure serve-path decision (C10, high-attention §0.7).

The decision function is the highest-blast-radius logic in the framework (a wrong
answer silently mis-routes organic or crawler traffic). It is pure, so we exercise it
over *every* combination of its flags and pin the critical orderings explicitly.
"""

import itertools

import pytest

from springfield.cms.routing.dispatch import (
    SERVE_CANONICAL,
    SERVE_PREVIEW,
    SERVE_RESOLVER,
    decide_routing,
)

FLAG_NAMES = (
    "routing_enabled",
    "has_loop_breaker",
    "is_preview_admin",
    "is_paused",
    "trigger_satisfied",
    "is_canonical",
    "has_live_rules",
)


# An independent transcription of spec §2.3 + the §0.5 outermost switch, written as an
# ordered priority scan rather than an if-chain, so it can disagree with a buggy
# decide_routing (e.g. wrong order, OR instead of AND in the resolver clause).
_ORDERED_RULES = (
    (lambda f: not f["routing_enabled"], SERVE_CANONICAL),
    (lambda f: f["has_loop_breaker"], SERVE_CANONICAL),
    (lambda f: f["is_preview_admin"], SERVE_PREVIEW),
    (lambda f: f["is_paused"], SERVE_CANONICAL),
    (lambda f: f["trigger_satisfied"] and f["is_canonical"] and f["has_live_rules"], SERVE_RESOLVER),
)


def expected_decision(flags):
    for predicate, outcome in _ORDERED_RULES:
        if predicate(flags):
            return outcome
    return SERVE_CANONICAL


ALL_FLAG_COMBINATIONS = [dict(zip(FLAG_NAMES, values)) for values in itertools.product([False, True], repeat=len(FLAG_NAMES))]


# ---------------------------------------------------------------------------
# Exhaustive truth table: all 2^7 = 128 flag combinations.
# ---------------------------------------------------------------------------


def test_covers_every_flag_combination():
    assert len(ALL_FLAG_COMBINATIONS) == 128


@pytest.mark.parametrize("flags", ALL_FLAG_COMBINATIONS)
def test_decision_matches_spec_order_for_every_combination(flags):
    assert decide_routing(**flags) == expected_decision(flags)


# ---------------------------------------------------------------------------
# Critical invariants, pinned to explicit expected values (not via the oracle).
# ---------------------------------------------------------------------------


def _flags(**overrides):
    base = dict.fromkeys(FLAG_NAMES, False)
    base.update(overrides)
    return base


def test_switch_off_short_circuits_everything():
    # Every downstream flag set to "would route/preview", but the switch is off.
    result = decide_routing(
        **_flags(
            routing_enabled=False,
            is_preview_admin=True,
            trigger_satisfied=True,
            is_canonical=True,
            has_live_rules=True,
        )
    )
    assert result == SERVE_CANONICAL


def test_loop_breaker_is_checked_before_everything_else():
    # A fallen-through user (loop-breaker present) who is also triggered on a live
    # canonical with rules — and even an admin preview — still gets canonical.
    result = decide_routing(
        **_flags(
            routing_enabled=True,
            has_loop_breaker=True,
            is_preview_admin=True,
            trigger_satisfied=True,
            is_canonical=True,
            has_live_rules=True,
        )
    )
    assert result == SERVE_CANONICAL


def test_preview_wins_over_pause_and_resolver_but_needs_the_flag():
    routed = _flags(routing_enabled=True, is_paused=True, trigger_satisfied=True, is_canonical=True, has_live_rules=True)
    assert decide_routing(**{**routed, "is_preview_admin": True}) == SERVE_PREVIEW
    # Without the preview-admin flag, the pause takes over -> canonical.
    assert decide_routing(**{**routed, "is_preview_admin": False}) == SERVE_CANONICAL


def test_pause_short_circuits_the_resolver():
    result = decide_routing(**_flags(routing_enabled=True, is_paused=True, trigger_satisfied=True, is_canonical=True, has_live_rules=True))
    assert result == SERVE_CANONICAL


def test_resolver_requires_trigger_canonical_and_live_rules():
    routes = _flags(routing_enabled=True, trigger_satisfied=True, is_canonical=True, has_live_rules=True)
    assert decide_routing(**routes) == SERVE_RESOLVER
    # Dropping any one of the three falls back to canonical.
    assert decide_routing(**{**routes, "trigger_satisfied": False}) == SERVE_CANONICAL
    assert decide_routing(**{**routes, "is_canonical": False}) == SERVE_CANONICAL
    assert decide_routing(**{**routes, "has_live_rules": False}) == SERVE_CANONICAL


def test_untriggered_traffic_is_canonical():
    # The organic case: enabled, canonical, has rules, but no trigger -> canonical.
    result = decide_routing(**_flags(routing_enabled=True, is_canonical=True, has_live_rules=True, trigger_satisfied=False))
    assert result == SERVE_CANONICAL
