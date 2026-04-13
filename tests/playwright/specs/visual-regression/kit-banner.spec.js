/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/banner/kit_banner_variants_2026.html`;

test.describe(
    `Kit Banner`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('variant 1', async ({ page }) => {
            await expectComponentScreenshot(page, 'kit-banner-variant-1');
        });

        test('variant 2', async ({ page }) => {
            await expectComponentScreenshot(page, 'kit-banner-variant-2');
        });
    }
);
