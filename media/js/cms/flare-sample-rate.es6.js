/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { isApprovedToRun } from '../base/experiment-utils.es6';

/**
 * Reads the sample rate a Conditional Display block set on this page.
 * CMS enforces using the same sample rate for the entire page
 * @return {Number} percentage between 0 and 100; 0 if no rate is set.
 */
function getSampleRate() {
    const rate = document.documentElement.dataset.experimentSampleRate;
    return isNaN(rate) || !rate
        ? 0
        : Math.min(Math.max(parseFloat(rate), 0), 100);
}

/**
 * Rolls a single random number and checks it against the given sample rate.
 * Every sample-rated Conditional Display block on the page shares this number.
 * @param {Number} rate - percentage between 0 and 100.
 * @return {Boolean}
 */
function withinSampleRate(rate) {
    return Math.random() * 100 < rate;
}

/**
 * Reveals this page's sample-rated Conditional Display blocks for a random
 * percentage of eligible visitors, and logs a GA4 experiment_view event for
 * the ones who see them.
 */
function initSampleRate() {
    const rate = getSampleRate();
    if (!rate || !isApprovedToRun()) {
        return;
    }

    if (withinSampleRate(rate)) {
        document.documentElement.classList.add('in-experiment-sample');

        if (typeof window.dataLayer === 'undefined') {
            window.dataLayer = [];
        }
        window.dataLayer.push({
            event: 'experiment_view',
            id: document.documentElement.dataset.experimentId,
            variant: 'in-sample'
        });
    }
}

export { getSampleRate, withinSampleRate, initSampleRate };
