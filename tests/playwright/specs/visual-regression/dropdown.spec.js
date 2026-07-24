/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/dropdown/dropdown.html`;

test.describe(
    'Dropdown',
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('closed', async ({ page }) => {
            await expectComponentScreenshot(page, 'dropdown-sample');
        });

        test('open', async ({ page }) => {
            await page.locator('.fl-dropdown-trigger').click();
            await page
                .locator('.fl-dropdown.fl-is-open .fl-dropdown-panel')
                .waitFor({ state: 'visible' });
            await expectComponentScreenshot(
                page,
                'dropdown-sample',
                'dropdown-sample-open'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('closed', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'dropdown-sample',
                    'dropdown-sample-dark'
                );
            });

            test('open', async ({ page }) => {
                await page.locator('.fl-dropdown-trigger').click();
                await page
                    .locator('.fl-dropdown-panel:not(.fl-is-closed)')
                    .waitFor({ state: 'visible' });
                await expectComponentScreenshot(
                    page,
                    'dropdown-sample',
                    'dropdown-sample-open-dark'
                );
            });
        });
    }
);
