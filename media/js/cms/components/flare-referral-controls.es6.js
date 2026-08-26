/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initReferralControls(containerEl) {
    const emailEl = containerEl.querySelector(
        '.fl-referral-controls-share-email'
    );
    const qrEl = containerEl.querySelector('.fl-referral-controls-qr-button');

    const clipboardEl = containerEl.querySelector(
        '[data-js="fl-copy-to-clipboard"]'
    );

    if (clipboardEl) {
        clipboardEl.addEventListener('fl-copy-success', () => {
            if (window.dataLayer) {
                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'referral share',
                    action: 'copy link'
                });
            }
        });
    }

    if (emailEl) {
        emailEl.addEventListener('click', () => {
            if (window.dataLayer) {
                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'referral share',
                    action: 'mailto link'
                });
            }
        });
    }

    if (qrEl) {
        qrEl.addEventListener('click', () => {
            if (window.dataLayer) {
                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'referral share',
                    action: 'qr code modal'
                });
            }
        });
    }
}

export default function setupReferralControls() {
    document
        .querySelectorAll('.fl-referral-controls')
        .forEach(initReferralControls);
}
