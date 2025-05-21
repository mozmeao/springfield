/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');
const url = '/en-US/compare/chrome';

test.describe(
    `${url} page`,
    {
        tag: '@firefox'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Download button is displayed', async ({ page, browserName }) => {
            const downloadButtonPrimary = page
                .locator('.c-compare-footer')
                .getByRole('link', {
                    name: 'Download Firefox'
                });

            if (browserName === 'firefox') {
                await expect(downloadButtonPrimary).not.toBeVisible();
            } else {
                await expect(downloadButtonPrimary).toBeVisible();
            }
        });
    }
);
