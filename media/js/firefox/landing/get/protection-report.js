/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
    protection report button
    - check for support
    - add listener, enable, and show button
*/
(function (Mozilla) {
    'use strict';

    var client = Mozilla.Client;

    function handleOpenProtectionReport(e) {
        e.preventDefault();

        // GA4
        window.dataLayer.push({
            event: 'widget_action',
            type: 'protection report',
            action: 'open',
            label: 'See your protection report'
        });

        Mozilla.UITour.showProtectionReport();
    }

    if (client.isFirefoxDesktop) {
        if (client._getFirefoxMajorVersion() >= 136) {
            // show "See what Firefox has blocked for you" links.
            document
                .querySelector('body')
                .classList.add('data-uitour');

            // Intercept link clicks to open about:protections page using UITour.
            Mozilla.UITour.ping(function () {
                document
                    .getElementById('protection-report')
                    .addEventListener(
                        'click',
                        handleOpenProtectionReport,
                        false
                    );
            });
        }
    }
})(window.Mozilla);
