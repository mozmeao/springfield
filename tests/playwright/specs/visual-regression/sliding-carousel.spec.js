/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/sliding-carousel/sliding-carousel.html`;

test.describe(
    `Sliding Carousel`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await page.emulateMedia({ reducedMotion: 'reduce' });
            await openPage(url, page, browserName);
            await page.waitForTimeout(1000);
        });

        test('light', async ({ page }) => {
            await expectComponentScreenshot(page, 'sliding-carousel');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('dark mode', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'sliding-carousel',
                    'sliding-carousel-dark'
                );
            });
        });

        test.describe('mobile', () => {
            test.use({ viewport: { width: 375, height: 812 } });

            test('light mobile', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'sliding-carousel',
                    'sliding-carousel-mobile'
                );
            });
        });
    }
);
