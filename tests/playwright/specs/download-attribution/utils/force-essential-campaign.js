/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * Sets data-stub-attribution-campaign-force on <html> before page scripts run.
 * Pass to page.addInitScript() before navigation.
 * @param {String} campaign - Campaign name (default: 'smart_window').
 */
function forceEssentialCampaign(campaign = 'smart_window') {
    function setAttr() {
        document.documentElement.setAttribute(
            'data-stub-attribution-campaign-force',
            campaign
        );
    }
    // Init scripts run before HTML is parsed, so document.documentElement
    // may be null. Observe the document for the <html> element if needed.
    if (document.documentElement) {
        setAttr();
    } else {
        new MutationObserver(function (_, obs) {
            if (document.documentElement) {
                obs.disconnect();
                setAttr();
            }
        }).observe(document, { childList: true, subtree: true });
    }
}

module.exports = forceEssentialCampaign;
