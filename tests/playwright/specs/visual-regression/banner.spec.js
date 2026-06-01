/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const openPage = require('../../scripts/open-page');
const { test } = require('@playwright/test');
const { patternLibraryURL, expectComponentScreenshot } = require('./helpers');
const url = `${patternLibraryURL}/banner/banner_variants.html`;

test.describe(
    `Banner variants`,
    {
        tag: '@visual-regression'
    },
    () => {
        test.beforeEach(async ({ page, browserName }) => {
            await openPage(url, page, browserName);
        });

        test('qr code', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-qr-code');
        });

        test('simple', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-simple');
        });

        test('with media', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-with-media');
        });

        test('with media after', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-with-media-after');
        });

        test('with video', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-with-video');
        });

        test('default', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-default');
        });

        test('dark purple', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-dark-purple');
        });

        test('dark purple inverted', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'banner-dark-purple-inverted'
            );
        });

        test('purple qr code', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-purple-qr-code');
        });

        test('purple simple', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-purple-simple');
        });

        test('purple with media', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-purple-with-media');
        });

        test('purple with media after', async ({ page }) => {
            await expectComponentScreenshot(
                page,
                'banner-purple-with-media-after'
            );
        });

        test('purple with video', async ({ page }) => {
            await expectComponentScreenshot(page, 'banner-purple-with-video');
        });

        test.describe('dark mode', () => {
            test.use({ colorScheme: 'dark' });

            test('qr code', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-qr-code',
                    'banner-qr-code-dark'
                );
            });

            test('simple', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-simple',
                    'banner-simple-dark'
                );
            });

            test('with media', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-with-media',
                    'banner-with-media-dark'
                );
            });

            test('with media after', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-with-media-after',
                    'banner-with-media-after-dark'
                );
            });

            test('with video', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-with-video',
                    'banner-with-video-dark'
                );
            });

            test('default', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-default',
                    'banner-default-dark'
                );
            });

            test('dark purple', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-dark-purple',
                    'banner-dark-purple-dark'
                );
            });

            test('dark purple inverted', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-dark-purple-inverted',
                    'banner-dark-purple-inverted-dark'
                );
            });

            test('purple qr code', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-purple-qr-code',
                    'banner-purple-qr-code-dark'
                );
            });

            test('purple simple', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-purple-simple',
                    'banner-purple-simple-dark'
                );
            });

            test('purple with media', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-purple-with-media',
                    'banner-purple-with-media-dark'
                );
            });

            test('purple with media after', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-purple-with-media-after',
                    'banner-purple-with-media-after-dark'
                );
            });

            test('purple with video', async ({ page }) => {
                await expectComponentScreenshot(
                    page,
                    'banner-purple-with-video',
                    'banner-purple-with-video-dark'
                );
            });
        });
    }
);
