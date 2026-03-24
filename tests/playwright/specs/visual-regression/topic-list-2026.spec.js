/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/topic/topic-list2026.html`;

test.describe(
    `Topic list 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('desktop', async ({ page }) => {
            await expectComponentScreenshot(page, 'topic-list');
        });

        test.describe('mobile', () => {
            test.use({ viewport: { width: 375, height: 812 } });

            test('mobile', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'topic-list',
                    'topic-list-mobile'
                );
            });
        });

        test.describe('dark theme', () => {
            test.use({ colorScheme: 'dark' });

            test('dark theme', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'topic-list',
                    'topic-list-dark'
                );
            });
        });
    }
);
