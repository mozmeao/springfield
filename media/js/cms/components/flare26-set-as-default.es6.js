/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { isUITourEnabled } from './flare26-ui-tour-helpers.es6';

const setAsDefaultPage = {
    checkTimer: undefined,
    isDefaultBrowser() {
        return isUITourEnabled().then(function () {
            return new window.Promise(function (resolve, reject) {
                Mozilla.UITour.getConfiguration('appinfo', function (details) {
                    if (details.defaultBrowser) {
                        resolve();
                    } else {
                        reject(details.canSetDefaultBrowserInBackground);
                    }
                });
            });
        });
    },
    trySetDefaultBrowser() {
        Mozilla.UITour.setConfiguration('defaultBrowser');
        setAsDefaultPage.checkForDefaultSwitch();
    },
    onDefaultSwitch() {
        document
            .querySelector('html')
            .classList.remove('firefox-is-not-default');
        document.querySelector('html').classList.add('firefox-is-default');
        // GA4
        window.dataLayer.push({
            event: 'default_browser_set'
        });
        window.dataLayer.push({
            event: 'dimension_set',
            firefox_is_default: true
        });
    },
    checkForDefaultSwitch() {
        setAsDefaultPage
            .isDefaultBrowser()
            .then(function () {
                setAsDefaultPage.onDefaultSwitch();
                clearInterval(setAsDefaultPage.checkTimer);
            })
            .catch(function () {
                if (!setAsDefaultPage.checkTimer) {
                    window.setTimeout(function () {
                        setAsDefaultPage.checkTimer = setInterval(
                            setAsDefaultPage.checkForDefaultSwitch,
                            1000
                        );
                    }, 1500);
                }
            });
    },
    onLoad() {
        const setAsDefaultButtonEls = document.querySelectorAll(
            '.fl-set-as-default-button'
        );

        if (!setAsDefaultButtonEls.length) return;

        let hasValidSetAsDefaultTrigger = false;

        setAsDefaultButtonEls.forEach((setAsDefaultButtonEl) => {
            const targetId =
                setAsDefaultButtonEl.getAttribute('data-target-id');
            const setAsDefaultDialogEl = targetId
                ? document.getElementById(targetId)
                : null;
            if (!setAsDefaultDialogEl) {
                return;
            }
            hasValidSetAsDefaultTrigger = true;
            setAsDefaultButtonEl.addEventListener('click', () => {
                setAsDefaultPage.trySetDefaultBrowser();
            });
        });

        if (!hasValidSetAsDefaultTrigger) {
            return;
        }

        setAsDefaultPage
            .isDefaultBrowser()
            .then(function () {
                document
                    .querySelector('html')
                    .classList.add('firefox-is-default');
                // GA4
                window.dataLayer.push({
                    event: 'dimension_set',
                    firefox_is_default: true
                });
            })
            .catch(function () {
                document
                    .querySelector('html')
                    .classList.add('firefox-is-not-default');

                // GA4
                window.dataLayer.push({
                    event: 'dimension_set',
                    firefox_is_default: false
                });
            });
    }
};

export const setupSetAsDefault = function () {
    setAsDefaultPage.onLoad();
};
