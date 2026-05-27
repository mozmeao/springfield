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
const removeDownloadAsDefault = require('./utils/remove-download-as-default');

test.beforeEach(async ({ page }) => {
    await removeDownloadAsDefault(page);
});

test.describe.skip('attribution cookies exist', () => {
    test('add to links', async ({ page, browserName }) => {
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        // Open home page to trigger attribution.
        await openPage('/en-US/?geo=us', page, browserName);

        // Wait for signed cookie (set after stub service responds).
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });

        // Navigate to /thanks and prevent auto-download.
        page.on('download', (download) => download.cancel());

        const downloadThanksButton = page
            .locator('[href*="thanks"]')
            .filter({ visible: true })
            .first();
        await downloadThanksButton.click();
        await page.waitForURL('**/thanks/', { waitUntil: 'commit' });

        // Wait for auto-download module to finish loading
        // (indicated by 'download-ready' class added to <html>).
        await page.waitForFunction(() =>
            document.documentElement.classList.contains('download-ready')
        );

        const directDownloadLink = page.locator('#direct-download-link');
        const href = await directDownloadLink.getAttribute('href');
        expect(href).toContain('attribution_code=mocked-attribution-code');
        expect(href).toContain('attribution_sig=mocked-attribution-sig');
    });
});

test.describe.skip('attribution cookies do not exist', () => {
    test('download links unchanged', async ({ page, browserName }) => {
        await page.addInitScript(mockGetGtagClientID);

        const capture = { params: null };
        await routeStubAttributionCode(page, capture);

        // Open home page to trigger attribution.
        await openPage('/en-US/?geo=us', page, browserName);

        // Wait for signed cookie (set after stub service responds).
        await page.waitForFunction(() => {
            return document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });

        // Navigate to cookie settings to change consent status.
        await openPage(
            '/en-US/privacy/websites/cookie-settings/?geo=us',
            page,
            browserName
        );

        // Change consent status.
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

        // Wait for signed cookie to be removed.
        await page.waitForFunction(() => {
            return !document.cookie
                .split(';')
                .some((c) =>
                    c.trim().startsWith('moz-download-attribution-code=')
                );
        });

        // Navigate to /thanks and prevent auto-download.
        page.on('download', (download) => download.cancel());
        await page.goto('/en-US/thanks/?geo=us&automation=true', {
            waitUntil: 'commit'
        });

        // Wait for auto-download module to finish loading
        // (indicated by 'download-ready' class added to <html>).
        await page.waitForFunction(() =>
            document.documentElement.classList.contains('download-ready')
        );

        const directDownloadLink = page.locator('#direct-download-link');
        const href = await directDownloadLink.getAttribute('href');
        expect(href).not.toContain('attribution_code=mocked-attribution-code');
        expect(href).not.toContain('attribution_sig=mocked-attribution-sig');
    });
});
