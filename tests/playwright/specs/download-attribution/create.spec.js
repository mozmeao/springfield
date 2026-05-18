/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');

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

function forceEssentialCampaign() {
    function setAttr() {
        document.documentElement.setAttribute(
            'data-stub-attribution-campaign-force',
            'smart_window'
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

/**
 * Prevents the download-as-default feature from interfering with
 * attribution tests by blocking the JS bundles and removing checkbox
 * elements from the DOM before page scripts run.
 * @param {import('@playwright/test').Page} page
 */
async function removeDownloadAsDefault(page) {
    await page.route('**/js/download_as_default*.js', (route) => route.abort());
    await page.addInitScript(() => {
        const obs = new MutationObserver(() => {
            const labels = document.querySelectorAll('.default-browser-label');
            if (labels.length > 0) {
                labels.forEach((el) => el.remove());
                obs.disconnect();
            }
        });
        obs.observe(document, { childList: true, subtree: true });
    });
}

const existingAnalyticsParams =
    'utm_source=newsletter&utm_medium=email&utm_campaign=existing';

test.beforeEach(async ({ page }) => {
    await removeDownloadAsDefault(page);
});

test.describe('analytics download attribution', () => {
    test('has expected cookie values', async ({ page, browserName }) => {
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(
            '/en-US/?geo=us&utm_source=newsletter&utm_campaign=test&utm_medium=email',
            page,
            browserName
        );

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-analytics-raw=')
                );
        });

        // Wait for signed cookie, which is set only after the stub
        // service responds, to ensure capture.params is populated.
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });

        const cookies = await page.context().cookies();
        const analyticsCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-analytics-raw'
        );
        expect(analyticsCookie).toBeDefined();
        const cookieData = JSON.parse(
            decodeURIComponent(analyticsCookie.value)
        );
        expect(cookieData.utm_source).toBe('newsletter');
        expect(cookieData.utm_campaign).toBe('test');
        expect(cookieData.utm_medium).toBe('email');
        expect(cookieData.client_id_ga4).toBe('mocked-ga4-client-id');
        expect(cookieData.dlsource).toBe('fxdotcom');
    });

    test('params for stub attribution service request match cookie values', async ({
        page,
        browserName
    }) => {
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(
            '/en-US/?geo=us&utm_source=newsletter&utm_campaign=test&utm_medium=email',
            page,
            browserName
        );

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-analytics-raw=')
                );
        });

        expect(capture.params).not.toBeNull();

        // Wait for signed cookie, which is set only after the stub
        // service responds, to ensure capture.params is populated.
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });

        const cookies = await page.context().cookies();
        const analyticsCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-analytics-raw'
        );
        expect(analyticsCookie).toBeDefined();
        const cookieData = JSON.parse(
            decodeURIComponent(analyticsCookie.value)
        );
        expect(cookieData.utm_source).toBe(capture.params.utm_source);
        expect(cookieData.utm_campaign).toBe(capture.params.utm_campaign);
        expect(cookieData.utm_medium).toBe(capture.params.utm_medium);
        expect(cookieData.client_id_ga4).toBe(capture.params.client_id_ga4);
        expect(cookieData.dlsource).toBe(capture.params.dlsource);
    });
    test.describe('not consent required geo', () => {
        test.describe(
            'default',
            {
                tag: '@firefox'
            },
            () => {
                const url = '/en-US/?geo=us';

                test('cookie created', async ({ page, browserName }) => {
                    await page.addInitScript(mockGetGtagClientID);

                    const capture = { params: null };
                    await routeStubAttributionCode(page, capture);

                    await openPage(url, page, browserName);

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
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeDefined();
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

                test('DNT enabled - cookie NOT created', async ({
                    page,
                    browserName
                }) => {
                    await page.addInitScript(interceptInitAnalytics, {
                        mockDNT: true
                    });
                    await openPage(url, page, browserName);
                    await page.waitForLoadState('networkidle');

                    const initAnalyticsCalled = await page.evaluate(
                        () => window.__initAnalyticsCalled
                    );
                    expect(initAnalyticsCalled).toBe(false);

                    const cookies = await page.context().cookies();
                    const analyticsCookie = cookies.find(
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeUndefined();
                });

                test('GPC enabled - cookie NOT created', async ({
                    page,
                    browserName
                }) => {
                    await page.addInitScript(interceptInitAnalytics, {
                        mockGPC: true
                    });
                    await openPage(url, page, browserName);
                    await page.waitForLoadState('networkidle');

                    const initAnalyticsCalled = await page.evaluate(
                        () => window.__initAnalyticsCalled
                    );
                    expect(initAnalyticsCalled).toBe(false);

                    const cookies = await page.context().cookies();
                    const analyticsCookie = cookies.find(
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeUndefined();
                });

                test('Pref cookie denies analytics - cookie NOT created', async ({
                    page,
                    browserName,
                    baseURL
                }) => {
                    await page.addInitScript(interceptInitAnalytics);
                    await page.context().addCookies([
                        {
                            name: 'moz-consent-pref',
                            value: JSON.stringify({ analytics: false }),
                            url: baseURL
                        }
                    ]);
                    await openPage(url, page, browserName);
                    await page.waitForLoadState('networkidle');

                    const initAnalyticsCalled = await page.evaluate(
                        () => window.__initAnalyticsCalled
                    );
                    expect(initAnalyticsCalled).toBe(false);

                    const cookies = await page.context().cookies();
                    const analyticsCookie = cookies.find(
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeUndefined();
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
                test('cookie NOT created', async ({ page, browserName }) => {
                    await page.addInitScript(interceptInitAnalytics);
                    await openPage('/fr/?geo=fr', page, browserName);
                    await page.waitForLoadState('networkidle');

                    const initAnalyticsCalled = await page.evaluate(
                        () => window.__initAnalyticsCalled
                    );
                    expect(initAnalyticsCalled).toBe(false);

                    const cookies = await page.context().cookies();
                    const analyticsCookie = cookies.find(
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeUndefined();
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
                test('cookie created', async ({
                    page,
                    browserName,
                    baseURL
                }) => {
                    await page.addInitScript(mockGetGtagClientID);

                    const capture = { params: null };
                    await routeStubAttributionCode(page, capture);

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
                                        'moz-download-attribution-analytics-raw='
                                    )
                            );
                    });

                    const cookies = await page.context().cookies();
                    const analyticsCookie = cookies.find(
                        (c) =>
                            c.name === 'moz-download-attribution-analytics-raw'
                    );
                    expect(analyticsCookie).toBeDefined();
                });
            }
        );
    });

    test.describe(
        'user action grants consent',
        {
            tag: '@firefox'
        },
        () => {
            test('cookie created', async ({ page, browserName }) => {
                await page.addInitScript(interceptInitAnalytics);
                await page.addInitScript(mockGetGtagClientID);
                await openPage(
                    `/fr/?geo=fr&mozcb=y&${existingAnalyticsParams}`,
                    page,
                    browserName
                );

                // confirm there's no existing cookie
                await page.waitForLoadState('networkidle');

                const initAnalyticsCalled = await page.evaluate(
                    () => window.__initAnalyticsCalled
                );
                expect(initAnalyticsCalled).toBe(false);

                const existingAnalyticsCookies = await page.context().cookies();
                const existingAnalyticsCookie = existingAnalyticsCookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(existingAnalyticsCookie).toBeUndefined();

                // change consent status
                const acceptButton = page.getByTestId(
                    'consent-banner-accept-button'
                );
                await acceptButton.click();

                // check analytics cookie was added
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
            });
        }
    );
});

test.describe('essential download attribution', () => {
    const url = '/en-US/?geo=us';

    test('has expected cookie values', async ({ page, browserName }) => {
        await page.addInitScript(forceEssentialCampaign);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(url, page, browserName);

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-essential-raw=')
                );
        });

        const cookies = await page.context().cookies();
        const essentialCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-essential-raw'
        );

        const cookieData = JSON.parse(
            decodeURIComponent(essentialCookie.value)
        );
        expect(cookieData.utm_campaign).toBe('smart_window');
    });

    test('params for stub attribution service request match cookie values', async ({
        page,
        browserName
    }) => {
        await page.addInitScript(forceEssentialCampaign);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(url, page, browserName);

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-essential-raw=')
                );
        });

        expect(capture.params).not.toBeNull();

        const cookies = await page.context().cookies();
        const essentialCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-essential-raw'
        );

        const cookieData = JSON.parse(
            decodeURIComponent(essentialCookie.value)
        );
        expect(cookieData.utm_campaign).toBe(capture.params.utm_campaign);
    });

    test.describe(
        'analytics granted',
        {
            tag: '@firefox'
        },
        () => {
            test('cookie created', async ({ page, browserName }) => {
                await page.addInitScript(forceEssentialCampaign);

                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                await openPage(url, page, browserName);

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
            });
        }
    );
    test.describe(
        'analytics denied',
        {
            tag: '@firefox'
        },
        () => {
            test('cookie created', async ({ page, browserName }) => {
                await page.addInitScript(forceEssentialCampaign);

                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                await openPage('/fr/?geo=fr', page, browserName);

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
            });
        }
    );
});

test.describe('essential and analytics download attribution', () => {
    const url =
        '/en-US/?geo=us&utm_source=newsletter&utm_campaign=test&utm_medium=email';

    test('creates a cookie for each type of data', async ({
        page,
        browserName
    }) => {
        await page.addInitScript(forceEssentialCampaign);
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(url, page, browserName);

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-essential-raw=')
                );
        });

        const cookies = await page.context().cookies();
        const analyticsCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-analytics-raw'
        );
        const essentialCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-essential-raw'
        );

        expect(analyticsCookie).toBeDefined();
        expect(essentialCookie).toBeDefined();
    });

    test('campaign param for stub attribution service request matches essential cookie campaign value', async ({
        page,
        browserName
    }) => {
        await page.addInitScript(forceEssentialCampaign);
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        await openPage(url, page, browserName);

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-essential-raw=')
                );
        });

        const cookies = await page.context().cookies();
        const essentialCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-essential-raw'
        );
        const essentialCookieData = JSON.parse(
            decodeURIComponent(essentialCookie.value)
        );

        expect(essentialCookieData.utm_campaign).toBe(
            capture.params.utm_campaign
        );
    });
});
