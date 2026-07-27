/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/intro/intro_variants.html`;

test.describe(
    `Intro variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('media after', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-media-after');
        });

        test('media before', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-media-before');
        });

        test('no media', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-no-media');
        });

        test('video', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-video');
        });

        test('media right', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-media-right');
        });

        test('media left', async ({ page }) => {
            await expectComponentScreenshot(page, 'intro-media-left');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('media after', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'intro-media-after',
                    'intro-media-after-dark'
                );
            });

            test('media before', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'intro-media-before',
                    'intro-media-before-dark'
                );
            });

            test('no media', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'intro-no-media',
                    'intro-no-media-dark'
                );
            });

            test('video', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'intro-video',
                    'intro-video-dark'
                );
            });
        });
    }
);
