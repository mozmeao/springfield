/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/media/image_caption.html`;

test.describe(
    `Image + Caption`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'image-caption');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('default', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'image-caption',
                    'image-caption-dark'
                );
            });
        });
    }
);
