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

const existingMarketingParams =
    'utm_source=newsletter&utm_medium=email&utm_campaign=existing';

test.describe('marketing download attribution', () => {
    test.describe(
        'user action denies consent',
        {
            tag: '@firefox'
        },
        () => {
            test('cookie removed', async ({ page, browserName }) => {
                await page.addInitScript(mockGetGtagClientID);
                await openPage(
                    `/en-US/privacy/websites/cookie-settings/?geo=us&${existingMarketingParams}`,
                    page,
                    browserName
                );
                // confirm there's an existing cookie
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
                const existingCookies = await page.context().cookies();
                const existingMarketingCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(existingMarketingCookie).toBeDefined();

                // change consent status
                const analyticsCategory = await page.getByTestId(
                    'cookie-consent-analytics'
                );
                const disagreeOption =
                    await analyticsCategory.getByLabel(/I do not agree/i);
                await disagreeOption.click();
                const saveButton = await page.getByRole('button', {
                    name: /Save changes/i
                });
                await saveButton.click();

                // confirm cookie is removed
                const cookies = await page.context().cookies();
                const marketingCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(marketingCookie).toBeUndefined();
            });

            test('marketing data removed from stub attribution service call', async ({
                page,
                browserName
            }) => {
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                await page.addInitScript(forceEssentialCampaign);
                await page.addInitScript(mockGetGtagClientID);
                await openPage(
                    `/en-US/privacy/websites/cookie-settings/?geo=us&${existingMarketingParams}`,
                    page,
                    browserName
                );
                // confirm there's an existing cookie
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
                const existingCookies = await page.context().cookies();
                const existingMarketingCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-marketing-raw'
                );
                expect(existingMarketingCookie).toBeDefined();
                const existingEssentialCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-essential-raw'
                );
                const existingEssentialCookieData = JSON.parse(
                    decodeURIComponent(existingEssentialCookie.value)
                );

                // change consent status
                const analyticsCategory = await page.getByTestId(
                    'cookie-consent-analytics'
                );
                const disagreeOption =
                    await analyticsCategory.getByLabel(/I do not agree/i);
                await disagreeOption.click();
                const saveButton = await page.getByRole('button', {
                    name: /Save changes/i
                });
                await saveButton.click();

                // Confirm stub attribution service call uses essential campaign param only
                expect(capture.params).not.toBeNull();

                expect(capture.params.utm_campaign).toBe(
                    existingEssentialCookieData.utm_campaign
                );
                expect(capture.params.utm_source).toBeUndefined();
                expect(capture.params.utm_medium).toBeUndefined();
                expect(capture.params.client_id_ga4).toBeUndefined();
                expect(capture.params.dlsource).toBeUndefined();
            });
        }
    );
});

test.describe('essential download attribution', () => {
    test.describe('new page with no essential data', () => {
        test('cookie removed', async ({ page, browserName }) => {
            const capture = { params: null };
            await routeStubAttributionCode(page, capture);

            // Load page where marketing consent is allowed
            await page.addInitScript(forceEssentialCampaign);
            await openPage(
                `/en-US/?geo=us&${existingMarketingParams}`,
                page,
                browserName
            );

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

            // Navigate to new page with no essential campaign.
            // A fresh page is required so the forceEssentialCampaign init
            // script (registered on `page`) does not run again and re-set
            // data-stub-attribution-campaign-force on the second navigation.
            const page2 = await page.context().newPage();
            await routeStubAttributionCode(page2, capture);
            await openPage(`/en-US/?geo=us`, page2, browserName);

            // Confirm there is existing marketing cookie
            await page2.waitForFunction(() => {
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

            // Confirm essential cookie does not exist
            const cookies = await page2.context().cookies();
            const essentialCookie = cookies.find(
                (c) => c.name === 'moz-download-attribution-essential-raw'
            );
            expect(essentialCookie).toBeUndefined();
        });
        test('essential campaign removed from stub attribution service call', async ({
            page,
            browserName
        }) => {
            const capture = { params: null };
            await routeStubAttributionCode(page, capture);

            // Load page where marketing consent is allowed
            await page.addInitScript(forceEssentialCampaign);
            await openPage(
                `/en-US/?geo=us&${existingMarketingParams}`,
                page,
                browserName
            );

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
            const existingMarketingCookie = existingCookies.find(
                (c) => c.name === 'moz-download-attribution-essential-raw'
            );
            expect(existingEssentialCookie).toBeDefined();
            const existingEssentialCookieData = JSON.parse(
                decodeURIComponent(existingEssentialCookie.value)
            );
            const existingMarketingCookieData = JSON.parse(
                decodeURIComponent(existingMarketingCookie.value)
            );
            expect(existingEssentialCookieData.utm_campaign).toBe(
                'smart_window'
            );

            // Navigate to new page with no essential campaign
            await openPage(`/en-US/?geo=us`, page, browserName);
            await page.waitForLoadState('networkidle');

            // Confirm stub attribution service call uses marketing campaign
            expect(capture.params).not.toBeNull();

            expect(capture.params.utm_campaign).toBe(
                existingMarketingCookieData.utm_campaign
            );
        });
    });
});
