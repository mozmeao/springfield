/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/media-content/media-content_variants.html`;

test.describe(
    `Media Content Variants 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('media before', async ({ page }) => {
            await expectComponentScreenshot(page, 'media-content-media-before');
        });

        test('media after', async ({ page }) => {
            await expectComponentScreenshot(page, 'media-content-media-after');
        });

        test('no eyebrow', async ({ page }) => {
            await expectComponentScreenshot(page, 'media-content-no-eyebrow');
        });

        test('youtube video', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'media-content-youtube-video'
            );
        });

        test('cdn video', async ({ page }) => {
            await expectComponentScreenshot(page, 'media-content-cdn-video');
        });
    }
);
