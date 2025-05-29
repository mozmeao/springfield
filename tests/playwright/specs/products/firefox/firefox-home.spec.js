/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');
const url = '/en-US/browsers/desktop/';

test.describe(
    `${url} page`,
    {
        tag: '@firefox'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Download Firefox desktop', async ({ page }) => {
            // Click download button.
            const downloadButton = page.getByTestId('firefox-desktop-download');
            await expect(downloadButton).toBeVisible();
            await downloadButton.click();
            await page.waitForURL('**/thanks/', {
                waitUntil: 'commit'
            });

            // Assert /thanks/ page triggers file download.
            const download = await page.waitForEvent('download');
            const downloadURL = download.url();

            expect(downloadURL).toEqual(
                expect.stringMatching(
                    /https:\/\/download-installer.cdn.mozilla.net\/|https:\/\/cdn-stage.stubattribution.nonprod.cloudops.mozgcp.net\/|https:\/\/cdn.stubdownloader.services.mozilla.com\//
                )
            );

            // Cancel download if not finished.
            await download.cancel();
        });

        test('Account form sign up', async ({ page }) => {
            const emailQueryString = /&email=success%40example.com/;
            const accountButton = page.getByTestId('fxa-form-submit-button');
            const emailField = page.getByTestId('fxa-form-email-field');

            await emailField.fill('success@example.com');
            await accountButton.click();
            await page.waitForURL(emailQueryString, {
                waitUntil: 'commit'
            });
            await expect(page).toHaveURL(emailQueryString);
        });
    }
);
