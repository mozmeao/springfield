/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import PartnerDownload from './partner-download.es6';

window.Mozilla.Utils.onDocumentReady(() => {
    PartnerDownload.begin();
});

// A hint for test automation that the page has loaded, as on /thanks/.
document.documentElement.classList.add('download-ready');
