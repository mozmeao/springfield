/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — client-side tri-state rule evaluator.
 *
 * Pure, dependency-free logic: it knows nothing about Firefox, Mozilla.Client, or
 * UITour. Signal values arrive through an injected `provider` (the readers),
 * which is the extractability seam.
 *
 * Provider contract:
 *   read(signalName)        -> Promise resolving to the signal's value; a rejection
 *                              or a timeout is treated as the signal being unavailable.
 *   getBudgetMs(signalName) -> optional per-signal read budget in ms (defaults to
 *                              PER_SIGNAL_TIMEOUT_MS; UITour signals use the longer
 *                              PER_UITOUR_KEY_TIMEOUT_MS).
 */

// The tri-state a condition or rule resolves to.
export const MATCHED = 'matched';
export const NOT_MATCHED = 'not_matched';
export const PENDING = 'pending';

// The state of a single signal read, as seen by the evaluator.
export const SIGNAL_PENDING = 'pending';
export const SIGNAL_AVAILABLE = 'available';
export const SIGNAL_UNAVAILABLE = 'unavailable';

// Timeout envelope. The evaluator owns the global cap; per-signal budgets
// are supplied by the provider (UITour reads get the longer per-key budget).
export const PER_SIGNAL_TIMEOUT_MS = 500;
export const PER_UITOUR_KEY_TIMEOUT_MS = 800;
export const GLOBAL_TIMEOUT_MS = 1500;

// Operator semantics, mirroring the Python registry operators. `compare` is the
// positive comparison kind; `negated` flips the positive result.
export const OPERATORS = {
    is: { compare: 'eq', negated: false },
    is_not: { compare: 'eq', negated: true },
    in: { compare: 'in', negated: false },
    not_in: { compare: 'in', negated: true },
    equals: { compare: 'eq', negated: false },
    not_equals: { compare: 'eq', negated: true },
    lt: { compare: 'lt', negated: false },
    not_lt: { compare: 'lt', negated: true },
    lte: { compare: 'lte', negated: false },
    not_lte: { compare: 'lte', negated: true },
    gt: { compare: 'gt', negated: false },
    not_gt: { compare: 'gt', negated: true },
    gte: { compare: 'gte', negated: false },
    not_gte: { compare: 'gte', negated: true }
};

function splitList(expected) {
    // Set-membership operators carry a comma-separated list (matches the Python
    // RoutingCondition.expected_values() convention).
    if (expected === null || expected === undefined) {
        return [];
    }
    return String(expected)
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean);
}

function toBoolean(value) {
    if (typeof value === 'boolean') {
        return value;
    }
    const normalized = String(value).trim().toLowerCase();
    return normalized === 'true' || normalized === '1';
}

function toNumber(value) {
    return Number(String(value).trim());
}

export function normalizeVersion(value) {
    // Accept bare (129), prefixed (rv:129) and fully-qualified (129.0.1) forms by
    // stripping any leading non-digits, then comparing dot-separated numbers.
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .trim()
        .replace(/^[^\d]*/, '');
}

/**
 * Version-aware comparison. Returns -1, 0 or 1.
 */
export function compareVersions(a, b) {
    const partsA = normalizeVersion(a).split('.');
    const partsB = normalizeVersion(b).split('.');
    const length = Math.max(partsA.length, partsB.length);
    for (let i = 0; i < length; i++) {
        const numA = parseInt(partsA[i], 10) || 0;
        const numB = parseInt(partsB[i], 10) || 0;
        if (numA < numB) {
            return -1;
        }
        if (numA > numB) {
            return 1;
        }
    }
    return 0;
}

function valuesEqual(valueType, value, expected) {
    if (valueType === 'version') {
        return compareVersions(value, expected) === 0;
    }
    if (valueType === 'integer') {
        return toNumber(value) === toNumber(expected);
    }
    if (valueType === 'boolean') {
        return toBoolean(value) === toBoolean(expected);
    }
    return String(value) === String(expected);
}

function compareOrdered(valueType, value, expected) {
    if (valueType === 'version') {
        return compareVersions(value, expected);
    }
    const diff = toNumber(value) - toNumber(expected);
    if (diff < 0) {
        return -1;
    }
    if (diff > 0) {
        return 1;
    }
    return 0;
}

function comparePositive(kind, valueType, value, expected) {
    switch (kind) {
        case 'eq':
            return valuesEqual(valueType, value, expected);
        case 'in':
            return splitList(expected).some((member) =>
                valuesEqual(valueType, value, member)
            );
        case 'lt':
            return compareOrdered(valueType, value, expected) < 0;
        case 'lte':
            return compareOrdered(valueType, value, expected) <= 0;
        case 'gt':
            return compareOrdered(valueType, value, expected) > 0;
        case 'gte':
            return compareOrdered(valueType, value, expected) >= 0;
        default:
            return false;
    }
}

/**
 * Resolve a single condition against a signal's current state.
 *
 * A pending signal leaves the condition PENDING (negation never touches pending). An
 * unavailable/timed-out signal makes the condition NOT_MATCHED with no negation flip —
 * a negated *unknown* must never become a match. Only a resolved (available) value is
 * operator-evaluated and then negation-flipped.
 *
 * @param state {status, value?} — a signal state, or undefined (treated as pending).
 */
export function evaluateCondition(condition, state) {
    if (!state || state.status === SIGNAL_PENDING) {
        return PENDING;
    }
    if (state.status === SIGNAL_UNAVAILABLE) {
        return NOT_MATCHED;
    }
    const operator = OPERATORS[condition.operator];
    if (!operator) {
        // Unknown operator: fail safe — never match.
        return NOT_MATCHED;
    }
    const positive = comparePositive(
        operator.compare,
        condition.valueType,
        state.value,
        condition.expected
    );
    const matched = operator.negated ? !positive : positive;
    return matched ? MATCHED : NOT_MATCHED;
}

