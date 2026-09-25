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
 * A form control named `submit` shadows `HTMLFormElement.submit`, so go through
 * the prototype instead of calling the property off the element.
 *
 * @param {HTMLFormElement} form
 * @returns {void}
 */
function submitNatively(form) {
    HTMLFormElement.prototype.submit.call(form);
}

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
 * @param {EventTarget} target
 * @returns {boolean}
 */
function isContactForm(target) {
    return (
        target instanceof HTMLFormElement &&
        target.closest('.fl-contact-form-wrapper') !== null
    );
}

/**
 * A swapped-in wrapper is brand new, so the role="alert"/role="status" region it
 * carries is not reliably announced: live regions announce changes to a region
 * that already existed. Moving focus into it announces the message and leaves the
 * user at the top of the re-rendered form instead of on <body>.
 *
 * @param {HTMLElement} wrapper
 * @returns {void}
 */
function focusNotification(wrapper) {
    const notification = wrapper.querySelector(
        '[role="alert"]:not(.hidden), [role="status"]'
    );
    if (notification) {
        notification.setAttribute('tabindex', '-1');
        notification.focus();
    }
}

/**
 * @returns {void}
 */
function initAntiBotGate() {
    document.body.addEventListener('htmx:confirm', (event) => {
        const form = event.target;
        // The block's placeholder also fires htmx:confirm when it loads the form.
        if (isContactForm(form) && Date.now() < readyAt) {
            event.preventDefault();
            // htmx already blocked the native submit; submit directly so the
            // bot lands on the decoy action instead of the click doing nothing.
            submitNatively(form);
        }
    });
}

/**
 * @returns {void}
 */
function initErrorFallback() {
    // The request never reached the server, so a real submit cannot send the lead twice.
    // It loses in-progress field values; revisit with an inline error if this gets common.
    document.body.addEventListener('htmx:sendError', (event) => {
        const form = event.target;
        if (isContactForm(form)) {
            form.action = form.getAttribute('hx-post');
            submitNatively(form);
        }
    });
    // The server may already have sent the lead before failing, so resubmitting could
    // send it twice. Tell the visitor instead and keep what they typed.
    document.body.addEventListener('htmx:responseError', (event) => {
        const form = event.target;
        if (isContactForm(form)) {
            const error = form.querySelector('.contact-form-request-error');
            error.classList.remove('hidden');
            error.setAttribute('tabindex', '-1');
            error.focus();
        }
    });
}

/**
 * @returns {void}
 */
export default function setupContactForms() {
    initAntiBotGate();
    initErrorFallback();
    document.body.addEventListener('htmx:afterSwap', (event) => {
        const wrapper = event.target.closest('.fl-contact-form-wrapper');
        if (wrapper) {
            startDocumentDownload(wrapper);
            focusNotification(wrapper);
        }
    });
    initDocumentDownloads();
}
