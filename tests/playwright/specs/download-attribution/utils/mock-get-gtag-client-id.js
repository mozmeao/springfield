/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * Intercepts Mozilla.DownloadAttribution.getGtagClientID before page scripts
 * run so it returns a fixed GA4 client ID without triggering real GA4 network
 * calls.
 *
 * Pass to page.addInitScript() before navigation.
 */
function mockGetGtagClientID() {
    let _daValue;
    const _mozilla = {};

    Object.defineProperty(window, 'Mozilla', {
        configurable: true,
        enumerable: true,
        get() {
            return _mozilla;
        },
        set(val) {
            if (val && typeof val === 'object') {
                Object.assign(_mozilla, val);
            }
        }
    });

    Object.defineProperty(_mozilla, 'DownloadAttribution', {
        configurable: true,
        enumerable: true,
        get() {
            return _daValue;
        },
        set(val) {
            if (val && typeof val === 'object') {
                val.getGtagClientID = () => 'mocked-ga4-client-id';
            }
            _daValue = val;
        }
    });
}

module.exports = mockGetGtagClientID;
