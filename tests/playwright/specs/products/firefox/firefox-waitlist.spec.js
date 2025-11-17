/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');
const url = '/en-US/ai';

test.describe(
    `${url} page`,
    {
        tag: '@newsletter'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test(`Newsletter submit success`, async ({ page }) => {
            const form = page.getByTestId('newsletter-form');
            const emailField = page.getByTestId('newsletter-email-input');
            const privacyCheckbox = page.getByTestId(
                'newsletter-privacy-checkbox'
            );
            const submitButton = page.getByTestId('newsletter-submit-button');
            const thanksMessage = page.getByTestId('newsletter-thanks-message');

            await expect(thanksMessage).not.toBeVisible();
            await emailField.fill('success@example.com');
            await privacyCheckbox.click();
            await submitButton.click();
            await expect(form).not.toBeVisible();
            await expect(thanksMessage).toBeVisible();
        });

        test(`Newsletter submit frontend validation failure`, async ({
            page
        }) => {
            const emailField = page.getByTestId('newsletter-email-input');
            const submitButton = page.getByTestId('newsletter-submit-button');
            const thanksMessage = page.getByTestId('newsletter-thanks-message');
            const emailInvalidErrorMessage = page.getByTestId(
                'newsletter-error-message-email-invalid'
            );
            const privacyErrorMessage = page.getByTestId(
                'newsletter-error-message-privacy'
            );

            await submitButton.click();
            await expect(emailInvalidErrorMessage).toBeVisible();
            await expect(thanksMessage).not.toBeVisible();

            await emailField.fill('failure@example.com');
            await submitButton.click();
            await expect(emailInvalidErrorMessage).not.toBeVisible();
            await expect(privacyErrorMessage).toBeVisible();
            await expect(thanksMessage).not.toBeVisible();
        });

        test(`Newsletter submit API failure`, async ({ page }) => {
            const emailField = page.getByTestId('newsletter-email-input');
            const privacyCheckbox = page.getByTestId(
                'newsletter-privacy-checkbox'
            );
            const submitButton = page.getByTestId('newsletter-submit-button');
            const thanksMessage = page.getByTestId('newsletter-thanks-message');
            const tryAgainErrorMessage = page.getByTestId(
                'newsletter-error-message-try-again'
            );

            await expect(tryAgainErrorMessage).not.toBeVisible();
            await emailField.fill('failure@example.com');
            await privacyCheckbox.click();
            await submitButton.click();
            await expect(tryAgainErrorMessage).toBeVisible();
            await expect(thanksMessage).not.toBeVisible();
        });
    }
);
