/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { dntEnabled, gpcEnabled } from '../consent/utils.es6';

const Plausible = {};

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

    if (gpcEnabled() || dntEnabled()) {
        return;
    }

    Plausible.loadScript();
};

export default Plausible;
