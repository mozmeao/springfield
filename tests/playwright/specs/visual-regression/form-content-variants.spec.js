/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/form-content/form-content_variants.html`;

test.describe(
    `Form Content Variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('form after', async ({ page }) => {
            await expectComponentScreenshot(page, 'form-content-form-after');
        });

        test('form before', async ({ page }) => {
            await expectComponentScreenshot(page, 'form-content-form-before');
        });

        test('two column form', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'form-content-two-column-form'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('form after', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'form-content-form-after',
                    'form-content-form-after-dark'
                );
            });

            test('form before', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'form-content-form-before',
                    'form-content-form-before-dark'
                );
            });

            test('two column form', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'form-content-two-column-form',
                    'form-content-two-column-form-dark'
                );
            });
        });
    }
);
