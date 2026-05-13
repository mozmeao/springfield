/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');

/**
 * Sets up a route mock for stub_attribution_code XHR requests.
 *
 * Captured query params are written to capturedStubParams
 * (passed by reference via wrapper).
 *
 * The mock responds with a signed attribution payload so downstream cookie
 * writes complete normally.
 * @param {import('@playwright/test').Page} page
 * @param {{ params: Object | null }} capture - Object whose .params property
 *   is set to the captured URLSearchParams entries when the request fires.
 */
async function routeStubAttributionCode(page, capture) {
    await page.route('**/stub_attribution_code/**', async (route) => {
        const reqUrl = new URL(route.request().url());
        capture.params = Object.fromEntries(reqUrl.searchParams);
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                attribution_code: 'mocked-attribution-code',
                attribution_sig: 'mocked-attribution-sig'
            })
        });
    });
}

/**
 * Intercepts Mozilla.DownloadAttribution.initAnalytics before page scripts run
 * so tests can assert whether it was called.
 *
 * Optionally mocks dntEnabled or gpcEnabled on the Mozilla namespace to simulate
 * denial signals.
 *
 * Pass to page.addInitScript() before navigation.
 * @param {Object} options
 * @param {Boolean} options.mockDNT
 * @param {Boolean} options.mockGPC
 */
function interceptInitAnalytics({ mockDNT = false, mockGPC = false } = {}) {
    window.__initAnalyticsCalled = false;
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
            if (val && typeof val.initAnalytics === 'function') {
                const orig = val.initAnalytics;
                val.initAnalytics = function (...args) {
                    window.__initAnalyticsCalled = true;
                    return orig.apply(this, args);
                };
            }
            _daValue = val;
        }
    });
}

/**
 * Intercepts Mozilla.DownloadAttribution.getGtagClientID before page scripts
 * run so it returns a fixed GA4 client ID without triggering real GA4 network
 * calls.
 *
 * Pass to page.addInitScript() before navigation.
 */
function mockGetGtagClientID() {
    let _daValue;
    const _mozilla = {};

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
            if (val && typeof val === 'object') {
                val.getGtagClientID = () => 'mocked-ga4-client-id';
            }
            _daValue = val;
        }
    });
}

/**
 * Sets data-stub-attribution-campaign-force on <html> before page scripts run.
 * Pass to page.addInitScript() before navigation.
 */
function forceEssentialCampaign(campaign = 'smart_window') {
    function setAttr() {
        document.documentElement.setAttribute(
            'data-stub-attribution-campaign-force',
            campaign
        );
    }
    // Init scripts run before HTML is parsed, so document.documentElement
    // may be null. Observe the document for the <html> element if needed.
    if (document.documentElement) {
        setAttr();
    } else {
        new MutationObserver(function (_, obs) {
            if (document.documentElement) {
                obs.disconnect();
                setAttr();
            }
        }).observe(document, { childList: true, subtree: true });
    }
}

const existingAnalyticsParams =
    'utm_source=newsletter&utm_medium=email&utm_campaign=existing';

test.describe('analytics download attribution', () => {
    test.describe(
        'essential data added',
        {
            tag: '@firefox'
        },
        () => {
            test('pre-existing analytics data preserved', async ({
                page,
                browserName
            }) => {
                await page.addInitScript(mockGetGtagClientID);

                const initialCapture = { params: null };
                await routeStubAttributionCode(page, initialCapture);

                await openPage(
                    `/en-US/?geo=us&${existingAnalyticsParams}`,
                    page,
                    browserName
                );

                // Confirm existing cookie values
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                const existingCookies = await page.context().cookies();
                const existingAnalyticsCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(existingAnalyticsCookie).toBeDefined();
                const existingAnalyticsCookieData = JSON.parse(
                    decodeURIComponent(existingAnalyticsCookie.value)
                );
                expect(existingAnalyticsCookieData.utm_source).toBe(
                    'newsletter'
                );
                expect(existingAnalyticsCookieData.utm_medium).toBe('email');
                expect(existingAnalyticsCookieData.client_id_ga4).toBe(
                    'mocked-ga4-client-id'
                );
                expect(existingAnalyticsCookieData.dlsource).toBe('fxdotcom');
                expect(existingAnalyticsCookieData.utm_campaign).toBe(
                    'existing'
                );

                // Navigate to new page with essential campaign
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);
                await page.addInitScript(forceEssentialCampaign);
                await openPage('/en-US/?geo=us', page, browserName);

                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                // Confirm new essential cookie added
                const cookies = await page.context().cookies();
                const essentialCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-essential-raw'
                );
                expect(essentialCookie).toBeDefined();

                // Confirm stub attribution service params preserve pre-existing analytics data
                // (with exception of campaign)
                expect(capture.params).not.toBeNull();

                expect(capture.params.utm_source).toBe(
                    existingAnalyticsCookieData.utm_source
                );
                expect(capture.params.utm_medium).toBe(
                    existingAnalyticsCookieData.utm_medium
                );
                expect(capture.params.client_id_ga4).toBe(
                    existingAnalyticsCookieData.client_id_ga4
                );
                expect(capture.params.dlsource).toBe(
                    existingAnalyticsCookieData.dlsource
                );
                // essential campaign should override analytics
                expect(capture.params.utm_campaign).not.toBe(
                    existingAnalyticsCookieData.utm_campaign
                );
            });
        }
    );
    test.describe(
        'new analytics data',
        {
            tag: '@firefox'
        },
        () => {
            test('pre-existing analytics data preserved', async ({
                page,
                browserName
            }) => {
                await page.addInitScript(mockGetGtagClientID);

                const initialCapture = { params: null };
                await routeStubAttributionCode(page, initialCapture);

                await openPage(
                    `/en-US/?geo=us&${existingAnalyticsParams}`,
                    page,
                    browserName
                );

                // Confirm existing cookie values
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                const existingCookies = await page.context().cookies();
                const existingAnalyticsCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(existingAnalyticsCookie).toBeDefined();
                const existingAnalyticsCookieData = JSON.parse(
                    decodeURIComponent(existingAnalyticsCookie.value)
                );
                expect(existingAnalyticsCookieData.utm_source).toBe(
                    'newsletter'
                );
                expect(existingAnalyticsCookieData.utm_medium).toBe('email');
                expect(existingAnalyticsCookieData.client_id_ga4).toBe(
                    'mocked-ga4-client-id'
                );
                expect(existingAnalyticsCookieData.dlsource).toBe('fxdotcom');
                expect(existingAnalyticsCookieData.utm_campaign).toBe(
                    'existing'
                );

                // Navigate to new page with new analytics params
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);
                await openPage(
                    '/en-US/?geo=us&utm_source=new&utm_campaign=new&utm_medium=new',
                    page,
                    browserName
                );

                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                // Confirm stub attribution service params preserve pre-existing analytics data
                expect(capture.params).not.toBeNull();

                expect(capture.params.utm_source).toBe(
                    existingAnalyticsCookieData.utm_source
                );
                expect(capture.params.utm_medium).toBe(
                    existingAnalyticsCookieData.utm_medium
                );
                expect(capture.params.client_id_ga4).toBe(
                    existingAnalyticsCookieData.client_id_ga4
                );
                expect(capture.params.dlsource).toBe(
                    existingAnalyticsCookieData.dlsource
                );
                expect(capture.params.utm_campaign).toBe(
                    existingAnalyticsCookieData.utm_campaign
                );
            });
        }
    );
});

