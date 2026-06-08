/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');
const interceptInitAnalytics = require('./utils/intercept-init-analytics');
const mockGetGtagClientID = require('./utils/mock-get-gtag-client-id');
const routeStubAttributionCode = require('./utils/route-stub-attribution-code');
const forceEssentialCampaign = require('./utils/force-essential-campaign');
const removeDownloadAsDefault = require('./utils/remove-download-as-default');

const existingAnalyticsParams =
    'utm_source=newsletter&utm_medium=email&utm_campaign=existing';

test.beforeEach(async ({ page }) => {
    await removeDownloadAsDefault(page);
});

test.describe.skip('analytics download attribution', () => {
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

                // Wait for stub service response
                // (must register before navigationto avoid a race condition)
                const stubResponse = page.waitForResponse(
                    '**/stub_attribution_code/**'
                );
                await openPage('/en-US/?geo=us', page, browserName);
                await stubResponse;

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
                const page1AnalyticsCookieData = JSON.parse(
                    decodeURIComponent(existingAnalyticsCookie.value)
                );
                expect(page1AnalyticsCookieData.utm_source).toBe('newsletter');
                expect(page1AnalyticsCookieData.utm_medium).toBe('email');
                expect(page1AnalyticsCookieData.client_id_ga4).toBe(
                    'mocked-ga4-client-id'
                );
                expect(page1AnalyticsCookieData.dlsource).toBe('fxdotcom');
                expect(page1AnalyticsCookieData.utm_campaign).toBe('existing');

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

                // Confirm no call to stub attribution service
                expect(capture.params).toBeNull();

                // Confirm no change to stored analytics cookie
                const page2AnalyticsCookieData = JSON.parse(
                    decodeURIComponent(existingAnalyticsCookie.value)
                );
                expect(page2AnalyticsCookieData.utm_source).toBe(
                    page1AnalyticsCookieData.utm_source
                );
                expect(page2AnalyticsCookieData.utm_medium).toBe(
                    page1AnalyticsCookieData.utm_medium
                );
                expect(page2AnalyticsCookieData.utm_campaign).toBe(
                    page1AnalyticsCookieData.utm_campaign
                );
            });
        }
    );
});

test.describe.skip('essential download attribution', () => {
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
                await acceptButton.click();

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
                    'SET_DEFAULT_BROWSER'
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
                    'SET_DEFAULT_BROWSERT'
                );

                // Confirm new essential data was sent to stub attribution service
                expect(capture.params.utm_campaign).toBe(
                    essentialCookieData.utm_campaign
                );
            });
        }
    );
});

