/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    SOURCE_CDN_GEO,
    SOURCE_UITOUR,
    createGeoReader,
    createUserAgentReader,
    createUITourReader,
    createUrlReader,
    createProvider
} from '../../../../../media/js/cms/routing/readers.es6.js';

// Resolve a promise to its value, or the sentinel REJECTED — lets a single helper
// assert both outcomes without depending on a particular jasmine version's
// expectAsync.
const REJECTED = { rejected: true };
function settle(promise) {
    return promise.then(
        (value) => value,
        () => REJECTED
    );
}

describe('cms/routing/readers.es6.js', function () {
    describe('geo reader (CDN geo header)', function () {
        it('reads the server-rendered data-country-code attribute', async function () {
            const reader = createGeoReader({
                root: { dataset: { countryCode: 'US' } }
            });
            expect(await reader.read({ name: 'country' })).toEqual('US');
        });

        it('is unavailable when the attribute is absent', async function () {
            const reader = createGeoReader({ root: { dataset: {} } });
            expect(await settle(reader.read({ name: 'country' }))).toBe(
                REJECTED
            );
        });
    });

    describe('user-agent reader (Mozilla.Client)', function () {
        const firefox = {
            isFirefox: true,
            platform: 'windows',
            _getFirefoxVersion: () => '129.0'
        };

        it('maps Mozilla.Client output to signal values', async function () {
            const reader = createUserAgentReader({ client: firefox });
            expect(await reader.read({ name: 'platform' })).toEqual('windows');
            expect(await reader.read({ name: 'firefox_version' })).toEqual(
                '129.0'
            );
            expect(await reader.read({ name: 'is_firefox' })).toBe(true);
        });

        it('yields false for is_firefox when stubbed non-Firefox', async function () {
            const reader = createUserAgentReader({
                client: {
                    isFirefox: false,
                    platform: 'windows',
                    _getFirefoxVersion: () => ''
                }
            });
            expect(await reader.read({ name: 'is_firefox' })).toBe(false);
        });

        it('still reads platform off Firefox, but firefox_version is unavailable', async function () {
            const reader = createUserAgentReader({
                client: {
                    isFirefox: false,
                    platform: 'osx',
                    _getFirefoxVersion: () => ''
                }
            });
            expect(await reader.read({ name: 'platform' })).toEqual('osx');
            expect(await settle(reader.read({ name: 'firefox_version' }))).toBe(
                REJECTED
            );
        });
    });

    describe('UITour reader', function () {
        it('resolves a value once the ping and getConfiguration answer', async function () {
            const uiTour = {
                ping: (cb) => cb(),
                getConfiguration: (key, cb) => cb({ defaultBrowser: true })
            };
            const reader = createUITourReader({ uiTour: uiTour, timeout: 100 });
            const value = await reader.read({
                name: 'is_default_browser',
                browserStateKey: 'appinfo'
            });
            expect(value).toBe(true);
        });

        it('stays pending then times out to unavailable when the ping never answers', async function () {
            const stuck = {
                ping: function () {
                    /* never calls back */
                },
                getConfiguration: function () {
                    /* never called */
                }
            };
            const reader = createUITourReader({ uiTour: stuck, timeout: 30 });
            const outcome = await settle(
                reader.read({
                    name: 'is_default_browser',
                    browserStateKey: 'appinfo'
                })
            );
            expect(outcome).toBe(REJECTED);
        });

        it('is unavailable when UITour is absent', async function () {
            const reader = createUITourReader({ uiTour: null, timeout: 30 });
            const outcome = await settle(
                reader.read({
                    name: 'is_default_browser',
                    browserStateKey: 'appinfo'
                })
            );
            expect(outcome).toBe(REJECTED);
        });
    });

    describe('URL reader', function () {
        it('reads query params by signal name', async function () {
            const reader = createUrlReader({
                search: '?utm_source=google&utm_medium=cpc'
            });
            expect(await reader.read({ name: 'utm_source' })).toEqual('google');
            expect(await reader.read({ name: 'utm_medium' })).toEqual('cpc');
        });

        it('is unavailable when the param is absent', async function () {
            const reader = createUrlReader({ search: '?utm_source=google' });
            expect(await settle(reader.read({ name: 'utm_campaign' }))).toBe(
                REJECTED
            );
        });
    });

    describe('createProvider — composes the adapters for the evaluator', function () {
        const manifest = {
            country: { source: 'cdn_geo' },
            platform: { source: 'user_agent' },
            is_default_browser: {
                source: 'uitour',
                browserStateKey: 'appinfo'
            },
            utm_source: { source: 'url' }
        };

        function provider() {
            return createProvider(manifest, {
                root: { dataset: { countryCode: 'DE' } },
                client: {
                    platform: 'linux',
                    isFirefox: true,
                    _getFirefoxVersion: () => '1'
                },
                uiTour: {
                    ping: (cb) => cb(),
                    getConfiguration: (key, cb) => cb({ defaultBrowser: false })
                },
                search: '?utm_source=bing',
                timeout: 100
            });
        }

        it('routes each signal to the right source adapter', async function () {
            const p = provider();
            expect(await p.read('country')).toEqual('DE');
            expect(await p.read('platform')).toEqual('linux');
            expect(await p.read('is_default_browser')).toBe(false);
            expect(await p.read('utm_source')).toEqual('bing');
        });

        it('gives UITour signals the longer per-key budget', function () {
            const p = provider();
            expect(p.getBudgetMs('is_default_browser')).toEqual(800);
            expect(p.getBudgetMs('country')).toEqual(500);
            expect(p.getBudgetMs('utm_source')).toEqual(500);
        });

        it('is unavailable for a signal missing from the manifest', async function () {
            const p = provider();
            expect(await settle(p.read('not_in_manifest'))).toBe(REJECTED);
        });

        it('exposes the source identifiers that mirror the Python registry', function () {
            expect(SOURCE_CDN_GEO).toEqual('cdn_geo');
            expect(SOURCE_UITOUR).toEqual('uitour');
        });
    });
});
