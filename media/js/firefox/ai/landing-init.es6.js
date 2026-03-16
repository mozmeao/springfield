/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

if (
    typeof window.Mozilla !== 'undefined' &&
    typeof window.Mozilla.Client !== 'undefined' &&
    window.Mozilla.Client.isFirefoxDesktop
) {
    const ctaButton = document.getElementById('js-uitour-show-account');
    ctaButton.addEventListener('click', (e) => {
        e.preventDefault();

        if (
            typeof window.Mozilla.UITour !== 'undefined' &&
            typeof window.Mozilla.UITour.showFirefoxAccountsForAIWindow ===
                'function'
        ) {
            window.Mozilla.UITour.showFirefoxAccountsForAIWindow();
        }

        if (window.dataLayer) {
            window.dataLayer.push({
                event: 'smart_window_enable',
                cta_type: 'uitour'
            });
        }
    });
}
// TODO: Else ensure expected campaign is associated with download