/**
 * Resolve a rule (an ordered conjunction of conditions) against signal states.
 *
 * A `matchAll` rule matches the whole triggered audience immediately.
 * Otherwise: NOT_MATCHED as soon as any one condition is not-matched (short-circuit,
 * even while siblings are pending); MATCHED only when all conditions match; PENDING
 * otherwise. An empty, non-matchAll rule is NOT_MATCHED (defensive — the serializer
 * already drops it), never the old match-everyone footgun.
 */
export function evaluateRule(rule, signalStates) {
    if (rule.matchAll) {
        return MATCHED;
    }
    let anyPending = false;
    const conditions = rule.conditions || [];
    if (conditions.length === 0) {
        return NOT_MATCHED;
    }
    for (let i = 0; i < conditions.length; i++) {
        const condition = conditions[i];
        const result = evaluateCondition(
            condition,
            signalStates.get(condition.signal)
        );
        if (result === NOT_MATCHED) {
            return NOT_MATCHED;
        }
        if (result === PENDING) {
            anyPending = true;
        }
    }
    return anyPending ? PENDING : MATCHED;
}

/**
 * Priority-strict decision across all rules.
 *
 * Walking rules in priority order, the first MATCHED rule wins — but a PENDING
 * higher-priority rule blocks every lower-priority rule (returns pending), so a slow
 * signal can never let a lower-priority rule jump the queue.
 */
export function decideOutcome(rules, signalStates) {
    for (let i = 0; i < rules.length; i++) {
        const rule = rules[i];
        const result = evaluateRule(rule, signalStates);
        if (result === MATCHED) {
            return { status: MATCHED, rule: rule, target: rule.target };
        }
        if (result === PENDING) {
            return { status: PENDING };
        }
        // NOT_MATCHED: this rule is ruled out; consider the next one.
    }
    return { status: NOT_MATCHED };
}

function budgetFor(provider, signalName) {
    if (provider && typeof provider.getBudgetMs === 'function') {
        const budget = provider.getBudgetMs(signalName);
        if (typeof budget === 'number' && budget > 0) {
            return budget;
        }
    }
    return PER_SIGNAL_TIMEOUT_MS;
}

function collectSignalNames(rules) {
    const names = [];
    const seen = {};
    rules.forEach((rule) => {
        (rule.conditions || []).forEach((condition) => {
            if (!seen[condition.signal]) {
                seen[condition.signal] = true;
                names.push(condition.signal);
            }
        });
    });
    return names;
}

/**
 * Evaluate rules against live signals, under the timeout envelope.
 *
 * Resolves as soon as a decision is reachable, or when the global cap forces closure
 * (unresolved signals become unavailable ⇒ not-matched). Never rejects, never hangs.
 *
 * @returns Promise resolving to one of:
 *   { status: 'matched', target, rule, timedOut }
 *   { status: 'not_matched', timedOut }
 */
export function evaluateRules(rules, provider, options) {
    const opts = options || {};
    const globalTimeoutMs =
        opts.globalTimeoutMs === null || opts.globalTimeoutMs === undefined
            ? GLOBAL_TIMEOUT_MS
            : opts.globalTimeoutMs;

    return new Promise((resolve) => {
        const states = new Map();
        const timers = [];
        let settled = false;

        const signalNames = collectSignalNames(rules);
        signalNames.forEach((name) =>
            states.set(name, { status: SIGNAL_PENDING })
        );

        function finish(outcome) {
            if (settled) {
                return;
            }
            settled = true;
            timers.forEach((timer) => window.clearTimeout(timer));
            resolve(outcome);
        }

        function markUnavailable(name) {
            const state = states.get(name);
            if (state && state.status === SIGNAL_PENDING) {
                states.set(name, { status: SIGNAL_UNAVAILABLE });
            }
        }

        function reevaluate(timedOut) {
            if (settled) {
                return;
            }
            const decision = decideOutcome(rules, states);
            if (decision.status === PENDING && !timedOut) {
                return; // still resolvable — keep waiting within the budget
            }
            if (decision.status === MATCHED) {
                finish({
                    status: MATCHED,
                    target: decision.target,
                    rule: decision.rule,
                    timedOut: !!timedOut
                });
            } else {
                // Genuine no-match, or the budget forced pending to close out.
                finish({ status: NOT_MATCHED, timedOut: !!timedOut });
            }
        }

        // Global hard cap: force any still-pending signal to unavailable and close.
        timers.push(
            window.setTimeout(function () {
                signalNames.forEach(markUnavailable);
                reevaluate(true);
            }, globalTimeoutMs)
        );

        // Kick off each signal read under its own per-signal budget.
        signalNames.forEach((name) => {
            const perTimer = window.setTimeout(
                function () {
                    markUnavailable(name);
                    reevaluate(false);
                },
                budgetFor(provider, name)
            );
            timers.push(perTimer);

            Promise.resolve()
                .then(() => provider.read(name))
                .then(
                    (value) => {
                        window.clearTimeout(perTimer);
                        const state = states.get(name);
                        if (state && state.status === SIGNAL_PENDING) {
                            states.set(name, {
                                status: SIGNAL_AVAILABLE,
                                value: value
                            });
                        }
                        reevaluate(false);
                    },
                    () => {
                        window.clearTimeout(perTimer);
                        markUnavailable(name);
                        reevaluate(false);
                    }
                );
        });

        // Handle the degenerate cases (no rules / no signals) synchronously.
        reevaluate(false);
    });
}
