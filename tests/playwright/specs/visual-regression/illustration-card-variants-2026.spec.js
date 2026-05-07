/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/illustration-card/illustration-card_variants.html`;

test.describe(
    `Illustration Card Variants 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'illustration-card-default');
        });

        test('icon', async ({ page }) => {
            await expectComponentScreenshot(page, 'illustration-card-icon');
        });

        test('sticker', async ({ page }) => {
            await expectComponentScreenshot(page, 'illustration-card-sticker');
        });
    }
);
