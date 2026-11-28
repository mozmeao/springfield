/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { baseStylesURL, expectComponentScreenshot } = require('./helpers');
const url = `${baseStylesURL}/typography/typography_examples.html`;

// The only capture of the Compact scale and the Enterprise heading face; component specs render Regular.
test.describe(
    `Typography`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('desktop', async ({ page }) => {
            await expectComponentScreenshot(page, 'typography');
        });

        test.describe('mobile', () => {
            test.use({ viewport: { width: 375, height: 812 } });

            test('mobile', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'typography',
                    'typography-mobile'
                );
            });
        });
    }
);
