/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test, expect } = require('@playwright/test');
const { patternLibraryURL } = require('../visual-regression/helpers');
const url = `${patternLibraryURL}/roadmap-list-section/roadmap-list-section.html`;

test.describe(
    `Roadmap List Section`,
    {
        tag: '@flare-components'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test.describe('filter button', () => {
            test('sets is-selected on the tag when clicked', async ({
                page
            }) => {
                const button = page.locator(
                    '.fl-roadmap-filter-button[data-filter="desktop"]'
                );
                await button.click();
                await expect(button.locator('.fl-tag')).toHaveClass(
                    /is-selected/
                );
            });

            test('removes is-selected from the tag when clicked again', async ({
                page
            }) => {
                const button = page.locator(
                    '.fl-roadmap-filter-button[data-filter="desktop"]'
                );
                await button.click();
                await button.click();
                await expect(button.locator('.fl-tag')).not.toHaveClass(
                    /is-selected/
                );
            });

            test('sets aria-pressed on the button when clicked', async ({
                page
            }) => {
                const button = page.locator(
                    '.fl-roadmap-filter-button[data-filter="desktop"]'
                );
                await button.click();
                await expect(button).toHaveAttribute('aria-pressed', 'true');
            });

            test('removes aria-pressed from the button when clicked again', async ({
                page
            }) => {
                const button = page.locator(
                    '.fl-roadmap-filter-button[data-filter="desktop"]'
                );
                await button.click();
                await button.click();
                await expect(button).toHaveAttribute('aria-pressed', 'false');
            });
        });
    }
);
