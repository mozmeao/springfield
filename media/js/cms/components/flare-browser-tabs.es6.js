/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { detectBrowser, isBrave } from './flare-browser-detect.es6';

/**
 * Auto-select the tab comparing the visitor's own browser against Firefox.
 *
 * Kept out of flare-tabs.es6.js: tabs are a general-purpose component, and
 * only the browser comparison tables care who the visitor is. A tablist opts
 * in purely by having tabs with a data-browser attribute, which TabBlock's
 * "Detected browser" field sets. Tablists without it are left alone.
 */

// Where visitors with no tab of their own end up. Firefox users land here too:
// the tables all compare Firefox against something else, so there is never a
// Firefox tab to select.
const FALLBACK_BROWSER = 'chrome';

function getBrowserTab(tablist, browser) {
    return browser
        ? tablist.querySelector('[role=tab][data-browser="' + browser + '"]')
        : null;
}

/**
 * @param {Array<TabsAutomatic>} tabInstances - as returned by setupTabs().
 */
export default function setupBrowserTabs(tabInstances) {
    if (!tabInstances || !tabInstances.length) {
        return;
    }

    const browser = detectBrowser();

    tabInstances.forEach(function (tabs) {
        const tablist = tabs.tablistNode;

        // Opt-in check.
        if (!tablist.querySelector('[role=tab][data-browser]')) {
            return;
        }

        // Select synchronously, so a single tab is always shown rather than
        // leaving the pre-JS state (every panel visible) up while the Brave
        // check below settles.
        const match =
            getBrowserTab(tablist, browser) ||
            getBrowserTab(tablist, FALLBACK_BROWSER);
        if (match) {
            tabs.setSelectedTab(match, false);
        }

        // Brave ships Chrome's user agent verbatim, so a Brave tab can only be
        // resolved asynchronously. Only worth asking when a Brave tab exists
        // and detection landed on Chrome, which is what Brave looks like.
        const braveTab = getBrowserTab(tablist, 'brave');
        if (browser === 'chrome' && braveTab && navigator.brave) {
            // The result can land after the visitor has already picked a tab, at
            // which point applying it would yank the panel out from under them.
            // An explicit choice always outranks this guess, so watch for one
            // and stand down if it comes.
            let hasActed = false;
            const noteAction = function () {
                hasActed = true;
            };
            const events = ['click', 'keydown', 'focusin'];
            events.forEach(function (name) {
                tablist.addEventListener(name, noteAction, true);
            });

            isBrave().then(function (result) {
                events.forEach(function (name) {
                    tablist.removeEventListener(name, noteAction, true);
                });
                if (result && !hasActed) {
                    tabs.setSelectedTab(braveTab, false);
                }
            });
        }
    });
}
