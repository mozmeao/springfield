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

Rule shape:

    Rule has 1+ conditions (via ParentalKey) — evaluated with AND semantics.
    Each condition has the shape ``{"signal": "<name>", "op": "is"|"is_not",
    "values": [...]}``.
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
    """Sort key: lower ``sort_order`` first (drag-to-reorder position),
    then id for a stable tiebreaker.

    Wagtail's ``Orderable.sort_order`` is a nullable IntegerField — a fresh
    rule that hasn't been re-ordered yet has ``sort_order=None``. Treat
    ``None`` as 0 so those rules sort ahead of anything explicitly ordered
    below them.
    """
    sort_order = getattr(rule, "sort_order", None)
    return (sort_order if sort_order is not None else 0, getattr(rule, "pk", 0) or 0)


def _rule_conditions(rule) -> list[dict]:
    """Return the rule's conditions as a list of engine-shaped dicts.

    Delegates to ``rule.conditions_as_dicts()`` when the rule is a Django
    model with an inline conditions relation. As a fallback (used by the
    client-side path and tests), accepts a plain ``.conditions`` attribute
    that is already a list of dicts.
    """
    accessor = getattr(rule, "conditions_as_dicts", None)
    if callable(accessor):
        return accessor()
    conditions = getattr(rule, "conditions", None)
    if isinstance(conditions, list):
        return conditions
    return []


def _condition_matches(condition: dict, resolved_signals: dict[str, Any]) -> bool | None:
    """Match a single condition against the resolved signals.

    Returns:
        True  — condition matches definitively.
        False — condition does not match definitively.
        None  — cannot decide (required signal absent).
    """
    if not isinstance(condition, dict):
        return False
    signal_name = condition.get("signal")
    if not signal_name:
        # A condition with no signal can never match under this shape.
        return False
    if signal_name not in resolved_signals:
        return None

    resolved_value = resolved_signals[signal_name]
    values = condition.get("values")
    if not isinstance(values, list) or not values:
        # No expected values means the condition can't ever match — a common
        # "not fully filled in" state that should never publish, but is
        # safe to treat as no-match if it slips through.
        return False

    is_in_list = resolved_value in values
    operator = condition.get("op") or "is"
    if operator == "is":
        return is_in_list
    if operator == "is_not":
        return not is_in_list
    # Unknown operator (shouldn't happen with clean() validation).
    return False


def _rule_matches(rule, resolved_signals: dict[str, Any]) -> bool | None:
    """Match a single rule against the resolved signals.

    A rule contains one or more conditions joined by AND. It matches iff every
    condition matches. Precedence when combining tri-state per-condition
    outcomes:

    * If any condition is definitively **False** → rule is **False**
      (short-circuits regardless of unresolved others — one failing AND-clause
      is enough to reject).
    * Else if any condition is **unresolved** (``None``) → rule is
      **unresolved**.
    * Else (all conditions True) → rule is **True**.
    """
    conditions = _rule_conditions(rule)
    if not conditions:
        # No conditions = rule can't match. Same treatment as a condition
        # with no signal — safe default is "don't route."
        return False

    any_unresolved = False
    for condition in conditions:
        outcome = _condition_matches(condition, resolved_signals)
        if outcome is False:
            return False
        if outcome is None:
            any_unresolved = True

    if any_unresolved:
        return None
    return True


def evaluate_rules(rules: Iterable, resolved_signals: dict[str, Any]) -> EvaluationResult:
    """Evaluate ``rules`` in priority order against ``resolved_signals``.

    Args:
        rules: Iterable of rule objects (``RoutingRule`` instances or anything
            with ``sort_order``, ``pk``, ``conditions``). Sorted by
            ``sort_order`` internally; callers do not need to pre-sort.
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
    """True if ANY of the rule's conditions references a signal whose resolver
    type is ``CLIENT_SIDE_STATE`` — i.e., the rule can only be fully decided
    in the browser via UITour.

    A rule may mix server-side and client-side signals; if any single
    condition needs the client, the whole rule needs the resolver page.
    """
    for condition in _rule_conditions(rule):
        if not isinstance(condition, dict):
            continue
        signal_name = condition.get("signal")
        if not signal_name:
            continue
        signal = registry.get(signal_name)
        if signal is None:
            continue
        if signal.resolver_type == ResolverType.CLIENT_SIDE_STATE:
            return True
    return False
