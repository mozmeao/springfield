/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    hasConsentCookie,
    getConsentCookie,
    consentRequired
} from '../base/consent/utils.es6';

const experimentCookieID = 'moz-exp-download-privacy';

function meetsExperimentCriteria() {
    if (!window.site.fxSupported) {
        // Don't enter into experiment if visitor is on unsupported version
        return false;
    } else if (!Mozilla.Cookies.enabled()) {
        // Don't enter into experiment if cookies are disabled.
        return false;
    } else if (hasConsentCookie()) {
        const cookie = getConsentCookie();
        // Don't enter into experiment if visitor has previously rejected analytics.
        if (!cookie.analytics) {
            return false;
        }
    } else if (consentRequired()) {
        // Don't enter into experiment if consent required and not explicitly given by cookie
        return false;
    } else if (
        (Mozilla.Cookies.hasItem('moz-stub-attribution-code') ||
            Mozilla.Cookies.hasItem('moz-stub-attribution-sig')) &&
        !Mozilla.Cookies.hasItem(experimentCookieID)
    ) {
        // Don't enter into experiment if we already have an attribution cookie
        return false;
    }

    return true;
}

export { meetsExperimentCriteria, experimentCookieID };
