/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const BASE_URL_A = process.env.HOST_A || 'http://localhost:8000';
const BASE_URL_B = process.env.HOST_B || 'https://www.firefox.com';
const LOCALE = process.env.LOCALE || 'en-US';

const PAGES = [
    { name: 'home', path: '/' },
    { name: 'download-windows', path: '/en-US/download/windows/' },
    { name: 'thanks', path: '/en-US/thanks/' },
    { name: 'whatsnew', path: '/en-US/whatsnew/' },
    { name: 'roadmap', path: '/en-US/whatsnext/' },
    { name: 'article-index', path: '/en-US/features/all/' },
    { name: 'article-hub', path: '/en-US/features/' },
    { name: 'article-detail', path: '/features/password-manager/' },
    { name: 'enterprise-landing', path: '/en-US/browsers/enterprise/' },
    { name: 'mobile-landing', path: '/en-US/mobile/' },
    { name: 'user-privacy', path: '/en-US/user-privacy/' },
    { name: 'newsletter', path: '/en-US/newsletter/' },
    { name: 'release-notes', path: '/en-US/firefox/notes/' },
    { name: 'download-all', path: '/en-US/download/all/' }
];

const VIEWPORT = { width: 1280, height: 720 };
const SCREENSHOT_OPTIONS = { fullPage: true, animations: 'disabled' };
const AUTH_FILE = path.join(__dirname, '../.auth/compare-live-auth.json');
const storageState = fs.existsSync(AUTH_FILE) ? AUTH_FILE : undefined;

for (const { name, path: pagePath } of PAGES) {
    test(name, async ({ browser }, testInfo) => {
        const localizedPath = pagePath.startsWith('/en-US/')
            ? pagePath.replace('/en-US/', `/${LOCALE}/`)
            : pagePath === '/' ? `/${LOCALE}/` : `/${LOCALE}${pagePath}`;
        const contextB = await browser.newContext({
            viewport: VIEWPORT,
            storageState
        });
        const pageB = await contextB.newPage();
        await pageB.goto(BASE_URL_B + localizedPath);
        const refScreenshot = await pageB.screenshot(SCREENSHOT_OPTIONS);
        await contextB.close();

        // Write live screenshot as comparison baseline and as a viewable artifact
        const snapshotPath = testInfo.snapshotPath(`${name}.png`);
        fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
        fs.writeFileSync(snapshotPath, refScreenshot);
        fs.writeFileSync(
            testInfo.outputPath(`${name}-live.png`),
            refScreenshot
        );

        const contextA = await browser.newContext({
            viewport: VIEWPORT,
            storageState
        });
        const pageA = await contextA.newPage();
        await pageA.goto(BASE_URL_A + localizedPath);
        const localScreenshot = await pageA.screenshot(SCREENSHOT_OPTIONS);
        fs.writeFileSync(
            testInfo.outputPath(`${name}-local.png`),
            localScreenshot
        );
        await contextA.close();

        expect(localScreenshot).toMatchSnapshot(`${name}.png`);
    });
}
