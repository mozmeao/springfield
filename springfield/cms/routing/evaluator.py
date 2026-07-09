# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Rule evaluation.

Given a set of rules and a dict of resolved signals, decide whether any rule
fully matches (and if so, which one), and which rules remain undecidable
because their signals are not yet known.

Consumers:

* ``wnp_dispatch`` (server-side) — passes ``resolve_server_signals()`` output
  and gets back ``(matched, unresolved)``. If matched, 302 to variant; if
  unresolved rules reference client-side signals, may serve a resolver page
  (Step 3b) that runs client-side evaluation.
* The client-side resolver library (JS) mirrors this logic on ``Firefox.State``.

Condition shape (kept intentionally minimal — composite matchers come later):

    {"signal": "<name>", "equals": <value>}
"""

from collections.abc import Iterable
from typing import Any, NamedTuple

from .signals import ResolverType, SignalRegistry, registry as default_registry


class EvaluationResult(NamedTuple):
    """Outcome of evaluating a rule set against a signal dict.

    Attributes:
        matched: The first rule that fully matched, or ``None``.
        unresolved: Rules whose outcome could not be decided because at least
            one required signal was absent from ``resolved_signals``.
            Populated only when ``matched`` is ``None``.
    """

    matched: Any  # RoutingRule instance or None
    unresolved: list[Any]


def _rule_priority_key(rule):
    """Sort key: lower priority first, then id for a stable tiebreaker."""
    return (getattr(rule, "priority", 0), getattr(rule, "pk", 0) or 0)


def _condition_signal(rule) -> str | None:
    """Extract the signal name from a rule's condition dict, or None."""
    condition = getattr(rule, "condition", None) or {}
    if not isinstance(condition, dict):
        return None
    return condition.get("signal")


def _condition_expected(rule) -> Any:
    condition = getattr(rule, "condition", None) or {}
    if not isinstance(condition, dict):
        return None
    return condition.get("equals")


def _rule_matches(rule, resolved_signals: dict[str, Any]) -> bool | None:
    """Match a single rule against the resolved signals.

    Returns:
        True  — rule matches definitively.
        False — rule does not match definitively.
        None  — cannot decide (required signal absent).
    """
    signal_name = _condition_signal(rule)
    if not signal_name:
        # A rule with no signal condition can never match under this shape.
        # Later composite conditions will need different handling.
        return False
    if signal_name not in resolved_signals:
        return None
    return resolved_signals[signal_name] == _condition_expected(rule)


def evaluate_rules(rules: Iterable, resolved_signals: dict[str, Any]) -> EvaluationResult:
    """Evaluate ``rules`` in priority order against ``resolved_signals``.

    Args:
        rules: Iterable of rule objects (``RoutingRule`` instances or anything
            with ``priority``, ``pk``, ``condition``). Sorted by priority
            internally; callers do not need to pre-sort.
        resolved_signals: Mapping of ``{signal_name: value}``. Signals absent
            from the mapping are treated as "unknown" and mark rules that
            reference them as unresolved.

    Returns:
        ``EvaluationResult(matched, unresolved)``. If ``matched`` is set,
        ``unresolved`` is empty.
    """
    unresolved: list = []
    for rule in sorted(rules, key=_rule_priority_key):
        outcome = _rule_matches(rule, resolved_signals)
        if outcome is True:
            return EvaluationResult(matched=rule, unresolved=[])
        if outcome is None:
            unresolved.append(rule)
    return EvaluationResult(matched=None, unresolved=unresolved)


def rule_needs_client_side(rule, registry: SignalRegistry = default_registry) -> bool:
    """True if the rule references a signal whose resolver type is
    ``CLIENT_SIDE_STATE`` — i.e., it can only be decided in the browser
    via UITour."""
    signal_name = _condition_signal(rule)
    if not signal_name:
        return False
    signal = registry.get(signal_name)
    if signal is None:
        # Unknown signal — treat as not-client-side. The rule can never match
        # anyway; ``clean()`` on RoutingRule should have caught this earlier.
        return False
    return signal.resolver_type == ResolverType.CLIENT_SIDE_STATE
