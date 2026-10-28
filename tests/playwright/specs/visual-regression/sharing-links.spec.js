/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test, expect } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/sharing-links/sharing-links.html`;

// The dialog opens in the top layer, outside its pattern library row, so it is captured on its own.
async function expectOpenQRCodeDialogScreenshot(page, snapshotName) {
    await page
        .locator('[data-testid="sharing-links-full"] .fl-sharing-links-qr')
        .click();
    const dialog = page.locator('dialog[open]');
    await dialog.waitFor({ state: 'visible' });
    await expect(dialog).toHaveScreenshot(`${snapshotName}.png`, {
        animations: 'disabled'
    });
}

test.describe(
    `Sharing links`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('all fields', async ({ page }) => {
            await expectComponentScreenshot(page, 'sharing-links-full');
        });

        test('required fields only', async ({ page }) => {
            await expectComponentScreenshot(page, 'sharing-links-required');
        });

        test('open QR code dialog', async ({ page }) => {
            await expectOpenQRCodeDialogScreenshot(
                page,
                'sharing-links-qr-dialog'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('all fields', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'sharing-links-full',
                    'sharing-links-full-dark'
                );
            });

            test('required fields only', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'sharing-links-required',
                    'sharing-links-required-dark'
                );
            });

            test('open QR code dialog', async ({ page }) => {
                await expectOpenQRCodeDialogScreenshot(
                    page,
                    'sharing-links-qr-dialog-dark'
                );
            });
        });
    }
);
