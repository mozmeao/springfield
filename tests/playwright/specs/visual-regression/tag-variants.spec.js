/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/tag/tag_variants.html`;

test.describe(
    `Tag Variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-default');
        });

        test('default selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-default-selected');
        });

        test('red', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-red');
        });

        test('red selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-red-selected');
        });

        test('orange', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-orange');
        });

        test('orange selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-orange-selected');
        });

        test('green', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-green');
        });

        test('green selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-green-selected');
        });

        test('white', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-white');
        });

        test('white selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-white-selected');
        });

        test('light purple', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-light-purple');
        });

        test('light purple selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-light-purple-selected');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('default', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-default',
                    'tag-default-dark'
                );
            });

            test('default selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-default-selected',
                    'tag-default-selected-dark'
                );
            });

            test('red', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-red',
                    'tag-red-dark'
                );
            });

            test('red selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-red-selected',
                    'tag-red-selected-dark'
                );
            });

            test('orange', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-orange',
                    'tag-orange-dark'
                );
            });

            test('orange selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-orange-selected',
                    'tag-orange-selected-dark'
                );
            });

            test('green', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-green',
                    'tag-green-dark'
                );
            });

            test('green selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-green-selected',
                    'tag-green-selected-dark'
                );
            });

            test('white', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-white',
                    'tag-white-dark'
                );
            });

            test('white selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-white-selected',
                    'tag-white-selected-dark'
                );
            });

            test('light purple', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-light-purple',
                    'tag-light-purple-dark'
                );
            });

            test('light purple selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-light-purple-selected',
                    'tag-light-purple-selected-dark'
                );
            });
        });
    }
);
