/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');
const url = '/en-US/channel/desktop/';

test.describe(
    `${url} page`,
    {
        tag: '@firefox'
    },
    () => {
        test('Download Firefox Beta / DevEdition / Nightly (Windows, macOS)', async ({
            page,
            browserName
        }) => {
            const win64BetaDownload = page.getByTestId(
                'desktop-beta-download-win64'
            );
            const winDevDownload = page.getByTestId(
                'desktop-developer-download-win'
            );
            const winNightlyDownload = page.getByTestId(
                'desktop-nightly-download-win'
            );
            const osxBetaDownload = page.getByTestId(
                'desktop-beta-download-osx'
            );
            const osxDevDownload = page.getByTestId(
                'desktop-developer-download-osx'
            );
            const osxNightlyDownload = page.getByTestId(
                'desktop-nightly-download-osx'
            );

            await openPage(url, page, browserName);

            if (browserName === 'webkit') {
                // Assert macOS download buttons are displayed.
                await expect(osxBetaDownload).toBeVisible();
                await expect(osxBetaDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-beta-latest-ssl&os=osx/
                );
                await expect(osxDevDownload).toBeVisible();
                await expect(osxDevDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-devedition-latest-ssl&os=osx/
                );
                await expect(osxNightlyDownload).toBeVisible();
                await expect(osxNightlyDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-nightly-latest-ssl&os=osx/
                );

                // Assert Windows download buttons are not displayed.
                await expect(win64BetaDownload).not.toBeVisible();
                await expect(winDevDownload).not.toBeVisible();
                await expect(winNightlyDownload).not.toBeVisible();
            } else {
                /**
                 * Assert Windows download buttons are displayed.
                 * Note: we serve the full installer for Firefox Beta on Windows.
                 * See https://github.com/mozilla/bedrock/issues/9836
                 * and https://github.com/mozilla/bedrock/issues/10194
                 */
                await expect(win64BetaDownload).toBeVisible();
                await expect(win64BetaDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-beta-latest-ssl&os=win64/
                );
                await expect(winDevDownload).toBeVisible();
                await expect(winDevDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-devedition-stub&os=win/
                );
                await expect(winNightlyDownload).toBeVisible();
                await expect(winNightlyDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-nightly-stub&os=win/
                );

                // Assert macOS download buttons are not displayed.
                await expect(osxBetaDownload).not.toBeVisible();
                await expect(osxDevDownload).not.toBeVisible();
                await expect(osxNightlyDownload).not.toBeVisible();
            }
        });

        test('Download Firefox Beta / DevEdition / Nightly (Linux)', async ({
            page,
            browserName
        }) => {
            test.skip(
                browserName === 'webkit',
                'Safari not available on Linux'
            );

            // Set Linux UA strings.
            await page.addInitScript({
                path: `./scripts/useragent/linux/${browserName}.js`
            });
            await page.goto(url + '?automation=true');

            // Linux 32 buttons disappearing in 145 (Issue #466)
            const latest_firefox = await page.evaluate(
                () =>
                    document.documentElement
                        .getAttribute('data-latest-firefox')
                        .split('.')[0]
            );
            const nightly_linux_32 = latest_firefox < 143 ? true : false;
            const dev_linux_32 = latest_firefox < 144 ? true : false;
            const beta_linux_32 = latest_firefox < 144 ? true : false;

            let linuxBetaDownload;
            if (beta_linux_32) {
                linuxBetaDownload = page.getByTestId(
                    'desktop-beta-download-linux'
                );
            }
            const linux64BetaDownload = page.getByTestId(
                'desktop-beta-download-linux64'
            );

            let linuxDevDownload;
            if (dev_linux_32) {
                linuxDevDownload = page.getByTestId(
                    'desktop-developer-download-linux'
                );
            }
            const linux64DevDownload = page.getByTestId(
                'desktop-developer-download-linux64'
            );

            let linuxNightlyDownload;
            if (nightly_linux_32) {
                linuxNightlyDownload = page.getByTestId(
                    'desktop-nightly-download-linux'
                );
            }
            const linux64NightlyDownload = page.getByTestId(
                'desktop-nightly-download-linux64'
            );

            const win64BetaDownload = page.getByTestId(
                'desktop-beta-download-win64'
            );
            const winDevDownload = page.getByTestId(
                'desktop-developer-download-win'
            );
            const winNightlyDownload = page.getByTestId(
                'desktop-nightly-download-win'
            );
            const osxBetaDownload = page.getByTestId(
                'desktop-beta-download-osx'
            );
            const osxDevDownload = page.getByTestId(
                'desktop-developer-download-osx'
            );
            const osxNightlyDownload = page.getByTestId(
                'desktop-nightly-download-osx'
            );

            // Assert Linux download buttons are displayed.
            if (beta_linux_32) {
                await expect(linuxBetaDownload).toBeVisible();
                await expect(linuxBetaDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-beta-latest-ssl&os=linux/
                );
            }
            await expect(linux64BetaDownload).toBeVisible();
            await expect(linux64BetaDownload).toHaveAttribute(
                'href',
                /\?product=firefox-beta-latest-ssl&os=linux64/
            );
            if (dev_linux_32) {
                await expect(linuxDevDownload).toBeVisible();
                await expect(linuxDevDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-devedition-latest-ssl&os=linux/
                );
            }
            await expect(linux64DevDownload).toBeVisible();
            await expect(linux64DevDownload).toHaveAttribute(
                'href',
                /\?product=firefox-devedition-latest-ssl&os=linux64/
            );
            if (nightly_linux_32) {
                await expect(linuxNightlyDownload).toBeVisible();
                await expect(linuxNightlyDownload).toHaveAttribute(
                    'href',
                    /\?product=firefox-nightly-latest-ssl&os=linux/
                );
            }
            await expect(linux64NightlyDownload).toBeVisible();
            await expect(linux64NightlyDownload).toHaveAttribute(
                'href',
                /\?product=firefox-nightly-latest-ssl&os=linux64/
            );

            // Assert Windows / macOS download buttons are not displayed.
            await expect(win64BetaDownload).not.toBeVisible();
            await expect(winDevDownload).not.toBeVisible();
            await expect(winNightlyDownload).not.toBeVisible();
            await expect(osxBetaDownload).not.toBeVisible();
            await expect(osxDevDownload).not.toBeVisible();
            await expect(osxNightlyDownload).not.toBeVisible();
        });

        test('Firefox unsupported OS version messaging (Win / Mac)', async ({
            page,
            browserName
        }) => {
            const win64BetaDownload = page.getByTestId(
                'desktop-beta-download-win64'
            );
            const winDevDownload = page.getByTestId(
                'desktop-developer-download-win'
            );
            const winNightlyDownload = page.getByTestId(
                'desktop-nightly-download-win'
            );
            const osxBetaDownload = page.getByTestId(
                'desktop-beta-download-osx'
            );
            const osxDevDownload = page.getByTestId(
                'desktop-developer-download-osx'
            );
            const osxNightlyDownload = page.getByTestId(
                'desktop-nightly-download-osx'
            );

            const betaDownloadOsxUnsupported = page.locator(
                'css=.download-button-beta .fx-unsupported-message.mac .download-link'
            );
            const devDownloadOsxUnsupported = page.locator(
                'css=.download-button-alpha .fx-unsupported-message.mac .download-link'
            );
            const nightlyDownloadOsxUnsupported = page.locator(
                'css=.download-button-nightly .fx-unsupported-message.mac .download-link'
            );
            const betaDownloadWinUnsupported = page.locator(
                'css=.download-button-beta .fx-unsupported-message.win .download-link.os_win64'
            );
            const devDownloadWinUnsupported = page.locator(
                'css=.download-button-alpha .fx-unsupported-message.win .download-link.os_win64'
            );
            const nightlyDownloadWinUnsupported = page.locator(
                'css=.download-button-nightly .fx-unsupported-message.win .download-link.os_win64'
            );

            if (browserName === 'webkit') {
                // Set macOS 10.14 UA strings.
                await page.addInitScript({
                    path: `./scripts/useragent/mac-old/${browserName}.js`
                });
                await page.goto(url + '?automation=true');

                // Assert ESR button is displayed instead of Firefox Beta button.
                await expect(betaDownloadOsxUnsupported).toBeVisible();
                await expect(betaDownloadOsxUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=osx/
                );
                await expect(osxBetaDownload).not.toBeVisible();

                // Assert ESR button is displayed instead of Firefox Developer Edition button.
                await expect(devDownloadOsxUnsupported).toBeVisible();
                await expect(devDownloadOsxUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=osx/
                );
                await expect(osxDevDownload).not.toBeVisible();

                // Assert ESR button is displayed instead of Firefox Nightly button.
                await expect(nightlyDownloadOsxUnsupported).toBeVisible();
                await expect(nightlyDownloadOsxUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=osx/
                );
                await expect(osxNightlyDownload).not.toBeVisible();
            } else {
                // Set Windows 8.1 UA string (64-bit).
                await page.addInitScript({
                    path: `./scripts/useragent/win-old/${browserName}.js`
                });
                await page.goto(url + '?automation=true');

                // Assert ESR button is displayed instead of Firefox Beta 64-bit button.
                await expect(betaDownloadWinUnsupported).toBeVisible();
                await expect(betaDownloadWinUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=win64/
                );
                await expect(win64BetaDownload).not.toBeVisible();

                // Assert ESR button is displayed instead of Firefox Developer Edition button.
                await expect(devDownloadWinUnsupported).toBeVisible();
                await expect(devDownloadWinUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=win64/
                );
                await expect(winDevDownload).not.toBeVisible();

                // Assert ESR button is displayed instead of Firefox Nightly button.
                await expect(nightlyDownloadWinUnsupported).toBeVisible();
                await expect(nightlyDownloadWinUnsupported).toHaveAttribute(
                    'href',
                    /\?product=firefox-esr115-latest-ssl&os=win64/
                );
                await expect(winNightlyDownload).not.toBeVisible();
            }
        });
    }
);
