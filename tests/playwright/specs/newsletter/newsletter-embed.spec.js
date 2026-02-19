/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../scripts/open-page');
const url = '/en-US/';
const slugs = ['channel/desktop/developer', 'newsletter'];

slugs.forEach((slug) => {
    test.describe(
        `${url}${slug} page`,
        {
            tag: '@newsletter'
        },
        () => {
            test.beforeEach(async ({ page, browserName }) => {
                await openPage(url + `${slug}/`, page, browserName);
            });

            test(`Newsletter submit success /${slug}/`, async ({ page }) => {
                const form = page.getByTestId('newsletter-form');
                const emailField = page.getByTestId('newsletter-email-input');
                const countryField = page.getByTestId(
                    'newsletter-country-select'
                );
                const privacyCheckbox = page.getByTestId(
                    'newsletter-privacy-checkbox'
                );
                const submitButton = page.getByTestId(
                    'newsletter-submit-button'
                );
                const thanksMessage = page.getByTestId(
                    'newsletter-thanks-message'
                );

                await emailField.fill('success@example.com');
                await countryField.selectOption('us');
                await privacyCheckbox.click();
                await submitButton.click();
                await expect(form).not.toBeVisible();
                await expect(thanksMessage).toBeVisible();
            });

            test(`Newsletter submit failure /${slug}/`, async ({ page }) => {
                const emailField = page.getByTestId('newsletter-email-input');
                const countryField = page.getByTestId(
                    'newsletter-country-select'
                );
                const privacyCheckbox = page.getByTestId(
                    'newsletter-privacy-checkbox'
                );
                const submitButton = page.getByTestId(
                    'newsletter-submit-button'
                );
                const thanksMessage = page.getByTestId(
                    'newsletter-thanks-message'
                );
                const errorMessage = page.getByTestId(
                    'newsletter-error-message'
                );

                // show an error message because the email is invalid
                await expect(errorMessage).not.toBeVisible();
                await emailField.fill('invalid-email');
                await countryField.selectOption('us');
                await privacyCheckbox.click();
                await submitButton.click();
                await expect(errorMessage).toBeVisible();
                await expect(thanksMessage).not.toBeVisible();
            });
        }
    );
});
