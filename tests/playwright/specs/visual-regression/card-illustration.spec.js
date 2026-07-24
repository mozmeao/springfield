/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/card/card_illustration.html`;

test.describe(
    `Card - Illustration`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-illustration-default');
        });

        test('icon', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-illustration-icon');
        });

        test('pictogram', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'card-illustration-pictogram'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('default', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'card-illustration-default',
                    'card-illustration-default-dark'
                );
            });

            test('icon', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'card-illustration-icon',
                    'card-illustration-icon-dark'
                );
            });

            test('pictogram', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'card-illustration-pictogram',
                    'card-illustration-pictogram-dark'
                );
            });
        });
    }
);
