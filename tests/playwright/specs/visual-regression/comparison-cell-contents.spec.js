/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');

const components = [
    {
        name: 'comparison-result',
        url: `${patternLibraryURL}/comparison-result/comparison-result.html`
    },
    {
        name: 'comparison-image-header',
        url: `${patternLibraryURL}/comparison-image-header/comparison-image-header.html`
    }
];

test.describe(
    'Comparison cell contents',
    {
        tag: '@visual-regression'
    },
    () => {
        components.forEach(({ name, url }) => {
            test.describe(name, () => {
                test.beforeEach(async ({ page, browserName }) => {
                    await openPage(url, page, browserName);
                });

                test('light mode', async ({ page }) => {
                    await expectComponentScreenshot(page, name);
                });

                test.describe('dark mode', () => {
                    test.use({ colorScheme: 'dark' });

                    test('dark mode', async ({ page }) => {
                        await expectComponentScreenshot(
                            page,
                            name,
                            `${name}-dark`
                        );
                    });
                });
            });
        });
    }
);
