/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/sliding-carousel/sliding-carousel-2026.html`;

test.describe(
    `Sliding Carousel 2026`,
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
            await expectComponentScreenshot(page, 'sliding-carousel-light');
        });

        test('dark', async ({ page }) => {
            await expectComponentScreenshot(page, 'sliding-carousel-dark');
        });

        test.describe('mobile', () => {
            test.use({ viewport: { width: 375, height: 812 } });

            test('light mobile', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'sliding-carousel-light',
                    'sliding-carousel-light-mobile'
                );
            });
        });
    }
);
