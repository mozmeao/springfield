/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * URL paths for inclusion in page-level a11y scans.
 * Pages will be scanned at both desktop and mobile resolutions.
 */
const desktopTestURLs = [
    '/en-US/',
    '/en-US/channel/android/',
    '/en-US/channel/desktop/',
    '/en-US/channel/desktop/developer/',
    '/en-US/download/',
    '/en-US/download/all/',
    '/en-US/thanks/',
    '/en-US/enterprise/',
    '/en-US/firefox/releasenotes/',
    '/en-US/privacy/websites/cookie-settings/'
];

const mobileTestURLs = [
    '/en-US/',
    '/en-US/channel/android/',
    '/en-US/download/'
];

module.exports = { desktopTestURLs, mobileTestURLs };
