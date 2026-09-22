/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/tag/tag_variants.html`;

test.describe(
    `Tag Variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-default');
        });

        test('default selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-default-selected');
        });

        test('grey', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-grey');
        });

        test('grey selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-grey-selected');
        });

        test('blog topic', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-blog-topic');
        });

        test('blog topic selected', async ({ page }) => {
            await expectComponentScreenshot(page, 'tag-blog-topic-selected');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('default', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-default',
                    'tag-default-dark'
                );
            });

            test('default selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-default-selected',
                    'tag-default-selected-dark'
                );
            });

            test('grey', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-grey',
                    'tag-grey-dark'
                );
            });

            test('grey selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-grey-selected',
                    'tag-grey-selected-dark'
                );
            });

            test('blog topic', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-blog-topic',
                    'tag-blog-topic-dark'
                );
            });

            test('blog topic selected', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'tag-blog-topic-selected',
                    'tag-blog-topic-selected-dark'
                );
            });
        });
    }
);
