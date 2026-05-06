/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');

/**
 * Intercepts Mozilla.DownloadAttribution.initMarketing before page scripts run
 * so tests can assert whether it was called. Optionally mocks dntEnabled or
 * gpcEnabled on the Mozilla namespace to simulate denial signals.
 * Pass to page.addInitScript() before navigation.
 * @param {Object} options
 * @param {Boolean} options.mockDNT
 * @param {Boolean} options.mockGPC
 */
function interceptInitMarketing({ mockDNT = false, mockGPC = false } = {}) {
    window.__initMarketingCalled = false;
    let _daValue;
    const _mozilla = {};

    if (mockDNT) {
        Object.defineProperty(_mozilla, 'dntEnabled', {
            configurable: true,
            get() {
                return () => true;
            }
        });
    }

    if (mockGPC) {
        Object.defineProperty(_mozilla, 'gpcEnabled', {
            configurable: true,
            get() {
                return () => true;
            }
        });
    }

    Object.defineProperty(window, 'Mozilla', {
        configurable: true,
        enumerable: true,
        get() {
            return _mozilla;
        },
        set(val) {
            if (val && typeof val === 'object') {
                Object.assign(_mozilla, val);
            }
        }
    });

    Object.defineProperty(_mozilla, 'DownloadAttribution', {
        configurable: true,
        enumerable: true,
        get() {
            return _daValue;
        },
        set(val) {
            if (val && typeof val.initMarketing === 'function') {
                const orig = val.initMarketing;
                val.initMarketing = function (...args) {
                    window.__initMarketingCalled = true;
                    return orig.apply(this, args);
                };
            }
            _daValue = val;
        }
    });
}

test.describe('not consent required geo', () => {
    test.describe(
        'default',
        {
            tag: '@firefox'
        },
        () => {
            const url = '/en-US/?geo=us';

            test.beforeEach(async ({ page, browserName }) => {
                await openPage(url, page, browserName);
            });

            test('marketing download attribution cookie created', async ({
                page
            }) => {
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-marketing-raw='
                                )
                        );
                });

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeDefined();
            });
        }
    );

    test.describe(
        'consent denied signal',
        {
            tag: '@firefox'
        },
        () => {
            const url = '/en-US/?geo=us';

            test('DNT enabled - marketing download attribution cookie NOT created', async ({
                page,
                browserName
            }) => {
                await page.addInitScript(interceptInitMarketing, {
                    mockDNT: true
                });
                await openPage(url, page, browserName);
                await page.waitForLoadState('networkidle');

                const initMarketingCalled = await page.evaluate(
                    () => window.__initMarketingCalled
                );
                expect(initMarketingCalled).toBe(false);

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeUndefined();
            });

            test('GPC enabled - marketing download attribution cookie NOT created', async ({
                page,
                browserName
            }) => {
                await page.addInitScript(interceptInitMarketing, {
                    mockGPC: true
                });
                await openPage(url, page, browserName);
                await page.waitForLoadState('networkidle');

                const initMarketingCalled = await page.evaluate(
                    () => window.__initMarketingCalled
                );
                expect(initMarketingCalled).toBe(false);

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeUndefined();
            });

            test('Pref cookie denies analytics - marketing download attribution cookie NOT created', async ({
                page,
                browserName,
                baseURL
            }) => {
                await page.addInitScript(interceptInitMarketing);
                await page.context().addCookies([
                    {
                        name: 'moz-consent-pref',
                        value: JSON.stringify({ analytics: false }),
                        url: baseURL
                    }
                ]);
                await openPage(url, page, browserName);
                await page.waitForLoadState('networkidle');

                const initMarketingCalled = await page.evaluate(
                    () => window.__initMarketingCalled
                );
                expect(initMarketingCalled).toBe(false);

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeUndefined();
            });
        }
    );
});

test.describe('consent required geo', () => {
    test.describe(
        'default',
        {
            tag: '@firefox'
        },
        () => {
            test('marketing download attribution cookie NOT created', async ({
                page,
                browserName
            }) => {
                await page.addInitScript(interceptInitMarketing);
                await openPage('/fr/?geo=fr', page, browserName);
                await page.waitForLoadState('networkidle');

                const initMarketingCalled = await page.evaluate(
                    () => window.__initMarketingCalled
                );
                expect(initMarketingCalled).toBe(false);

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeUndefined();
            });
        }
    );

    // NOTE: this test uses mozcb=y param to force a check of analytics consent
    test.describe(
        'pref cookie grants consent',
        {
            tag: '@firefox'
        },
        () => {
            test('marketing download attribution cookie created', async ({
                page,
                browserName,
                baseURL
            }) => {
                await page.context().addCookies([
                    {
                        name: 'moz-consent-pref',
                        value: JSON.stringify({ analytics: true }),
                        url: baseURL
                    }
                ]);
                await openPage('/fr/?geo=fr&mozcb=y', page, browserName);

                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-marketing-raw='
                                )
                        );
                });

                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeDefined();
            });
        }
    );
});
