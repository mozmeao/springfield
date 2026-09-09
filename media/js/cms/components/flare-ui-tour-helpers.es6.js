/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export const isUITourEnabled = function (timeout) {
    const delay = timeout || 500;
    return new window.Promise(function (resolve, reject) {
        if (
            !Mozilla ||
            !Mozilla.UITour ||
            typeof Mozilla.UITour.ping !== 'function'
        )
            return reject();
        const timer = window.setTimeout(reject, delay);
        Mozilla.UITour.ping(function () {
            window.clearTimeout(timer);
            resolve();
        });
    });
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;

// `previousSessionEnd` is 0 for a profile with no recorded session, and a future
// timestamp is possible under clock skew — both treated as unavailable, not as 0 days.
export function daysSinceLastSession(config, now) {
    const previousSessionEnd = config.previousSessionEnd;
    if (typeof previousSessionEnd !== 'number' || previousSessionEnd <= 0) {
        return undefined;
    }
    const days = Math.floor((now - previousSessionEnd) / MS_PER_DAY);
    return days < 0 ? undefined : days;
}