test.describe('essential download attribution', () => {
    test.describe(
        'analytics data added',
        {
            tag: '@firefox'
        },
        () => {
            test('pre-existing essential data preserved', async ({
                page,
                browserName
            }) => {
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                // Load page where analytics consent is default denied
                await page.addInitScript(forceEssentialCampaign);
                await page.addInitScript(interceptInitAnalytics);
                await page.addInitScript(mockGetGtagClientID);

                await openPage(
                    `/fr/?geo=fr&mozcb=y&${existingAnalyticsParams}`,
                    page,
                    browserName
                );

                // Confirm there's no existing analytics cookie
                const initAnalyticsCalled = await page.evaluate(
                    () => window.__initAnalyticsCalled
                );
                expect(initAnalyticsCalled).toBe(false);

                // Confirm there is existing essential cookie
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-essential-raw='
                                )
                        );
                });

                const existingCookies = await page.context().cookies();
                const existingEssentialCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-essential-raw'
                );
                expect(existingEssentialCookie).toBeDefined();
                const existingEssentialCookieData = JSON.parse(
                    decodeURIComponent(existingEssentialCookie.value)
                );
                expect(existingEssentialCookieData.utm_campaign).toBe(
                    'smart_window'
                );

                // Change consent status
                const acceptButton = page.getByTestId(
                    'consent-banner-accept-button'
                );
                acceptButton.click();

                // Confirm analytics cookie was added
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                const cookies = await page.context().cookies();
                const analyticsCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(analyticsCookie).toBeDefined();

                // Confirm pre-existing essential data was preserved
                expect(capture.params.utm_campaign).toBe(
                    existingEssentialCookieData.utm_campaign
                );
            });
        }
    );

    test.describe(
        'new essential data',
        {
            tag: '@firefox'
        },
        () => {
            test('replaces pre-existing essential data', async ({
                page,
                browserName
            }) => {
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                // Load page where analytics consent is default denied
                await page.addInitScript(forceEssentialCampaign);

                await openPage(`/fr/?geo=fr`, page, browserName);

                // Confirm there is existing essential cookie
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-essential-raw='
                                )
                        );
                });

                const existingCookies = await page.context().cookies();
                const existingEssentialCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-essential-raw'
                );
                expect(existingEssentialCookie).toBeDefined();
                const existingEssentialCookieData = JSON.parse(
                    decodeURIComponent(existingEssentialCookie.value)
                );
                expect(existingEssentialCookieData.utm_campaign).toBe(
                    'smart_window'
                );

                // Navigate to new page with different essential campaign
                await page.addInitScript(
                    forceEssentialCampaign,
                    'download_as_default'
                );

                await openPage(`/fr/?geo=fr`, page, browserName);

                // Confirm essential cookie still exists
                await page.waitForFunction(() => {
                    return document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-essential-raw='
                                )
                        );
                });

                const cookies = await page.context().cookies();
                const essentialCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-essential-raw'
                );
                expect(essentialCookie).toBeDefined();
                const essentialCookieData = JSON.parse(
                    decodeURIComponent(essentialCookie.value)
                );
                expect(essentialCookieData.utm_campaign).toBe(
                    'download_as_default'
                );

                // Confirm new essential data was sent to stub attribution service
                expect(capture.params.utm_campaign).toBe(
                    essentialCookieData.utm_campaign
                );
            });
        }
    );
});
