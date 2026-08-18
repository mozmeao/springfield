/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/comparison-table/comparison-table.html`;

test.describe(
    'Comparison Table',
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('desktop highlighted', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'comparison-table-highlighted'
            );
        });

        test('desktop cell contents', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'comparison-table-cell-contents'
            );
        });

        test.describe('mobile scroll', () => {
            test.use({ viewport: { width: 375, height: 667 } });

            test('highlighted', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'comparison-table-highlighted',
                    'comparison-table-highlighted-mobile'
                );
            });
        });

        test.describe('mobile stacked', () => {
            test.use({ viewport: { width: 375, height: 667 } });

            test('stacked', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'comparison-table-stacked',
                    'comparison-table-stacked-mobile'
                );
            });

            test('cell contents', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'comparison-table-cell-contents',
                    'comparison-table-cell-contents-mobile'
                );
            });
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('desktop highlighted', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'comparison-table-highlighted',
                    'comparison-table-highlighted-dark'
                );
            });

            test('desktop cell contents', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'comparison-table-cell-contents',
                    'comparison-table-cell-contents-dark'
                );
            });
        });
    }
);
