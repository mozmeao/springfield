/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    MATCHED,
    NOT_MATCHED,
    PENDING,
    SIGNAL_AVAILABLE,
    SIGNAL_PENDING,
    SIGNAL_UNAVAILABLE,
    OPERATORS,
    compareVersions,
    evaluateCondition,
    evaluateRule,
    decideOutcome,
    evaluateRules
} from '../../../../../media/js/cms/routing/evaluator.es6.js';

// --- helpers ---------------------------------------------------------------

function cond(signal, operator, expected, valueType) {
    return {
        signal: signal,
        operator: operator,
        expected: expected,
        valueType: valueType || 'string'
    };
}

function available(value) {
    return { status: SIGNAL_AVAILABLE, value: value };
}

const pending = { status: SIGNAL_PENDING };
const unavailable = { status: SIGNAL_UNAVAILABLE };

function states(map) {
    return new Map(Object.keys(map).map((name) => [name, map[name]]));
}

// A provider whose reads are described by `reads` (name -> () => Promise) and whose
// per-signal budgets come from `budgets` (name -> ms, default 500).
function fakeProvider(reads, budgets) {
    return {
        read: function (name) {
            return reads[name]();
        },
        getBudgetMs: function (name) {
            return (budgets && budgets[name]) || 500;
        }
    };
}

const resolveWith = (value) => () => Promise.resolve(value);
const never = () =>
    new window.Promise(function () {
        /* intentionally never resolves */
    });
const delayed = (value, ms) => () =>
    new window.Promise(function (resolve) {
        window.setTimeout(function () {
            resolve(value);
        }, ms);
    });

