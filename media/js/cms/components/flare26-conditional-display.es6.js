/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { isUITourEnabled } from './flare26-ui-tour-helpers.es6';

const client = Mozilla.Client;

function initFirefoxVersionConditionalDisplay() {
    const version = client._getFirefoxVersion();
    if (version) {
        document.documentElement.setAttribute('data-firefox-version', version);

        const conditionalEls = document.querySelectorAll(
            '.condition-fx-version'
        );
        conditionalEls.forEach((el) => {
            const minVersion = el.dataset.minVersion;
            const maxVersion = el.dataset.maxVersion;
            const matchInterval =
                minVersion &&
                maxVersion &&
                version >= minVersion &&
                version <= maxVersion;
            const matchMin = minVersion && !maxVersion && version >= minVersion;
            const matchMax = maxVersion && !minVersion && version <= maxVersion;
            if (matchInterval || matchMin || matchMax) {
                el.classList.add('version-match');
            } else {
                el.classList.remove('version-match');
            }
        });
    }
}

function initGeoConditionalDisplay() {
    const countryCode = document.documentElement.dataset.countryCode;
    if (!countryCode) {
        return;
    }

    const conditionalEls = document.querySelectorAll('.condition-geo');
    conditionalEls.forEach((el) => {
        const raw = el.dataset.geoConditions;
        if (!raw) {
            return;
        }
        const conditions = raw
            .split(',')
            .map((c) => c.trim().toUpperCase())
            .filter(Boolean);
        if (conditions.includes(countryCode.toUpperCase())) {
            el.classList.add('geo-match');
        } else {
            el.classList.remove('geo-match');
        }
    });
}

function initDefaultBrowserConditionalDisplay() {
    isUITourEnabled()
        .then(() => {
            Mozilla.UITour.getConfiguration('appinfo', (details) => {
                if (details.defaultBrowser) {
                    document.documentElement.classList.add(
                        'firefox-is-default'
                    );
                } else {
                    document.documentElement.classList.add(
                        'firefox-is-not-default'
                    );
                }
            });
        })
        .catch(() => {
            /* UITour not available */
        });
}

function initAiControlsConditionalDisplay() {
    isUITourEnabled()
        .then(() => {
            Mozilla.UITour.getConfiguration('aiControls', (config) => {
                if (config.default === 'available') {
                    document.documentElement.classList.add(
                        'ai-controls-available'
                    );
                } else {
                    document.documentElement.classList.add(
                        'ai-controls-unavailable'
                    );
                }
            });
        })
        .catch(() => {
            /* UITour not available */
        });
}

export default function setupConditionalDisplay() {
    initFirefoxVersionConditionalDisplay();
    initGeoConditionalDisplay();
    initDefaultBrowserConditionalDisplay();
    initAiControlsConditionalDisplay();
}
