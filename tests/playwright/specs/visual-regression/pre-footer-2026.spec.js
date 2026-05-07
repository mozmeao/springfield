/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');

test.describe(
    `Pre-footer 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test('newsletter form cta', async ({ page, browserName }) => {
            await openPage(
                `${patternLibraryURL}/pre-footer/newsletterform-cta.html`,
                page,
                browserName
            );
            await expectComponentScreenshot(page, 'newsletter-form-cta');
        });

        test('pre-footer cta', async ({ page, browserName }) => {
            await openPage(
                `${patternLibraryURL}/pre-footer/pre-footer-cta.html`,
                page,
                browserName
            );
            await expectComponentScreenshot(page, 'pre-footer-cta');
        });
    }
);
