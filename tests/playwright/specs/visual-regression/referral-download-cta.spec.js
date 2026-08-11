/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/referral-download-cta/referral-download-cta.html`;

/**
 * Simulate what referral-attribution.es6.js does on init: remove .hidden from
 * the consent label and set the checkbox to checked. Scoped to the given
 * data-testid so the two fixtures on the page don't interfere.
 */
async function initConsentUI(page, testId) {
    await page.evaluate((id) => {
        const root = document.querySelector(`[data-testid="${id}"]`);
        root.querySelector('.referral-consent-label').classList.remove(
            'hidden'
        );
        root.querySelector('.referral-consent-checkbox').checked = true;
    }, testId);
}

test.describe(
    `Referral Download CTA`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default state (before JS init)', async ({ page }) => {
            await expectComponentScreenshot(page, 'referral-download-cta');
        });

        test('initialized state (consent UI visible)', async ({ page }) => {
            await initConsentUI(page, 'referral-download-cta-initialized');
            await expectComponentScreenshot(
                page,
                'referral-download-cta-initialized'
            );
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('default state dark mode', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'referral-download-cta',
                    'referral-download-cta-dark'
                );
            });

            test('initialized state dark mode', async ({ page }) => {
                await initConsentUI(page, 'referral-download-cta-initialized');
                await expectComponentScreenshot(
                    page,
                    'referral-download-cta-initialized',
                    'referral-download-cta-initialized-dark'
                );
            });
        });
    }
);
