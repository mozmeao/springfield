/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Smart Window page logic for supported countries.
 * Detects Firefox Desktop vs other browsers and shows the appropriate CTA:
 * - Firefox Desktop: "Enable Smart Window" button that triggers UITour FxA sign-in
 * - Non-Firefox: "Download Firefox" button with attribution
 */

const stateFirefox = document.getElementById('state-firefox');
const stateNonFirefox = document.getElementById('state-non-firefox');

if (
    typeof window.Mozilla !== 'undefined' &&
    typeof window.Mozilla.Client !== 'undefined' &&
    window.Mozilla.Client.isFirefoxDesktop
) {
    // Firefox Desktop: show UITour CTA
    stateFirefox.hidden = false;

    const ctaButton = document.getElementById('smart-window-cta');
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
} else {
    // Non-Firefox: show download CTA
    stateNonFirefox.hidden = false;

    const downloadButton = document.getElementById('smart-window-download');
    if (downloadButton) {
        downloadButton.addEventListener('click', () => {
            if (window.dataLayer) {
                window.dataLayer.push({
                    event: 'smart_window_download',
                    cta_type: 'download'
                });
            }
        });
    }
}
