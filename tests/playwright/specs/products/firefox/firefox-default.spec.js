/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');
const url = '/en-US/landing/set-as-default/';

test.describe(
    `${url} page`,
    {
        tag: '@firefox'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Click set Firefox as default', async ({ page, browserName }) => {
            const defaultButton = page.getByTestId('button-set-as-default');
            await expect(defaultButton).toBeVisible();
            await defaultButton.click();
            await page.waitForURL('**/landing/set-as-default/thanks/', {
                waitUntil: 'commit'
            });

            const downloadButton = page.getByTestId(
                'download-firefox-button__download-link'
            );
            const defaultMessaging = page.getByTestId(
                'firefox-not-default-message'
            );

            if (browserName !== 'firefox') {
                await expect(downloadButton).toBeVisible();
                await expect(defaultMessaging).not.toBeVisible();
            } else {
                await expect(defaultMessaging).toBeVisible();
                await expect(downloadButton).not.toBeVisible();
            }
        });
    }
);
