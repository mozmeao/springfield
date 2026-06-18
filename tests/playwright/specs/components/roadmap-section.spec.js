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

        test.describe('mobile accordion', () => {
            test.use({ viewport: { width: 375, height: 667 } });

            test.beforeEach(async ({ page, browserName }) => {
                await openPage(url, page, browserName);
            });

            test('toggle button is visible on mobile', async ({ page }) => {
                const toggle = page
                    .locator('.fl-roadmap-section-toggle .fl-icon-subtract')
                    .first();
                await expect(toggle).toBeVisible();
            });

            test('sections start expanded on mobile', async ({ page }) => {
                const sections = page.locator('.fl-roadmap-list-section');
                const count = await sections.count();
                for (let i = 0; i < count; i++) {
                    const section = sections.nth(i);
                    await expect(
                        section.locator('.fl-roadmap-list')
                    ).toBeVisible();
                }
            });

            test('clicking toggle collapses the section', async ({ page }) => {
                const section = page
                    .locator('.fl-roadmap-list-section')
                    .first();
                const toggle = section.locator('.fl-roadmap-section-toggle');
                await expect(toggle).toHaveAttribute('aria-expanded', 'true');
                await toggle.click();
                await expect(toggle).toHaveAttribute('aria-expanded', 'false');
                await expect(
                    section.locator('.fl-roadmap-list')
                ).not.toBeVisible();
            });

            test('clicking toggle again expands the section', async ({
                page
            }) => {
                const section = page
                    .locator('.fl-roadmap-list-section')
                    .first();
                const toggle = section.locator('.fl-roadmap-section-toggle');
                await toggle.click();
                await toggle.click();
                await expect(toggle).toHaveAttribute('aria-expanded', 'true');
                await expect(section.locator('.fl-roadmap-list')).toBeVisible();
            });
        });

        test('toggle button is hidden on desktop', async ({ page }) => {
            const toggle = page
                .locator('.fl-roadmap-section-toggle .fl-icon-subtract')
                .first();
            await expect(toggle).not.toBeVisible();
        });
    }
);
