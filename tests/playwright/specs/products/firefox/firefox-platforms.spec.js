/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');

test.describe(
    'Platform download pages',
    {
        tag: '@firefox'
    },
    () => {
        test('Download Firefox for Windows', async ({ page, browserName }) => {
            const downloadButton = page.locator(
                '#download-button-desktop-release-win'
            );

            await openPage(
                '/en-US/browsers/desktop/windows/',
                page,
                browserName
            );

            // Assert download button is visible
            await expect(downloadButton).toBeVisible();
            // Assert download button links to advertised platform
            await expect(downloadButton).toHaveAttribute('href', /os=win/);

            // Click download
            const downloadPromise = page.waitForEvent('download');
            await downloadButton.click();

            const download = await downloadPromise;
            expect(download.url()).toContain('win');

            // Cancel download
            await download.cancel();
        });

        test('Download Firefox for Mac', async ({ page, browserName }) => {
            const downloadButton = page.locator(
                '#download-button-desktop-release-osx'
            );

            await openPage('/en-US/browsers/desktop/mac/', page, browserName);

            // Assert download button is visible
            await expect(downloadButton).toBeVisible();
            // Assert download button links to advertised platform
            await expect(downloadButton).toHaveAttribute('href', /os=osx/);

            // Click download
            const downloadPromise = page.waitForEvent('download');
            await downloadButton.click();

            const download = await downloadPromise;
            expect(download.url()).toEqual(expect.stringMatching(/mac|osx/));

            // Cancel download
            await download.cancel();
        });

        test('Download Firefox for Mac in Japanese (bedrock#16294)', async ({
            page,
            browserName
        }) => {
            const downloadButton = page.locator(
                '#download-button-desktop-release-osx'
            );

            await openPage('/ja/browsers/desktop/mac/', page, browserName);

            //
            await expect(downloadButton).toHaveAttribute(
                'href',
                /lang=ja-JP-mac/
            );

            // Click download
            const downloadPromise = page.waitForEvent('download');
            await downloadButton.click();

            const download = await downloadPromise;
            expect(download.url()).toEqual(expect.stringMatching(/mac|osx/));

            // Cancel download
            await download.cancel();
        });

        test('Download Firefox for Linux (and APT info)', async ({
            page,
            browserName
        }) => {
            const downloadButton = page.locator(
                '#download-button-desktop-release-linux'
            );
            const repoLink = page.locator('.c-linux-debian a');

            await openPage('/en-US/browsers/desktop/linux/', page, browserName);

            // Assert APT instruction link is visible
            await expect(repoLink).toBeVisible();

            // Assert download button is visible
            await expect(downloadButton).toBeVisible();
            // Assert download button links to advertised platform
            await expect(downloadButton).toHaveAttribute('href', /os=linux/);

            // Click download
            const downloadPromise = page.waitForEvent('download');
            await downloadButton.click();

            const download = await downloadPromise;
            expect(download.url()).toContain('linux');

            // Cancel download
            await download.cancel();
        });
    }
);
