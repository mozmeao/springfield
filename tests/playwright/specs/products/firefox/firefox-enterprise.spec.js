/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const openPage = require('../../../scripts/open-page');
const languages = ['en-US', 'ja'];
const pageUrl = '/LANG/browsers/enterprise/';
const downloadBaseUrl = 'https://download.mozilla.org/';

languages.forEach((lang) => {
    const url = pageUrl.replace('LANG', lang);
    // Download language code for Windows is the same as the locale code.
    const winDownloadLang = lang;
    // For Japanese, the macOS download language code is `ja-JP-mac`.
    const macDownloadLang = lang === 'ja' ? 'ja-JP-mac' : lang;

    test.describe(
        `${url} page`,
        {
            tag: '@firefox'
        },
        () => {
            test.beforeEach(async ({ page, browserName }) => {
                await openPage(url, page, browserName);
            });

            test('Firefox ESR Windows 64bit menu open / close', async ({
                page
            }) => {
                const win64MenuButton = page.getByTestId(
                    'firefox-enterprise-win64-menu-button'
                );
                const win64MenuLink = page.getByTestId(
                    'firefox-enterprise-win64-menu-link'
                );
                const win64MsiMenuLink = page.getByTestId(
                    'firefox-enterprise-win64-msi-menu-link'
                );
                const win64EsrMenuLink = page.getByTestId(
                    'firefox-enterprise-win64-esr-menu-link'
                );
                const win64EsrMsiMenuLink = page.getByTestId(
                    'firefox-enterprise-win64-esr-msi-menu-link'
                );

                await expect(win64MenuLink).not.toBeVisible();
                await expect(win64MsiMenuLink).not.toBeVisible();
                await expect(win64EsrMenuLink).not.toBeVisible();
                await expect(win64EsrMsiMenuLink).not.toBeVisible();

                // open menu
                await win64MenuButton.click();

                // Assert Windows 64-bit menu links are displayed.
                await expect(win64MenuLink).toBeVisible();
                await expect(win64MenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-latest-ssl&os=win64&lang=${winDownloadLang}`
                    )
                );
                await expect(win64MsiMenuLink).toBeVisible();
                await expect(win64MsiMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-msi-latest-ssl&os=win64&lang=${winDownloadLang}`
                    )
                );
                await expect(win64EsrMenuLink).toBeVisible();
                await expect(win64EsrMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-latest-ssl&os=win64&lang=${winDownloadLang}`
                    )
                );
                await expect(win64EsrMsiMenuLink).toBeVisible();
                await expect(win64EsrMsiMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-msi-latest-ssl&os=win64&lang=${winDownloadLang}`
                    )
                );

                // close menu
                await win64MenuButton.click();

                // Assert Windows 64-bit menu links are hidden.
                await expect(win64MenuLink).not.toBeVisible();
                await expect(win64MsiMenuLink).not.toBeVisible();
                await expect(win64EsrMenuLink).not.toBeVisible();
                await expect(win64EsrMsiMenuLink).not.toBeVisible();
            });

            test('Firefox ESR macOS menu open / close', async ({ page }) => {
                const macMenuButton = page.getByTestId(
                    'firefox-enterprise-mac-menu-button'
                );
                const macMenuLink = page.getByTestId(
                    'firefox-enterprise-mac-menu-link'
                );
                const macPkgMenuLink = page.getByTestId(
                    'firefox-enterprise-mac-pkg-menu-link'
                );
                const macEsrMenuLink = page.getByTestId(
                    'firefox-enterprise-mac-esr-menu-link'
                );
                const macEsrPkgMenuLink = page.getByTestId(
                    'firefox-enterprise-mac-esr-pkg-menu-link'
                );

                await expect(macMenuLink).not.toBeVisible();
                await expect(macPkgMenuLink).not.toBeVisible();
                await expect(macEsrMenuLink).not.toBeVisible();
                await expect(macEsrPkgMenuLink).not.toBeVisible();

                // open menu
                await macMenuButton.click();

                // Assert macOS menu links are displayed.
                await expect(macMenuLink).toBeVisible();
                await expect(macMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-latest-ssl&os=osx&lang=${macDownloadLang}`
                    )
                );
                await expect(macPkgMenuLink).toBeVisible();
                await expect(macPkgMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-pkg-latest-ssl&os=osx&lang=${macDownloadLang}`
                    )
                );
                await expect(macEsrMenuLink).toBeVisible();
                await expect(macEsrMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-latest-ssl&os=osx&lang=${macDownloadLang}`
                    )
                );
                await expect(macEsrPkgMenuLink).toBeVisible();
                await expect(macEsrPkgMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-pkg-latest-ssl&os=osx&lang=${macDownloadLang}`
                    )
                );

                // close menu
                await macMenuButton.click();

                // Assert macOS menu links are hidden.
                await expect(macMenuLink).not.toBeVisible();
                await expect(macPkgMenuLink).not.toBeVisible();
                await expect(macEsrMenuLink).not.toBeVisible();
                await expect(macEsrPkgMenuLink).not.toBeVisible();
            });

            test('Firefox ESR Linux menu open / close', async ({ page }) => {
                const linuxMenuButton = page.getByTestId(
                    'firefox-enterprise-linux-menu-button'
                );
                const linuxMenuLink = page.getByTestId(
                    'firefox-enterprise-linux-menu-link'
                );
                const linuxArm64MenuLink = page.getByTestId(
                    'firefox-enterprise-linux-arm64-menu-link'
                );
                const linuxEsrMenuLink = page.getByTestId(
                    'firefox-enterprise-linux-esr-menu-link'
                );
                const linuxEsrArm64MenuLink = page.getByTestId(
                    'firefox-enterprise-linux-esr-arm64-menu-link'
                );

                await expect(linuxMenuLink).not.toBeVisible();
                await expect(linuxArm64MenuLink).not.toBeVisible();
                await expect(linuxEsrMenuLink).not.toBeVisible();
                await expect(linuxEsrArm64MenuLink).not.toBeVisible();

                // open menu
                await linuxMenuButton.click();

                // Assert Linux menu links are displayed.
                await expect(linuxMenuLink).toBeVisible();
                await expect(linuxMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-latest-ssl&os=linux64&lang=${lang}`
                    )
                );
                await expect(linuxArm64MenuLink).toBeVisible();
                await expect(linuxArm64MenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-latest-ssl&os=linux64-aarch64&lang=${lang}`
                    )
                );
                await expect(linuxEsrMenuLink).toBeVisible();
                await expect(linuxEsrMenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-latest-ssl&os=linux64&lang=${lang}`
                    )
                );
                await expect(linuxEsrArm64MenuLink).toBeVisible();
                await expect(linuxEsrArm64MenuLink).toHaveAttribute(
                    'href',
                    new RegExp(
                        `^${downloadBaseUrl}\\?product=firefox-esr-latest-ssl&os=linux64-aarch64&lang=${lang}`
                    )
                );

                // close menu
                await linuxMenuButton.click();

                // Assert Linux menu links are hidden.
                await expect(linuxMenuLink).not.toBeVisible();
                await expect(linuxArm64MenuLink).not.toBeVisible();
                await expect(linuxEsrMenuLink).not.toBeVisible();
                await expect(linuxEsrArm64MenuLink).not.toBeVisible();
            });
        }
    );
});
