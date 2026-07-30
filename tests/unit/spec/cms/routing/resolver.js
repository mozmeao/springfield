/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    initResolver,
    appendLoopBreaker,
    onResolveOutcome
} from '../../../../../media/js/cms/routing/resolver.es6.js';

function makeRoot(rules, manifest, canonical, param) {
    const el = document.createElement('main');
    el.setAttribute('data-routing-rules', JSON.stringify(rules));
    el.setAttribute('data-routing-manifest', JSON.stringify(manifest));
    el.setAttribute('data-canonical-url', canonical);
    el.setAttribute('data-loop-breaker-param', param);
    return el;
}

const RULES = [
    {
        target: '/target/',
        conditions: [
            {
                signal: 'utm_source',
                operator: 'is',
                expected: 'x',
                valueType: 'string'
            }
        ]
    }
];
const MANIFEST = { utm_source: { source: 'url' } };

describe('cms/routing/resolver.es6.js', function () {
    describe('appendLoopBreaker', function () {
        it('appends the marker, choosing ? or & correctly', function () {
            expect(appendLoopBreaker('/c/', 'routed')).toEqual('/c/?routed=1');
            expect(appendLoopBreaker('/c/?a=b', 'routed')).toEqual(
                '/c/?a=b&routed=1'
            );
        });
    });

    describe('onResolveOutcome', function () {
        it('is a no-op telemetry seam', function () {
            expect(onResolveOutcome({ status: 'matched' })).toBeUndefined();
        });
    });

    describe('initResolver', function () {
        it('returns null when there is no resolver element', function () {
            expect(initResolver({ root: null })).toBeNull();
        });

        it('navigates to the matched rule target', async function () {
            let navigated;
            const root = makeRoot(RULES, MANIFEST, '/canon/', 'routed');
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                providerOptions: { search: '?utm_source=x' },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            expect(navigated).toEqual('/target/');
        });

        it('navigates to canonical with the loop-breaker on no match', async function () {
            let navigated;
            const root = makeRoot(RULES, MANIFEST, '/canon/', 'routed');
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                providerOptions: { search: '?utm_source=nope' },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            expect(navigated).toEqual('/canon/?routed=1');
        });

        it('applies fake signals from the preview data blob (C9)', async function () {
            let navigated;
            const rules = [
                {
                    target: '/faked/',
                    conditions: [
                        {
                            signal: 'platform',
                            operator: 'is',
                            expected: 'windows',
                            valueType: 'enum'
                        }
                    ]
                }
            ];
            const root = makeRoot(
                rules,
                { platform: { source: 'user_agent' } },
                '/canon/',
                'routed'
            );
            root.setAttribute(
                'data-routing-fake-signals',
                JSON.stringify({ platform: 'windows' })
            );
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                // Live client would report linux; the fake blob makes it windows.
                providerOptions: {
                    client: { platform: 'linux', isFirefox: true }
                },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            expect(navigated).toEqual('/faked/');
        });
    });
});
