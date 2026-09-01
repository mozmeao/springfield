/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { getConsentCookie } from '../../base/consent/utils.es6';

const COOKIE_ID = 'moz-qr-snippet-dismissed';
const DEFAULT_OPEN_DELAY_MS = 3000;

/**
 * Reflect the open/closed state: swap the (decorative, aria-hidden) +/- icon
 * and set `aria-expanded` on the toggle button. The button keeps a stable
 * accessible name via `aria-labelledby`, so state is conveyed by
 * `aria-expanded` alone.
 */
function setToggleState(snippetEl, isOpen) {
    const icon = snippetEl.querySelector(
        isOpen ? '.fl-icon-add' : '.fl-icon-subtract'
    );

    if (icon) {
        icon.classList.remove(isOpen ? 'fl-icon-add' : 'fl-icon-subtract');
        icon.classList.add(isOpen ? 'fl-icon-subtract' : 'fl-icon-add');
    }

    const button = snippetEl.querySelector('.fl-qr-code-snippet-close');

    if (button) {
        button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }
}

function openSnippet(snippetEl) {
    if (snippetEl.classList.contains('is-open')) {
        return;
    }
    setToggleState(snippetEl, true);
    snippetEl.classList.add('is-open');
}

function closeSnippet(snippetEl) {
    if (!snippetEl.classList.contains('is-open')) {
        return;
    }
    setToggleState(snippetEl, false);
    snippetEl.classList.remove('is-open');
}

function dismiss(cookiesEnabled) {
    if (!cookiesEnabled) {
        return;
    }

    /**
     * Set a preference cookie to remember the user dismissed the QR code
     * snippet. Legal are OK to set this without explicit consent because:
     *
     * 1) The cookie is not used for tracking purposes.
     * 2) The cookie is set only after an explicit user action.
     *
     * We still honor not setting this cookie if preference cookies have been
     * explicitly rejected by the user.
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
}

function initQRCodeSnippet() {
    const oldSnippet = document.querySelector('.js-qr-code-snippet');

    const qrCodeSnippetEl =
        document.querySelector('.js-qr-code-floating-snippet') || oldSnippet;

    if (!qrCodeSnippetEl) {
        return;
    }

    const cookiesEnabled =
        typeof window.Mozilla.Cookies !== 'undefined' &&
        window.Mozilla.Cookies.enabled();

    // Don't show if previously dismissed.
    const wasDismissed = cookiesEnabled && Mozilla.Cookies.hasItem(COOKIE_ID);

    if (wasDismissed && oldSnippet) {
        return;
    }

    if (wasDismissed) {
        closeSnippet(qrCodeSnippetEl);
    }

    const showHideButton = qrCodeSnippetEl.querySelector(
        '.fl-qr-code-snippet-close'
    );

    // First-generation snippet: always auto-opens after a fixed delay.
    let autoOpenTimer;
    if (oldSnippet) {
        autoOpenTimer = setTimeout(function () {
            qrCodeSnippetEl.classList.add('is-open');
        }, DEFAULT_OPEN_DELAY_MS);
    } else if (
        qrCodeSnippetEl.dataset.openBehavior === 'delayed' &&
        !wasDismissed
    ) {
        // Floating snippet set to "closed, then opens automatically".
        const parsed = parseInt(qrCodeSnippetEl.dataset.openDelay, 10);
        const delay = Number.isFinite(parsed) ? parsed : DEFAULT_OPEN_DELAY_MS;
        autoOpenTimer = setTimeout(function () {
            openSnippet(qrCodeSnippetEl);
        }, delay);
    }

    if (qrCodeSnippetEl.classList.contains('fl-qr-code-snippet-closable')) {
        if (showHideButton) {
            qrCodeSnippetEl.addEventListener('click', function () {
                clearTimeout(autoOpenTimer);
                openSnippet(qrCodeSnippetEl);
            });
            showHideButton.addEventListener('click', function (e) {
                e.stopPropagation();
                clearTimeout(autoOpenTimer);
                if (qrCodeSnippetEl.classList.contains('is-open')) {
                    closeSnippet(qrCodeSnippetEl);
                    dismiss(cookiesEnabled);
                } else {
                    openSnippet(qrCodeSnippetEl);
                }
            });
        }
    }
}

export default function setupQRCodeSnippet() {
    initQRCodeSnippet();
}
