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
    `${url} navigation (desktop)`,
    {
        tag: '@firefox'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Navigation menu hover', async ({ page }) => {
            const resourceLink = page.getByTestId(
                'm24-navigation-link-resources'
            );
            const resourceMenu = page.getByTestId(
                'm24-navigation-menu-resources'
            );

            // Hover over Firefox link
            await resourceLink.hover();
            await expect(resourceMenu).toBeVisible();
        });

        test('Navigation link click', async ({ page }) => {
            const resourceLink = page.getByTestId(
                'm24-navigation-link-resources'
            );
            const resourceMenu = page.getByTestId(
                'm24-navigation-menu-resources'
            );
            const firefoxMenuLink = page.getByTestId(
                'm24-navigation-menu-link-firefox-desktop'
            );

            // Hover over Firefox link
            await resourceLink.hover();
            await expect(resourceMenu).toBeVisible();

            // Click Firefox desktop link
            await firefoxMenuLink.click();
            await page.waitForURL('**/#TODO', {
                waitUntil: 'commit'
            });

            // Assert Firefox menu is closed after navigation
            await expect(resourceMenu).not.toBeVisible();
        });
    }
);

test.describe(
    `${url} navigation (mobile)`,
    {
        tag: '@firefox'
    },
    () => {
        test.use({ viewport: { width: 360, height: 780 } });

        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('Navigation open / close click', async ({ page }) => {
            const navigationMenuButton = page.getByTestId(
                'm24-navigation-menu-button'
            );
            const navigationMenuItems = page.getByTestId(
                'm24-navigation-menu-items'
            );
            const resourcesMenu = page.getByTestId(
                'm24-navigation-menu-resources'
            );

            // Open navigation menu
            await navigationMenuButton.click();
            await expect(navigationMenuItems).toBeVisible();

            // Resources menu should be open by default
            await expect(resourcesMenu).toBeVisible();

            // Close navigation menu
            await navigationMenuButton.click();
            await expect(navigationMenuItems).not.toBeVisible();
        });

        test('Navigation link click', async ({ page }) => {
            const navigationMenuButton = page.getByTestId(
                'm24-navigation-menu-button'
            );
            const navigationMenuItems = page.getByTestId(
                'm24-navigation-menu-items'
            );
            const firefoxMenuLink = page.getByTestId(
                'm24-navigation-menu-link-firefox-desktop'
            );

            // Open navigation menu
            await navigationMenuButton.click();
            await expect(navigationMenuItems).toBeVisible();

            // Click firefox desktop link
            await firefoxMenuLink.click();
            await page.waitForURL('**/', {
                waitUntil: 'commit'
            });

            // Assert nav menu is closed again after navigation
            await expect(navigationMenuItems).not.toBeVisible();
        });
    }
);
