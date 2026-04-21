/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { getConsentCookie } from '../../base/consent/utils.es6';

function initQRCodeSnippet() {
    const COOKIE_ID = 'moz-qr-snippet-dismissed';
    const qrCodeSnippetEl = document.querySelector('.fl-qr-code-snippet');

    if (!qrCodeSnippetEl) {
        return;
    }

    const cookiesEnabled =
        typeof window.Mozilla.Cookies !== 'undefined' &&
        window.Mozilla.Cookies.enabled();

    // Don't show if previously dismissed.
    if (cookiesEnabled && Mozilla.Cookies.hasItem(COOKIE_ID)) {
        return;
    }

    const closeButton = qrCodeSnippetEl.querySelector(
        '.fl-qr-code-snippet-close'
    );

    qrCodeSnippetEl.setAttribute('aria-live', 'polite');

    setTimeout(function () {
        qrCodeSnippetEl.classList.add('is-open');
    }, 3000);

    if (qrCodeSnippetEl.classList.contains('fl-qr-code-snippet-closable')) {
        if (closeButton) {
            closeButton.addEventListener('click', function () {
                qrCodeSnippetEl.classList.remove('is-open');

                if (!cookiesEnabled) {
                    return;
                }

                /**
                 * Set a preference cookie to remember the user dismissed
                 * the QR code snippet. Legal are OK to set this without
                 * explicit consent because:
                 *
                 * 1) The cookie is not used for tracking purposes.
                 * 2) The cookie is set only after an explicit user action.
                 *
                 * We still honor not setting this cookie if preference
                 * cookies have been explicitly rejected by the user.
                 */
                const cookie = getConsentCookie();
                if (cookie && !cookie.preference) {
                    return;
                }

                const date = new Date();
                const cookieDuration = 24 * 60 * 60 * 1000; // 24 hours
                date.setTime(date.getTime() + cookieDuration);
                Mozilla.Cookies.setItem(
                    COOKIE_ID,
                    true,
                    date.toUTCString(),
                    '/',
                    undefined,
                    false,
                    'lax'
                );
            });
        }
    }
}

export default function setupQRCodeSnippet() {
    initQRCodeSnippet();
}
