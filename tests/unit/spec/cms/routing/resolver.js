/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    initResolver,
    appendLoopBreaker,
    preserveQueryString,
    RESERVED_ROUTING_PARAMS,
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

    describe('preserveQueryString', function () {
        const reserved = RESERVED_ROUTING_PARAMS;

        it('returns the url unchanged when there is nothing to preserve', function () {
            expect(preserveQueryString('/target/', '', reserved)).toEqual(
                '/target/'
            );
            expect(
                preserveQueryString('/target/', undefined, reserved)
            ).toEqual('/target/');
        });

        it('merges inbound params onto a clean url', function () {
            expect(
                preserveQueryString(
                    '/target/',
                    '?utm_source=update&oldversion=151',
                    reserved
                )
            ).toEqual('/target/?utm_source=update&oldversion=151');
        });

        it('merges onto a url that already has a query string', function () {
            expect(
                preserveQueryString('/target/?a=b', '?utm_source=x', reserved)
            ).toEqual('/target/?a=b&utm_source=x');
        });

        it('does not overwrite or duplicate a key the destination already carries', function () {
            expect(
                preserveQueryString(
                    '/target/?utm_source=keep',
                    '?utm_source=drop&utm_medium=email',
                    reserved
                )
            ).toEqual('/target/?utm_source=keep&utm_medium=email');
        });

        it('strips reserved routing params', function () {
            expect(
                preserveQueryString(
                    '/target/',
                    '?routing=1&routed=1&preview_rule=2&preview_signal=x&utm_source=keep',
                    reserved
                )
            ).toEqual('/target/?utm_source=keep');
        });

        it('preserves a fragment on the destination', function () {
            expect(
                preserveQueryString(
                    '/target/#section',
                    '?utm_source=x',
                    reserved
                )
            ).toEqual('/target/?utm_source=x#section');
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

        it('navigates to the matched rule target, preserving the inbound query string', async function () {
            let navigated;
            const root = makeRoot(RULES, MANIFEST, '/canon/', 'routed');
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                providerOptions: {
                    search: '?utm_source=x&utm_campaign=spring'
                },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            // Attribution (the matched signal + campaign) rides through to the target.
            expect(navigated).toEqual(
                '/target/?utm_source=x&utm_campaign=spring'
            );
        });

        it('navigates to canonical with the loop-breaker on no match, preserving attribution', async function () {
            let navigated;
            const root = makeRoot(RULES, MANIFEST, '/canon/', 'routed');
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                providerOptions: {
                    search: '?utm_source=nope&utm_campaign=spring'
                },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            expect(navigated).toEqual(
                '/canon/?utm_source=nope&utm_campaign=spring&routed=1'
            );
        });

        it('does not carry reserved routing params onto the destination, nor duplicate the loop-breaker', async function () {
            let navigated;
            const root = makeRoot(RULES, MANIFEST, '/canon/', 'routed');
            await initResolver({
                root: root,
                navigate: (url) => {
                    navigated = url;
                },
                // A stale loop-breaker + preview params must be stripped, utm kept.
                providerOptions: {
                    search: '?utm_source=nope&routing=1&routed=1&preview_rule=3'
                },
                evaluatorOptions: { globalTimeoutMs: 500 }
            });
            expect(navigated).toEqual('/canon/?utm_source=nope&routed=1');
        });

        it('applies fake signals from the preview data blob', async function () {
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
