/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { isUITourEnabled } from './flare26-ui-tour-helpers.es6';

class SetAsDefaultComponent {
    constructor() {
        this.checkTimer = undefined;
    }

    isDefaultBrowser() {
        return isUITourEnabled().then(() => {
            return new window.Promise((resolve, reject) => {
                Mozilla.UITour.getConfiguration('appinfo', (details) => {
                    if (details.defaultBrowser) {
                        resolve();
                    } else {
                        reject(details.canSetDefaultBrowserInBackground);
                    }
                });
            });
        });
    }

    trySetDefaultBrowser() {
        Mozilla.UITour.setConfiguration('defaultBrowser');
        this.checkForDefaultSwitch();
    }

    onDefaultSwitch() {
        document
            .querySelector('html')
            .classList.remove('firefox-is-not-default');
        document.querySelector('html').classList.add('firefox-is-default');
        window.dataLayer.push({ event: 'default_browser_set' });
        window.dataLayer.push({
            event: 'dimension_set',
            firefox_is_default: true
        });
    }

    checkForDefaultSwitch() {
        this.isDefaultBrowser()
            .then(() => {
                this.onDefaultSwitch();
                clearInterval(this.checkTimer);
            })
            .catch(() => {
                if (!this.checkTimer) {
                    window.setTimeout(() => {
                        this.checkTimer = setInterval(
                            () => this.checkForDefaultSwitch(),
                            1000
                        );
                    }, 1500);
                }
            });
    }

    onLoad() {
        const buttons = document.querySelectorAll('.fl-set-as-default-button');
        if (!buttons.length) return;

        let hasValidTrigger = false;

        buttons.forEach((btn) => {
            const targetId = btn.getAttribute('data-target-id');
            const dialog = targetId ? document.getElementById(targetId) : null;
            if (!dialog) return;

            hasValidTrigger = true;
            btn.addEventListener('click', () => this.trySetDefaultBrowser());
        });

        if (!hasValidTrigger) return;

        this.isDefaultBrowser()
            .then(() => {
                document
                    .querySelector('html')
                    .classList.add('firefox-is-default');
                window.dataLayer.push({
                    event: 'dimension_set',
                    firefox_is_default: true
                });
            })
            .catch(() => {
                document
                    .querySelector('html')
                    .classList.add('firefox-is-not-default');
                window.dataLayer.push({
                    event: 'dimension_set',
                    firefox_is_default: false
                });
            });
    }
}

export const setupSetAsDefault = () => new SetAsDefaultComponent().onLoad();
