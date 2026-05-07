/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/card/card_variants.html`;

test.describe(
    `Card Variants 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('icon card', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-icon');
        });

        test('icon card - no buttons', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-icon-no-buttons');
        });

        test('icon card - clickable', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-icon-clickable');
        });

        test('sticker card', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-sticker');
        });

        test('sticker card - no buttons', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-sticker-no-buttons');
        });

        test('sticker card - clickable', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-sticker-clickable');
        });

        test('filled card', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-filled');
        });

        test('filled card - multiple tags', async ({ page }) => {
            await expectComponentScreenshot(page, 'card-filled-multiple-tags');
        });
    }
);
