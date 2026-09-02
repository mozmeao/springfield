/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test, expect } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/navigation/navigation.html`;

// On desktop the dropdowns open on hover (mouseover adds `.is-active`), so
// hover the first folder and wait until its panel is actually visible.
async function openFirstFolder(page) {
    await page.locator('.fl-menu-category').first().hover();
    await expect(
        page.locator('.fl-menu-category.is-active .fl-menu-panel').first()
    ).toBeVisible();
}

// The QR dropdown only renders for Firefox desktop visitors. Real UA-sniffing
// JS adds these classes to <html>; force them here since CI runs chromium.
async function makeFirefoxDesktop(page) {
    await page.evaluate(() => {
        document.documentElement.classList.add('is-firefox', 'windows');
    });
}

test.describe(
    `Navigation`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('closed', async ({ page }) => {
            await expectComponentScreenshot(page, 'navigation');
        });

        test('open folder', async ({ page }) => {
            // The open panel is absolutely positioned and overflows the header,
            // so screenshot the whole page rather than the header element.
            await openFirstFolder(page);
            await expect(page).toHaveScreenshot('navigation-open.png', {
                animations: 'disabled'
            });
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('dark mode', async ({ page }) => {
                await openFirstFolder(page);
                await expect(page).toHaveScreenshot('navigation-dark.png', {
                    animations: 'disabled'
                });
            });
        });

        test.describe('Firefox desktop (QR dropdown)', () => {
            test('closed', async ({ page }) => {
                await makeFirefoxDesktop(page);
                await expectComponentScreenshot(
                    page,
                    'navigation',
                    'navigation-get-mobile-closed'
                );
            });

            test('open', async ({ page }) => {
                await makeFirefoxDesktop(page);
                await page.locator('#nav-get-mobile').click();
                await page
                    .locator(
                        '.nav-get-mobile .fl-dropdown.fl-is-open .fl-dropdown-panel'
                    )
                    .waitFor({ state: 'visible' });
                // The open panel is absolutely positioned and overflows the
                // header, so screenshot the whole page (same as "open folder").
                await expect(page).toHaveScreenshot(
                    'navigation-get-mobile-open.png',
                    { animations: 'disabled' }
                );
            });
        });
    }
);
