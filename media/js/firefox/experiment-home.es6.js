/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import TrafficCop from '@mozmeao/trafficcop';
import { isApprovedToRun } from '../base/experiment-utils.es6';
import {
    meetsExperimentCriteria,
    experimentCookieID
} from './experiment-meets-criteria.es6';

const href = window.location.href;
if (typeof window.dataLayer === 'undefined') {
    window.dataLayer = [];
}

const experimentName = 'download-privacy';

/**
 * Sets a cookie to remember which experiment variation has been seen.
 * @param {Object} traffic cop config
 */
function setVariationCookie(exp) {
    // set cookie to expire in 24 hours
    const date = new Date();
    date.setTime(date.getTime() + 1 * 24 * 60 * 60 * 1000);
    const expires = date.toUTCString();

    window.Mozilla.Cookies.setItem(
        exp.id,
        exp.chosenVariation,
        expires,
        undefined,
        undefined,
        false,
        'lax'
    );
}

const init = () => {
    if (href.indexOf(`experiment=${experimentName}&variation=control`) !== -1) {
        window.dataLayer.push({
            event: 'experiment_view',
            id: experimentCookieID,
            variant: 'control'
        });
    } else if (
        href.indexOf(`experiment=${experimentName}&variation=treatment`) !== -1
    ) {
        window.dataLayer.push({
            event: 'experiment_view',
            id: experimentCookieID,
            variant: 'treatment'
        });
    } else if (TrafficCop) {
        if (isApprovedToRun()) {
            // TODO: confirm traffic split
            const cop = new TrafficCop({
                id: experimentCookieID,
                variations: {
                    [`experiment=${experimentName}&variation=control`]: 10,
                    [`experiment=${experimentName}&variation=treatment`]: 10
                }
            });
            cop.init();

            setVariationCookie(cop);
        }
    }
};

if (meetsExperimentCriteria()) {
    init();
}
