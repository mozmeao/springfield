/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { dntEnabled, getConsentCookie, gpcEnabled } from '../consent/utils.es6';

const Plausible = {};

/**
 * Determines if the visitor has opted out of analytics, via GPC, DNT, or by
 * explicitly declining analytics in the consent banner.
 * @returns {Boolean}
 */
Plausible.analyticsDenied = () => {
    if (gpcEnabled() || dntEnabled()) {
        return true;
    }

    const consent = getConsentCookie();
    return !!consent && consent.analytics === false;
};

Plausible.defineQueueStub = () => {
    window.plausible =
        window.plausible ||
        function () {
            (window.plausible.q = window.plausible.q || []).push(arguments);
        };
};

Plausible.loadScript = () => {
    const html = document.getElementsByTagName('html')[0];
    const domain = html.getAttribute('data-plausible-domain');
    const src = html.getAttribute('data-plausible-src');

    if (!domain || !src) {
        return;
    }

    const script = document.createElement('script');
    script.defer = true;
    script.setAttribute('data-domain', domain);
    script.src = src;
    document.head.appendChild(script);
};

Plausible.init = () => {
    Plausible.defineQueueStub();

    if (Plausible.analyticsDenied()) {
        return;
    }

    Plausible.loadScript();
};

/**
 * Send a custom event to Plausible. No-ops when Plausible isn't loaded or the visitor has opted out.
 * @param {String} name - the custom event name (e.g. 'product_download')
 * @param {Object} [props] - optional custom properties
 */
Plausible.trackEvent = (name, props) => {
    if (typeof window.plausible !== 'function') {
        return;
    }

    if (gpcEnabled() || dntEnabled()) {
        return;
    }

    if (props) {
        window.plausible(name, { props: props });
    } else {
        window.plausible(name);
    }
};

export default Plausible;