test.describe.skip('conflict management', () => {
    const url =
        '/en-US/?geo=us&utm_source=newsletter&utm_campaign=test&utm_medium=email';

    test('when both triggers fire on the same page, the second request call should be applied regardless of response order', async ({
        page,
        browserName
    }) => {
        // i.e. Essential trigger fires on page load and analytics trigger
        // fires moments later via the consent flow.
        // The combined essential & analytics response should be applied
        await page.route('**/stub_attribution_code/**', async (route) => {
            const url = new URL(route.request().url());
            const params = Object.fromEntries(url.searchParams);
            // Distinguish the two requests by their payload so the final
            // cookie value tells us which response was applied.
            const isEssentialOnly =
                params.campaign === 'smart_window' && !params.source;
            const tag = isEssentialOnly ? 'essential' : 'combined';

            // Slow down the combined response so the essential response
            // reliably arrives first in the unfixed code path.
            if (!isEssentialOnly) {
                await new Promise((r) => setTimeout(r, 300));
            }

            try {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        attribution_code: 'mock-code-' + tag,
                        attribution_sig: 'mock-sig-' + tag
                    })
                });
            } catch (e) {
                // route.fulfill throws if the client aborted the request;
                // that is the expected path for the essential XHR when the
                // analytics trigger pre-empts it.
            }
        });

        await page.addInitScript(forceEssentialCampaign);
        await page.addInitScript(mockGetGtagClientID);

        await openPage(url, page, browserName);

        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });
        // Give any late response a chance to overwrite, so the assertion
        // reflects the settled state rather than a transient first write.
        await page.waitForTimeout(500);

        const cookies = await page.context().cookies();
        const signedCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-code'
        );
        expect(signedCookie).toBeDefined();
        expect(signedCookie.value).toBe('mock-code-combined');
    });

    test('in-flight XHR does not resurrect analytics cookies removed by consent denial', async ({
        page,
        browserName
    }) => {
        // i.e. Analytics XHR is still in flight and user denies consent,
        // `removeAttributionData` clears the cookies.
        // The late XHR response must not write the signed cookie back.
        await page.route('**/stub_attribution_code/**', async (route) => {
            // Hold every response long enough for the consent-denial click
            // to land while the XHR is in flight.
            await new Promise((r) => setTimeout(r, 2500));
            try {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        attribution_code: 'mock-code-late',
                        attribution_sig: 'mock-sig-late'
                    })
                });
            } catch (e) {
                // Aborted by the client — expected.
            }
        });

        await page.addInitScript(mockGetGtagClientID);
        await openPage(
            '/en-US/privacy/websites/cookie-settings/?geo=us&utm_source=newsletter&utm_medium=email&utm_campaign=summer',
            page,
            browserName
        );

        // Analytics raw cookie is written client-side before the XHR
        // fires, so it appears even while the response is delayed.
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-analytics-raw=')
                );
        });

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

        await page.waitForFunction(() => {
            return !document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-analytics-raw=')
                );
        });

        // Wait past the route delay so the in-flight XHR's response has
        // had its chance to write back.
        await page.waitForTimeout(3000);

        const cookies = await page.context().cookies();
        const analyticsCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-analytics-raw'
        );
        const signedCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-code'
        );
        expect(analyticsCookie).toBeUndefined();
        expect(signedCookie).toBeUndefined();
    });

    test('in-flight XHR preserves essential attribution when analytics consent is denied', async ({
        page,
        browserName
    }) => {
        // i.e. Essential XHR is in flight and the user denies analytics consent.
        // `initAnalytics(false)` aborts the in-flight combined XHR and re-signs
        // with essential-only data. The signed cookie must appear and the
        // essential raw cookie must survive.
        await page.route('**/stub_attribution_code/**', async (route) => {
            // Delay every response so the consent-denial click lands while
            // the XHR is in flight.
            await new Promise((r) => setTimeout(r, 2500));
            try {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        attribution_code: 'mock-code-essential',
                        attribution_sig: 'mock-sig-essential'
                    })
                });
            } catch (e) {
                // Request aborted by the client — expected when a later trigger
                // pre-empts the in-flight XHR. The replacement request will
                // reach this handler separately.
            }
        });

        await page.addInitScript(forceEssentialCampaign);
        await page.addInitScript(mockGetGtagClientID);
        await openPage(
            '/en-US/privacy/websites/cookie-settings/?geo=us',
            page,
            browserName
        );

        // Essential raw cookie is written synchronously before the XHR fires,
        // so it appears even while the response is delayed.
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c
                        .trim()
                        .startsWith('moz-download-attribution-essential-raw=')
                );
        });

        // Deny analytics consent while the stub-service XHR is still in flight.
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

        // Wait for the replacement request to complete.
        await page.waitForFunction(
            () => {
                return document.cookie
                    .split(';')
                    .some((c) =>
                        c.trim().startsWith('moz-download-attribution-code=')
                    );
            },
            { timeout: 10000 }
        );

        const cookies = await page.context().cookies();
        const essentialCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-essential-raw'
        );
        const analyticsCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-analytics-raw'
        );
        const signedCookie = cookies.find(
            (c) => c.name === 'moz-download-attribution-code'
        );
        expect(essentialCookie).toBeDefined();
        expect(analyticsCookie).toBeUndefined();
        expect(signedCookie).toBeDefined();
        expect(signedCookie.value).toBe('mock-code-essential');
    });
});
