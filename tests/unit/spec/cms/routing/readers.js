/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    SOURCE_CDN_GEO,
    SOURCE_UITOUR,
    aiControlsPosture,
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
    describe('aiControlsPosture', function () {
        // Firefox reports a state per AI feature with no overall summary. These are the
        // shapes getConfiguration('aiControls') actually returns, per UITour.sys.mjs.
        const untouched = {
            default: 'available',
            translations: 'default',
            pdfjsAltText: 'default',
            smartTabGroups: 'default',
            linkPreviewKeyPoints: 'default',
            sidebarChatbot: 'default',
            smartWindow: 'default'
        };

        it('reads an untouched profile as neutral', function () {
            expect(aiControlsPosture(untouched)).toEqual('neutral');
        });

        it('treats explicit "available" as no choice, like "default"', function () {
            // Firefox's own wording: available = "you'll see it and can use it";
            // enabled = "you've opted in". Only the latter is a choice.
            const allAvailable = Object.assign({}, untouched, {
                translations: 'available',
                sidebarChatbot: 'available'
            });
            expect(aiControlsPosture(allAvailable)).toEqual('neutral');
        });

        it('reads the global block as blocked_all, whatever the features say', function () {
            expect(
                aiControlsPosture(
                    Object.assign({}, untouched, {
                        default: 'blocked',
                        sidebarChatbot: 'enabled'
                    })
                )
            ).toEqual('blocked_all');
        });

        it('reads every feature blocked as blocked_all even without the master', function () {
            const all = { default: 'available' };
            Object.keys(untouched)
                .filter((k) => k !== 'default')
                .forEach((k) => {
                    all[k] = 'blocked';
                });
            expect(aiControlsPosture(all)).toEqual('blocked_all');
        });

        it('distinguishes opting in, blocking, and doing both', function () {
            expect(
                aiControlsPosture(
                    Object.assign({}, untouched, { sidebarChatbot: 'enabled' })
                )
            ).toEqual('enabled_some');
            expect(
                aiControlsPosture(
                    Object.assign({}, untouched, { translations: 'blocked' })
                )
            ).toEqual('blocked_some');
            expect(
                aiControlsPosture(
                    Object.assign({}, untouched, {
                        sidebarChatbot: 'enabled',
                        translations: 'blocked'
                    })
                )
            ).toEqual('mixed');
        });

        it('folds in AI features Firefox has not shipped yet', function () {
            // Keys are iterated, never named, so a new feature needs no change here.
            expect(
                aiControlsPosture({
                    default: 'available',
                    somethingBrandNew: 'enabled'
                })
            ).toEqual('enabled_some');
        });

        it('returns undefined for a payload it cannot read', function () {
            expect(aiControlsPosture(undefined)).toBeUndefined();
            expect(aiControlsPosture(null)).toBeUndefined();
            expect(aiControlsPosture('nope')).toBeUndefined();
        });
    });

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

        it('reads browser_language as the top preference, region dropped', async function () {
            const reader = createUserAgentReader({
                client: firefox,
                navigator: { languages: ['fr-CA', 'en-US'], language: 'fr-CA' }
            });
            expect(await reader.read({ name: 'browser_language' })).toEqual(
                'fr'
            );
        });

        it('reads browser_language without Mozilla.Client present', async function () {
            // navigator.languages is a plain browser API, so this must work off Firefox
            // where the Mozilla.Client global is absent.
            const reader = createUserAgentReader({
                client: null,
                navigator: { languages: ['de'], language: 'de' }
            });
            expect(await reader.read({ name: 'browser_language' })).toEqual(
                'de'
            );
        });

        it('falls back to navigator.language when languages is empty', async function () {
            const reader = createUserAgentReader({
                client: firefox,
                navigator: { languages: [], language: 'es-MX' }
            });
            expect(await reader.read({ name: 'browser_language' })).toEqual(
                'es'
            );
        });

        it('is unavailable for browser_language when the browser reports none', async function () {
            const reader = createUserAgentReader({
                client: firefox,
                navigator: { languages: [], language: '' }
            });
            expect(
                await settle(reader.read({ name: 'browser_language' }))
            ).toBe(REJECTED);
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

        it('reads oldversion, normalizing the rv: prefix', async function () {
            const reader = createUrlReader({ search: '?oldversion=rv:129' });
            expect(await reader.read({ name: 'oldversion' })).toEqual('129');
        });

        it('reads oldversion verbatim when already normalized', async function () {
            const reader = createUrlReader({ search: '?oldversion=129.0.1' });
            expect(await reader.read({ name: 'oldversion' })).toEqual(
                '129.0.1'
            );
        });

        it('is unavailable when oldversion is absent', async function () {
            const reader = createUrlReader({ search: '?utm_source=google' });
            expect(await settle(reader.read({ name: 'oldversion' }))).toBe(
                REJECTED
            );
        });

        it('resolves oldversion=unknown with no version rather than rejecting', async function () {
            // Firefox sends this when it has no prior version to report. The visitor did
            // supply a value, so the read succeeds; deciding that an unparseable value
            // proves nothing is the evaluator's job, and it fails closed on this.
            const reader = createUrlReader({ search: '?oldversion=unknown' });
            expect(await reader.read({ name: 'oldversion' })).toBeNull();
        });

        it('reads locale from the <html lang> attribute', async function () {
            const reader = createUrlReader({ search: '', lang: 'de' });
            expect(await reader.read({ name: 'locale' })).toEqual('de');
        });

        it('prefers an explicit ?locale= over <html lang>', async function () {
            const reader = createUrlReader({
                search: '?locale=pt-BR',
                lang: 'de'
            });
            expect(await reader.read({ name: 'locale' })).toEqual('pt-BR');
        });

        it('is unavailable when neither ?locale= nor <html lang> is set', async function () {
            const reader = createUrlReader({ search: '', lang: null });
            expect(await settle(reader.read({ name: 'locale' }))).toBe(
                REJECTED
            );
        });

        it('reads language as the locale with the region dropped', async function () {
            // One condition covers every regional variant: en matches en-US/en-GB/en-CA.
            const reader = createUrlReader({ search: '', lang: 'en-CA' });
            expect(await reader.read({ name: 'language' })).toEqual('en');
            expect(await reader.read({ name: 'locale' })).toEqual('en-CA');
        });

        it('reads language from a region-free locale unchanged', async function () {
            const reader = createUrlReader({ search: '', lang: 'de' });
            expect(await reader.read({ name: 'language' })).toEqual('de');
        });

        it('derives language from an explicit ?locale= override too', async function () {
            const reader = createUrlReader({
                search: '?locale=pt-BR',
                lang: 'de'
            });
            expect(await reader.read({ name: 'language' })).toEqual('pt');
        });

        it('is unavailable for language when no locale can be determined', async function () {
            const reader = createUrlReader({ search: '', lang: null });
            expect(await settle(reader.read({ name: 'language' }))).toBe(
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

    describe('createProvider — fake signals (preview_signal)', function () {
        it('resolves faked signals immediately and reads the rest live', async function () {
            const manifest = {
                platform: { source: 'user_agent' },
                utm_source: { source: 'url' }
            };
            const p = createProvider(manifest, {
                client: { platform: 'linux', isFirefox: true },
                search: '?utm_source=bing',
                fakes: { platform: 'windows' }
            });
            // Faked signal wins over the live reader value.
            expect(await p.read('platform')).toEqual('windows');
            // Un-faked signal still reads live.
            expect(await p.read('utm_source')).toEqual('bing');
        });
    });
});
