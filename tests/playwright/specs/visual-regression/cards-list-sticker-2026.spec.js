/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/cards-list/cards-list_sticker2026.html`;

test.describe(
    `Sticker Card 2026 List`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('split page upper', async ({ page }) => {
            await expectComponentScreenshot(page, 'cards-list-sticker');
        });

        test('split page lower', async ({ page }) => {
            await expectComponentScreenshot(page, 'cards-list-sticker-lower');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('split page upper (dark mode)', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'cards-list-sticker',
                    'cards-list-sticker-dark'
                );
            });

            test('split page lower (dark mode)', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'cards-list-sticker-lower',
                    'cards-list-sticker-lower-dark'
                );
            });
        });
    }
);
