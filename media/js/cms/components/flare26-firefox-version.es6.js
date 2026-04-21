/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

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
            let show = false;
            if (parseFloat(minVersion) && version >= parseFloat(minVersion)) {
                show = true;
            }
            if (parseFloat(maxVersion) && version <= parseFloat(maxVersion)) {
                show = true;
            }
            if (show) {
                el.classList.add('version-match');
            } else {
                el.classList.remove('version-match');
            }
        });
    }
}

export default function setupFirefoxVersionConditionalDisplay() {
    document.addEventListener('DOMContentLoaded', () => {
        initFirefoxVersionConditionalDisplay();
    });
}
