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
    }
);
