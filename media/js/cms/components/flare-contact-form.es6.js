/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// htmx (hx-post etc. on the form, see cms/includes/contact-form.html) handles the
// request/swap/scroll. This covers what htmx can't express under our CSP or has no attribute for.

// Submits are ignored until this time passes, so a bot that fires the
// request immediately on page load still hits the decoy form action.
const readyAt = Date.now() + 3000;

/**
 * @param {HTMLElement} wrapper
 * @returns {void}
 */
function startDocumentDownload(wrapper) {
    const link = wrapper.querySelector('.contact-form-download');
    if (link) {
        link.click();
        link.classList.add('hidden');
    }
}

/**
 * @returns {void}
 */
function initDocumentDownloads() {
    document
        .querySelectorAll('.fl-contact-form-wrapper')
        .forEach(startDocumentDownload);
}

/**
 * @returns {void}
 */
function initAntiBotGate() {
    document.body.addEventListener('htmx:confirm', (e) => {
        const form = e.target;
        if (form.closest('.fl-contact-form-wrapper') && Date.now() < readyAt) {
            e.preventDefault();
            // htmx already blocked the native submit; call submit() directly so the
            // bot lands on the decoy action instead of the click doing nothing.
            form.submit();
        }
    });
}

/**
 * @returns {void}
 */
function initErrorFallback() {
    // Network error or an unswappable response (e.g. stale-CSRF 403). Falls through to a
    // real submit, losing in-progress field values; revisit with an inline error if this gets common.
    const fallback = (e) => {
        const form = e.target;
        form.action = form.getAttribute('hx-post');
        form.submit();
    };
    document.body.addEventListener('htmx:sendError', fallback);
    document.body.addEventListener('htmx:responseError', fallback);
}

/**
 * @returns {void}
 */
export default function setupContactForms() {
    initAntiBotGate();
    initErrorFallback();
    document.body.addEventListener('htmx:afterSwap', (e) => {
        const wrapper = e.target.closest('.fl-contact-form-wrapper');
        if (wrapper) {
            startDocumentDownload(wrapper);
        }
    });
    initDocumentDownloads();
}
