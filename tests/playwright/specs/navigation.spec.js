/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../scripts/open-page');
const languages = ['en-US', 'sv-SE'];

languages.forEach((lang) => {
    test.describe(
        `${lang} navigation (desktop)`,
        {
            tag: '@firefox'
        },
        () => {
            test.beforeEach(async ({ page, browserName }) => {
                await openPage(`/${lang}/`, page, browserName);
            });

            test('Navigation menu hover', async ({ page }) => {
                const resourceLink = page.getByTestId(
                    'navigation-link-resources'
                );
                const resourceMenu = page.getByTestId(
                    'navigation-menu-resources'
                );

                // Hover over Firefox link
                await resourceLink.hover();
                await expect(resourceMenu).toBeVisible();
            });

            test('Navigation link click', async ({ page }) => {
                const resourceLink = page.getByTestId(
                    'navigation-link-resources'
                );
                const resourceMenu = page.getByTestId(
                    'navigation-menu-resources'
                );
                const firefoxMenuLink = page.getByTestId(
                    'navigation-menu-link-data-protection'
                );

                // Hover over Firefox link
                await resourceLink.hover();
                await expect(resourceMenu).toBeVisible();
                await expect(firefoxMenuLink).toBeVisible();

                // Click data protection link
                await firefoxMenuLink.click();
                await page.waitForURL('/en-US/user-privacy/', {
                    waitUntil: 'commit'
                });

                // Assert Firefox menu is closed after navigation
                await expect(resourceMenu).not.toBeVisible();
            });
        }
    );

    test.describe(
        `${lang} navigation (mobile)`,
        {
            tag: '@firefox'
        },
        () => {
            test.use({ viewport: { width: 360, height: 780 } });

            test.beforeEach(async ({ page, browserName }) => {
                await openPage(`/${lang}/`, page, browserName);
            });

            test('Navigation open / close click', async ({ page }) => {
                const navigationMenuButton = page.getByTestId(
                    'navigation-menu-button'
                );
                const navigationMenuItems = page.getByTestId(
                    'navigation-menu-items'
                );
                const browserMenu = page.getByTestId(
                    'navigation-menu-resources'
                );

                // Open navigation menu
                await navigationMenuButton.click();
                await expect(navigationMenuItems).toBeVisible();

                // Browser menu should be open by default
                await expect(browserMenu).toBeVisible();

                // Close navigation menu
                await navigationMenuButton.click();
                await expect(navigationMenuItems).not.toBeVisible();
            });

            test('Navigation link click', async ({ page }) => {
                const navigationMenuButton = page.getByTestId(
                    'navigation-menu-button'
                );
                const navigationMenuItems = page.getByTestId(
                    'navigation-menu-items'
                );
                const firefoxMenuLink = page.getByTestId(
                    'navigation-menu-link-data-protection'
                );

                // Open navigation menu
                await navigationMenuButton.click();
                await expect(navigationMenuItems).toBeVisible();
                await expect(firefoxMenuLink).toBeVisible();

                // Click mobile link
                await firefoxMenuLink.click();
                // this page only exists in the en-US locale
                await page.waitForURL(`/en-US/user-privacy/`, {
                    waitUntil: 'commit'
                });

                // Assert nav menu is closed again after navigation
                await expect(navigationMenuItems).not.toBeVisible();
            });
        }
    );
});
