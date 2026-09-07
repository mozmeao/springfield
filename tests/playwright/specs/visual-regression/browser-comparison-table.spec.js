/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/browser-comparison-table/browser-comparison-table.html`;

test.describe(
    'Browser Comparison Table',
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('desktop', async ({ page }) => {
            await expectComponentScreenshot(page, 'browser-comparison-table');
        });

        test.describe('mobile stacked', () => {
            test.use({ viewport: { width: 375, height: 667 } });

            test('stacked', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'browser-comparison-table',
                    'browser-comparison-table-mobile'
                );
            });
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('desktop', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'browser-comparison-table',
                    'browser-comparison-table-dark'
                );
            });
        });
    }
);
