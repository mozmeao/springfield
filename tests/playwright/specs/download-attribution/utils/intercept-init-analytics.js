/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

/**
 * Intercepts Mozilla.DownloadAttribution.initAnalytics before page scripts run
 * so tests can assert whether it was called.
 *
 * Optionally mocks dntEnabled or gpcEnabled on the Mozilla namespace to simulate
 * denial signals.
 *
 * Pass to page.addInitScript() before navigation.
 * @param {Object} options
 * @param {Boolean} options.mockDNT
 * @param {Boolean} options.mockGPC
 */
function interceptInitAnalytics({ mockDNT = false, mockGPC = false } = {}) {
    window.__initAnalyticsCalled = false;
    let _daValue;
    const _mozilla = {};

    if (mockDNT) {
        Object.defineProperty(_mozilla, 'dntEnabled', {
            configurable: true,
            get() {
                return () => true;
            }
        });
    }

    if (mockGPC) {
        Object.defineProperty(_mozilla, 'gpcEnabled', {
            configurable: true,
            get() {
                return () => true;
            }
        });
    }

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
            if (val && typeof val.initAnalytics === 'function') {
                const orig = val.initAnalytics;
                val.initAnalytics = function (...args) {
                    window.__initAnalyticsCalled = true;
                    return orig.apply(this, args);
                };
            }
            _daValue = val;
        }
    });
}

module.exports = interceptInitAnalytics;
