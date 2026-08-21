# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Exhaustive tests for the pure serve-path decision.

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


# An independent transcription of the serve-path decision plus the outermost switch, written as an
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


# These three are callables in the real signature. The truth table below reasons in
# plain booleans, so wrap them at the call site.
LAZY_FLAGS = ("is_paused", "is_canonical", "has_live_rules")


def decide(**flags):
    kwargs = dict(flags)
    for name in LAZY_FLAGS:
        kwargs[name] = lambda value=kwargs[name]: value
    return decide_routing(**kwargs)


ALL_FLAG_COMBINATIONS = [dict(zip(FLAG_NAMES, values)) for values in itertools.product([False, True], repeat=len(FLAG_NAMES))]


# ---------------------------------------------------------------------------
# Exhaustive truth table: all 2^7 = 128 flag combinations.
# ---------------------------------------------------------------------------


def test_covers_every_flag_combination():
    assert len(ALL_FLAG_COMBINATIONS) == 128


@pytest.mark.parametrize("flags", ALL_FLAG_COMBINATIONS)
def test_decision_matches_spec_order_for_every_combination(flags):
    assert decide(**flags) == expected_decision(flags)


# ---------------------------------------------------------------------------
# Critical invariants, pinned to explicit expected values (not via the oracle).
# ---------------------------------------------------------------------------


def _flags(**overrides):
    base = dict.fromkeys(FLAG_NAMES, False)
    base.update(overrides)
    return base


def test_switch_off_short_circuits_everything():
    # Every downstream flag set to "would route/preview", but the switch is off.
    result = decide(
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
    result = decide(
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
    assert decide(**{**routed, "is_preview_admin": True}) == SERVE_PREVIEW
    # Without the preview-admin flag, the pause takes over -> canonical.
    assert decide(**{**routed, "is_preview_admin": False}) == SERVE_CANONICAL


def test_pause_short_circuits_the_resolver():
    result = decide(**_flags(routing_enabled=True, is_paused=True, trigger_satisfied=True, is_canonical=True, has_live_rules=True))
    assert result == SERVE_CANONICAL


def test_resolver_requires_trigger_canonical_and_live_rules():
    routes = _flags(routing_enabled=True, trigger_satisfied=True, is_canonical=True, has_live_rules=True)
    assert decide(**routes) == SERVE_RESOLVER
    # Dropping any one of the three falls back to canonical.
    assert decide(**{**routes, "trigger_satisfied": False}) == SERVE_CANONICAL
    assert decide(**{**routes, "is_canonical": False}) == SERVE_CANONICAL
    assert decide(**{**routes, "has_live_rules": False}) == SERVE_CANONICAL


def test_untriggered_traffic_is_canonical():
    # The organic case: enabled, canonical, has rules, but no trigger -> canonical.
    result = decide(**_flags(routing_enabled=True, is_canonical=True, has_live_rules=True, trigger_satisfied=False))
    assert result == SERVE_CANONICAL


# ---------------------------------------------------------------------------
# The database-backed flags are only consulted if precedence reaches them. Passing
# them as values instead would put a pause read and a rule scan on every request to
# an adopted page — including while the switch is off, which must cost nothing.
# ---------------------------------------------------------------------------


class _Counter:
    """A flag callable that records whether anything asked for its value."""

    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


def _decide_counting(**overrides):
    flags = _flags(**overrides)
    paused = _Counter(flags["is_paused"])
    canonical = _Counter(flags["is_canonical"])
    live = _Counter(flags["has_live_rules"])
    flags["is_paused"] = paused
    flags["is_canonical"] = canonical
    flags["has_live_rules"] = live
    return decide_routing(**flags), paused, canonical, live


@pytest.mark.parametrize(
    ("label", "overrides"),
    (
        ("switch off", {"routing_enabled": False}),
        ("loop breaker", {"routing_enabled": True, "has_loop_breaker": True}),
        ("admin preview", {"routing_enabled": True, "is_preview_admin": True}),
    ),
)
def test_none_of_the_database_flags_is_read_before_its_gate(label, overrides):
    # All three exit above the pause check, so none of the callables may be touched.
    _, paused, canonical, live = _decide_counting(**overrides, trigger_satisfied=True, is_canonical=True, has_live_rules=True)
    assert paused.calls == 0, label
    assert canonical.calls == 0, label
    assert live.calls == 0, label


def test_the_rule_scan_is_skipped_for_untriggered_traffic():
    # The common case by volume: organic visitors to an adopted page. The pause is read;
    # is_canonical and the rule scan are not, since `and` short-circuits on the trigger.
    _, paused, canonical, live = _decide_counting(routing_enabled=True, is_canonical=True, has_live_rules=True, trigger_satisfied=False)
    assert paused.calls == 1
    assert canonical.calls == 0
    assert live.calls == 0


def test_the_rule_scan_is_skipped_on_a_non_canonical_page():
    _, _, canonical, live = _decide_counting(routing_enabled=True, trigger_satisfied=True, is_canonical=False, has_live_rules=True)
    assert canonical.calls == 1
    assert live.calls == 0
