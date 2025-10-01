/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function init() {
    Mozilla.UITour.ping(() => {
        // show privacy settings CTA
        document.body.classList.add('data-uitour');

        const privacySettingsCta = document.querySelector('#privacy-settings');

        if (typeof window.dataLayer === 'undefined') {
            window.dataLayer = [];
        }

        privacySettingsCta.addEventListener(
            'click',
            (e) => {
                e.preventDefault();

                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'privacy settings',
                    action: 'open',
                    label: 'Manage Your Privacy Settings'
                });

                Mozilla.UITour.openPreferences('privacy');
            },
            false
        );
    });
}

if (
    typeof window.Mozilla.Client !== 'undefined' &&
    typeof window.Mozilla.UITour !== 'undefined' &&
    window.Mozilla.Client.isFirefoxDesktop
) {
    init();
}
