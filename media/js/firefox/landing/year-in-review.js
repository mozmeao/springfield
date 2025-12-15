/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';

    function isDefaultBrowser() {
        return new window.Promise(function (resolve, reject) {
            Mozilla.UITour.getConfiguration('appinfo', function (details) {
                if (details.defaultBrowser) {
                    resolve();
                } else {
                    reject();
                }
            });
        });
    }

    function isSupported() {
        return Mozilla.Client.isFirefoxDesktop && 'Promise' in window;
    }

    function onLoad() {
        if (!isSupported()) {
            // Add check-finished class even when not supported
            document.querySelector('main').classList.add('check-finished');
            return;
        }

        /**
         * Check to see if Firefox is the default browser.
         * If true show a success message.
         * If false prompt to switch the default browser.
         */
        isDefaultBrowser()
            .then(function () {
                document
                    .querySelector('main')
                    .classList.add('is-firefox-default');
            })
            .catch(function () {
                // error
            })
            .finally(function () {
                document.querySelector('main').classList.add('check-finished');
            });
    }

    Mozilla.run(onLoad);
})(window.Mozilla);
