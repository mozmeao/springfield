/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../scripts/open-page');
const url = '/en-US/';

test.describe(
    `${url} footer (mobile)`,
    {
        tag: '@firefox'
    },
    () => {
        test.use({ viewport: { width: 360, height: 780 } });

        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Footer language change - mobile', async ({ page }) => {
            const languageSelect = page
                .getByTestId('fl-footer-mobile')
                .getByTestId('footer-language-select')
                .filter({ visible: true });

            // Assert default language is English
            await expect(languageSelect).toHaveValue('en-US');

            // Change page language from /en-US/ to /nl/
            await languageSelect.selectOption('nl');
            await page.waitForURL('/nl/?automation=true*', {
                waitUntil: 'commit'
            });

            // Assert page language is now Dutch
            await expect(
                page
                    .getByTestId('footer-language-select')
                    .filter({ visible: true })
            ).toHaveValue('nl');
        });
    }
);

test.describe(
    `${url} footer (desktop)`,
    {
        tag: '@firefox'
    },
    () => {
        test.use({ viewport: { width: 1280, height: 720 } });

        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Footer language change - desktop', async ({ page }) => {
            const languageSelect = page
                .getByTestId('fl-footer-desktop')
                .getByTestId('footer-language-select')
                .filter({ visible: true });

            // Assert default language is English
            await expect(languageSelect).toHaveValue('en-US');

            // Change page language from /en-US/ to /nl/
            await languageSelect.selectOption('nl');
            await page.waitForURL('/nl/?automation=true*', {
                waitUntil: 'commit'
            });

            // Assert page language is now Dutch
            await expect(
                page
                    .getByTestId('footer-language-select')
                    .filter({ visible: true })
            ).toHaveValue('nl');
        });
    }
);
