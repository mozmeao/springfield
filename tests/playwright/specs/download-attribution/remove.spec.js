/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');
const mockGetGtagClientID = require('./utils/mock-get-gtag-client-id');
const routeStubAttributionCode = require('./utils/route-stub-attribution-code');
const forceEssentialCampaign = require('./utils/force-essential-campaign');
const removeDownloadAsDefault = require('./utils/remove-download-as-default');

const existingAnalyticsParams =
    'utm_source=newsletter&utm_medium=email&utm_campaign=existing';

test.beforeEach(async ({ page }) => {
    await removeDownloadAsDefault(page);
});

test.describe('analytics download attribution', () => {
    test.describe(
        'user action denies consent',
        {
            tag: '@firefox'
        },
        () => {
            test('cookie removed', async ({ page, browserName }) => {
                await page.addInitScript(mockGetGtagClientID);
                await openPage(
                    `/en-US/privacy/websites/cookie-settings/?geo=us&${existingAnalyticsParams}`,
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
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });
                const existingCookies = await page.context().cookies();
                const existingAnalyticsCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(existingAnalyticsCookie).toBeDefined();

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

                // Wait for cookie removal before reading updated state.
                await page.waitForFunction(() => {
                    return !document.cookie
                        .split(';')
                        .some((c) =>
                            c
                                .trim()
                                .startsWith(
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });

                // confirm cookie is removed
                const cookies = await page.context().cookies();
                const analyticsCookie = cookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(analyticsCookie).toBeUndefined();
            });

            test('analytics data removed from stub attribution service call', async ({
                page,
                browserName
            }) => {
                const capture = { params: null };
                await routeStubAttributionCode(page, capture);

                await page.addInitScript(forceEssentialCampaign);
                await page.addInitScript(mockGetGtagClientID);
                await openPage(
                    `/en-US/privacy/websites/cookie-settings/?geo=us&${existingAnalyticsParams}`,
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
                                    'moz-download-attribution-analytics-raw='
                                )
                        );
                });
                const existingCookies = await page.context().cookies();
                const existingAnalyticsCookie = existingCookies.find(
                    (c) => c.name === 'moz-download-attribution-analytics-raw'
                );
                expect(existingAnalyticsCookie).toBeDefined();
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

                const stubResponse = page.waitForResponse(
                    '**/stub_attribution_code/**'
                );
                await saveButton.click();
                await stubResponse;

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

            // Load page where analytics consent is allowed
            await page.addInitScript(forceEssentialCampaign);
            await openPage(
                `/en-US/?geo=us&${existingAnalyticsParams}`,
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
            await removeDownloadAsDefault(page2);
            await routeStubAttributionCode(page2, capture);
            await openPage(`/en-US/?geo=us`, page2, browserName);

            // Wait for essential cookie removal. The analytics cookie from the
            // first navigation is already present, so waiting on it would
            // resolve immediately without confirming the essential cookie is gone.
            await page2.waitForFunction(() => {
                return !document.cookie
                    .split(';')
                    .some((c) =>
                        c
                            .trim()
                            .startsWith(
                                'moz-download-attribution-essential-raw='
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

            // Load page where analytics consent is allowed
            await page.addInitScript(forceEssentialCampaign);
            await page.addInitScript(mockGetGtagClientID);
            await openPage(
                `/en-US/?geo=us&${existingAnalyticsParams}`,
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

            // Confirm analytics cookie is also set before reading it
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
            const existingEssentialCookie = existingCookies.find(
                (c) => c.name === 'moz-download-attribution-essential-raw'
            );
            const existingAnalyticsCookie = existingCookies.find(
                (c) => c.name === 'moz-download-attribution-analytics-raw'
            );
            expect(existingEssentialCookie).toBeDefined();
            const existingEssentialCookieData = JSON.parse(
                decodeURIComponent(existingEssentialCookie.value)
            );
            const existingAnalyticsCookieData = JSON.parse(
                decodeURIComponent(existingAnalyticsCookie.value)
            );
            expect(existingEssentialCookieData.utm_campaign).toBe(
                'smart_window'
            );

            // A fresh page is required so the forceEssentialCampaign init
            // script (registered on `page`) does not run again and re-set
            // data-stub-attribution-campaign-force on the second navigation.
            const page2 = await page.context().newPage();
            await removeDownloadAsDefault(page2);
            await routeStubAttributionCode(page2, capture);
            const stubResponse = page2.waitForResponse(
                '**/stub_attribution_code/**'
            );
            await openPage(`/en-US/?geo=us`, page2, browserName);
            await stubResponse;

            // Confirm stub attribution service call uses analytics campaign
            expect(capture.params).not.toBeNull();

            expect(capture.params.utm_campaign).toBe(
                existingAnalyticsCookieData.utm_campaign
            );
        });
    });
});
