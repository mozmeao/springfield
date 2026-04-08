/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/notification/notification-variants-2026.html`;

test.describe(
    `Notification variants 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('dark purple', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-dark-purple');
        });

        test('dark red', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-dark-red');
        });

        test('dark orange', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-dark-orange');
        });

        test('dark green', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-dark-green');
        });

        test('light purple', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-light-purple');
        });

        test('light red', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-light-red');
        });

        test('light orange', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-light-orange');
        });

        test('light green', async ({ page }) => {
            await expectComponentScreenshot(page, 'notification-light-green');
        });
    }
);
