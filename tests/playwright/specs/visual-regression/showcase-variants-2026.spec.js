/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/showcase/showcase_variants_2026.html`;

test.describe(
    `Showcase Variants 2026`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('default with caption', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'showcase-default-with-caption'
            );
        });

        test('default without caption', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'showcase-default-without-caption'
            );
        });

        test('expanded with caption', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'showcase-expanded-with-caption'
            );
        });

        test('expanded without caption', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'showcase-expanded-without-caption'
            );
        });

        test('full with caption', async ({ page }) => {
            await expectComponentScreenshot(page, 'showcase-full-with-caption');
        });

        test('full without caption', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'showcase-full-without-caption'
            );
        });
    }
);
