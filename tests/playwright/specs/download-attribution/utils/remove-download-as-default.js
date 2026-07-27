/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * Prevents the download-as-default feature from interfering with
 * attribution tests by blocking the JS bundles and removing checkbox
 * elements from the DOM before page scripts run.
 * @param {import('@playwright/test').Page} page
 */
async function removeDownloadAsDefault(page) {
    await page.route('**/js/download_as_default*.js', (route) => route.abort());
    await page.addInitScript(() => {
        const obs = new MutationObserver(() => {
            const labels = document.querySelectorAll('.default-browser-label');
            if (labels.length > 0) {
                labels.forEach((el) => el.remove());
                obs.disconnect();
            }
        });
        obs.observe(document, { childList: true, subtree: true });
    });
}

module.exports = removeDownloadAsDefault;
