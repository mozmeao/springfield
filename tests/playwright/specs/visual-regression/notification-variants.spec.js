/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/notification/notification-variants.html`;

test.describe(
    `Notification variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('purple', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-purple');
        });

        test('red', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-red');
        });

        test('orange', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-orange');
        });

        test('green', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-green');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('purple', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'notification-purple',
                    'notification-purple-dark'
                );
            });

            test('red', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'notification-red',
                    'notification-red-dark'
                );
            });

            test('orange', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'notification-orange',
                    'notification-orange-dark'
                );
            });

            test('green', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'notification-green',
                    'notification-green-dark'
                );
            });
        });
    }
);
