/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/two-column-cards/two-column-cards.html`;

test.describe(
    'Two Column Cards',
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('light-dark theme (light mode)', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'two-column-cards-light-dark'
            );
        });

        test('light-light theme (light mode)', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'two-column-cards-light-light'
            );
        });

        test('image bottom-right / bottom-left (light mode)', async ({
            page
        }) => {
            await expectComponentScreenshot(
                page,
                'two-column-cards-image-bottom'
            );
        });

        test('image full-top (light mode)', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'two-column-cards-image-full-top'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('light-dark theme (dark mode)', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'two-column-cards-light-dark',
                    'two-column-cards-light-dark-dark'
                );
            });

            test('light-light theme (dark mode)', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'two-column-cards-light-light',
                    'two-column-cards-light-light-dark'
                );
            });

            test('image bottom-right / bottom-left (dark mode)', async ({
                page
            }) => {
                await expectComponentScreenshot(
                    page,
                    'two-column-cards-image-bottom',
                    'two-column-cards-image-bottom-dark'
                );
            });

            test('image full-top (dark mode)', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'two-column-cards-image-full-top',
                    'two-column-cards-image-full-top-dark'
                );
            });
        });
    }
);