describe('cms/routing/evaluator.es6.js', function () {
    describe('compareVersions (spec §4.4)', function () {
        it('normalizes bare, rv-prefixed and fully-qualified versions', function () {
            expect(compareVersions('rv:129', '129')).toEqual(0);
            expect(compareVersions('129', '129.0.0')).toEqual(0);
            expect(compareVersions('129.0.1', '129')).toEqual(1);
        });

        it('compares numerically, not as strings', function () {
            expect(compareVersions('9', '100')).toEqual(-1);
            expect(compareVersions('100', '9')).toEqual(1);
            expect(compareVersions('129.1', '129.0.5')).toEqual(1);
        });
    });

    describe('evaluateCondition (spec §7.3)', function () {
        it('matches / does not match a resolved positive condition', function () {
            expect(
                evaluateCondition(
                    cond('platform', 'is', 'windows', 'enum'),
                    available('windows')
                )
            ).toEqual(MATCHED);
            expect(
                evaluateCondition(
                    cond('platform', 'is', 'windows', 'enum'),
                    available('linux')
                )
            ).toEqual(NOT_MATCHED);
        });

        it('flips matched<->not-matched for a negated resolved condition', function () {
            expect(
                evaluateCondition(
                    cond('platform', 'is_not', 'windows', 'enum'),
                    available('linux')
                )
            ).toEqual(MATCHED);
            expect(
                evaluateCondition(
                    cond('platform', 'is_not', 'windows', 'enum'),
                    available('windows')
                )
            ).toEqual(NOT_MATCHED);
        });

        it('leaves a pending signal PENDING — positive and negated alike', function () {
            expect(
                evaluateCondition(
                    cond('platform', 'is', 'windows', 'enum'),
                    pending
                )
            ).toEqual(PENDING);
            expect(
                evaluateCondition(
                    cond('platform', 'is_not', 'windows', 'enum'),
                    pending
                )
            ).toEqual(PENDING);
            // A missing state is treated as pending too.
            expect(
                evaluateCondition(
                    cond('platform', 'is', 'windows', 'enum'),
                    undefined
                )
            ).toEqual(PENDING);
        });

        it('treats an unavailable signal as NOT_MATCHED and never flips it to a match', function () {
            // The subtle §7.3 point: a negated *unknown* must not become a match.
            expect(
                evaluateCondition(
                    cond('platform', 'is', 'windows', 'enum'),
                    unavailable
                )
            ).toEqual(NOT_MATCHED);
            expect(
                evaluateCondition(
                    cond('platform', 'is_not', 'windows', 'enum'),
                    unavailable
                )
            ).toEqual(NOT_MATCHED);
        });

        it('supports set membership (in / not_in)', function () {
            const c = cond('platform', 'in', 'windows, osx', 'enum');
            expect(evaluateCondition(c, available('osx'))).toEqual(MATCHED);
            expect(evaluateCondition(c, available('linux'))).toEqual(
                NOT_MATCHED
            );
            const n = cond('platform', 'not_in', 'windows, osx', 'enum');
            expect(evaluateCondition(n, available('linux'))).toEqual(MATCHED);
            expect(evaluateCondition(n, available('windows'))).toEqual(
                NOT_MATCHED
            );
        });

        it('supports version comparisons', function () {
            expect(
                evaluateCondition(
                    cond('firefox_version', 'gte', '128', 'version'),
                    available('129.0')
                )
            ).toEqual(MATCHED);
            expect(
                evaluateCondition(
                    cond('firefox_version', 'lt', '128', 'version'),
                    available('129.0')
                )
            ).toEqual(NOT_MATCHED);
            expect(
                evaluateCondition(
                    cond('firefox_version', 'not_gte', '128', 'version'),
                    available('129.0')
                )
            ).toEqual(NOT_MATCHED);
        });

        it('supports integer and boolean comparisons', function () {
            expect(
                evaluateCondition(
                    cond('profile_age', 'gt', '30', 'integer'),
                    available(45)
                )
            ).toEqual(MATCHED);
            expect(
                evaluateCondition(
                    cond('is_firefox', 'is', 'true', 'boolean'),
                    available(true)
                )
            ).toEqual(MATCHED);
            expect(
                evaluateCondition(
                    cond('is_firefox', 'is', 'true', 'boolean'),
                    available(false)
                )
            ).toEqual(NOT_MATCHED);
        });

        it('every operator is present and paired with its negation', function () {
            Object.keys(OPERATORS).forEach(function (key) {
                const op = OPERATORS[key];
                expect(typeof op.compare).toEqual('string');
                expect(typeof op.negated).toEqual('boolean');
            });
        });
    });

    describe('evaluateRule — conjunction (spec §7.3)', function () {
        const rule = {
            target: 'x',
            conditions: [
                cond('platform', 'is', 'windows', 'enum'),
                cond('country', 'is', 'US', 'string')
            ]
        };

        it('is MATCHED only when all conditions match', function () {
            expect(
                evaluateRule(
                    rule,
                    states({
                        platform: available('windows'),
                        country: available('US')
                    })
                )
            ).toEqual(MATCHED);
        });

        it('short-circuits to NOT_MATCHED on one failed condition, even with a pending sibling', function () {
            expect(
                evaluateRule(
                    rule,
                    states({ platform: available('linux'), country: pending })
                )
            ).toEqual(NOT_MATCHED);
        });

        it('is PENDING when some conditions are pending and none have failed', function () {
            expect(
                evaluateRule(
                    rule,
                    states({ platform: available('windows'), country: pending })
                )
            ).toEqual(PENDING);
        });
    });

    describe('decideOutcome — priority-strict (spec §7.2)', function () {
        const high = { target: 'HIGH', conditions: [cond('a', 'is', '1')] };
        const low = { target: 'LOW', conditions: [cond('b', 'is', '1')] };

        it('the first matched rule wins', function () {
            const out = decideOutcome(
                [high, low],
                states({ a: available('1'), b: available('1') })
            );
            expect(out.status).toEqual(MATCHED);
            expect(out.target).toEqual('HIGH');
        });

        it('a pending higher-priority rule blocks a matched lower-priority rule', function () {
            const out = decideOutcome(
                [high, low],
                states({ a: pending, b: available('1') })
            );
            expect(out.status).toEqual(PENDING);
        });

        it('a lower-priority rule wins once every higher rule is definitively not-matched', function () {
            const out = decideOutcome(
                [high, low],
                states({ a: available('0'), b: available('1') })
            );
            expect(out.status).toEqual(MATCHED);
            expect(out.target).toEqual('LOW');
        });

        it('is NOT_MATCHED when no rule matches', function () {
            const out = decideOutcome(
                [high, low],
                states({ a: available('0'), b: available('0') })
            );
            expect(out.status).toEqual(NOT_MATCHED);
        });
    });

    describe('evaluateRules — async under the timeout envelope (spec §7.5)', function () {
        const high = { target: 'HIGH', conditions: [cond('a', 'is', 'yes')] };
        const low = { target: 'LOW', conditions: [cond('b', 'is', 'yes')] };

        it('resolves to the matched rule target', async function () {
            const out = await evaluateRules(
                [high],
                fakeProvider({ a: resolveWith('yes') }),
                { globalTimeoutMs: 1000 }
            );
            expect(out.status).toEqual(MATCHED);
            expect(out.target).toEqual('HIGH');
        });

        it('a slow higher-priority match still wins over a fast lower-priority match', async function () {
            // If a pending high rule failed to block, the fast low rule would win here.
            const provider = fakeProvider(
                { a: delayed('yes', 40), b: resolveWith('yes') },
                { a: 1000, b: 1000 }
            );
            const out = await evaluateRules([high, low], provider, {
                globalTimeoutMs: 1000
            });
            expect(out.status).toEqual(MATCHED);
            expect(out.target).toEqual('HIGH');
        });

        it('a lower-priority rule wins only after the higher rule is decided not-matched', async function () {
            const provider = fakeProvider(
                { a: delayed('no', 30), b: resolveWith('yes') },
                { a: 1000, b: 1000 }
            );
            const out = await evaluateRules([high, low], provider, {
                globalTimeoutMs: 1000
            });
            expect(out.status).toEqual(MATCHED);
            expect(out.target).toEqual('LOW');
        });

        it('forces closure to not-matched when the global cap is hit', async function () {
            const provider = fakeProvider({ a: never }, { a: 5000 });
            const out = await evaluateRules([high], provider, {
                globalTimeoutMs: 60
            });
            expect(out.status).toEqual(NOT_MATCHED);
            expect(out.timedOut).toBe(true);
        });

        it('treats a signal that exceeds its per-signal budget as not-matched', async function () {
            const provider = fakeProvider({ a: never }, { a: 40 });
            const out = await evaluateRules([high], provider, {
                globalTimeoutMs: 1000
            });
            expect(out.status).toEqual(NOT_MATCHED);
            expect(out.timedOut).toBe(false);
        });

        it('a read rejection makes the signal unavailable (not-matched)', async function () {
            const provider = fakeProvider(
                { a: () => Promise.reject(new Error('nope')) },
                { a: 1000 }
            );
            const out = await evaluateRules([high], provider, {
                globalTimeoutMs: 1000
            });
            expect(out.status).toEqual(NOT_MATCHED);
        });

        it('a timed-out signal under a negated condition never becomes a match', async function () {
            // "platform is_not linux" with platform timing out must NOT route (§7.3).
            const negatedRule = {
                target: 'NEG',
                conditions: [cond('platform', 'is_not', 'linux', 'enum')]
            };
            const provider = fakeProvider(
                { platform: never },
                { platform: 40 }
            );
            const out = await evaluateRules([negatedRule], provider, {
                globalTimeoutMs: 1000
            });
            expect(out.status).toEqual(NOT_MATCHED);
        });
    });
});
