/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/heading/heading.html`;

test.describe(
    `Heading`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('heading with superheading and subheading', async ({ page }) => {
            await expectComponentScreenshot(page, 'heading');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('dark mode', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'heading',
                    'heading-dark'
                );
            });
        });
    }
);
