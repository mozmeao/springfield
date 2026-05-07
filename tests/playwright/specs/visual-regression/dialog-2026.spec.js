/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/dialog/dialog-2026.html`;

test.describe(
    `Dialog 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('open dialog', async ({ page }) => {
            await page.locator('.fl-dialog-trigger').first().click();
            await page.locator('dialog[open]').waitFor({ state: 'visible' });
            await expectComponentScreenshot(page, 'dialog-sample');
        });
    }
);
