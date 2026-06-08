/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export const isUITourEnabled = function (timeout) {
    const delay = timeout || 500;
    return new window.Promise(function (resolve, reject) {
        const timer = window.setTimeout(reject, delay);
        Mozilla.UITour.ping(function () {
            window.clearTimeout(timer);
            resolve();
        });
    });
};
