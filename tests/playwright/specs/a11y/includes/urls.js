/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * URL paths for inclusion in page-level a11y scans.
 * Different set of pages will be scanned at desktop and mobile resolutions.
 */
const desktopTestURLs = [
    '/en-US/',
    '/en-US/browsers/desktop/',
    '/en-US/browsers/desktop/linux/',
    '/en-US/browsers/enterprise/',
    '/en-US/browsers/mobile/',
    '/en-US/browsers/mobile/android/',
    '/en-US/browsers/mobile/ios/',
    '/en-US/browsers/mobile/focus/',
    '/en-US/browsers/mobile/get-app/',
    '/en-US/channel/android/',
    '/en-US/channel/desktop/',
    '/en-US/channel/desktop/developer/',
    '/en-US/download/all/',
    '/en-US/compare/',
    '/en-US/compare/opera/',
    '/en-US/features/',
    '/en-US/features/sync/',
    '/en-US/firefox/releasenotes/',
    '/en-US/privacy/websites/cookie-settings/',
    '/en-US/thanks/'
];

const mobileTestURLs = [
    '/en-US/',
    '/en-US/browsers/mobile/',
    '/en-US/browsers/mobile/android/',
    '/en-US/browsers/mobile/ios/',
    '/en-US/browsers/mobile/focus/',
    '/en-US/channel/android/',
    '/en-US/download/all/',
    '/en-US/firefox/android/notes/',
    '/en-US/thanks/'
];

module.exports = { desktopTestURLs, mobileTestURLs };
