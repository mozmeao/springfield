/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

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

export default function setupGeoConditionalDisplay() {
    initGeoConditionalDisplay();
}
