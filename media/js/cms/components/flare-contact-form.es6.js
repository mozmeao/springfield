/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

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

// `window.location` is unforgeable (can't be stubbed via spyOnProperty in a real
// browser), so the redirect is routed through this plain, stubbable object instead.
export const browserNav = {
    /**
     * @param {string} url
     * @returns {void}
     */
    redirectTo(url) {
        window.location.href = url;
    }
};

/**
 * @param {HTMLFormElement} form
 * @param {HTMLElement} wrapper
 * @returns {Promise<void>}
 */
async function handleSubmit(form, wrapper) {
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
    }

    // The real target is parked in data-actn as a decoy against bots that skip JS
    // and submit `form.action` (a dead-end URL) directly; see the 3s gate below.
    const action = form.dataset.actn;

    try {
        const response = await fetch(action, {
            method: 'POST',
            body: new FormData(form)
        });

        if (response.redirected) {
            browserNav.redirectTo(response.url);
            return;
        }

        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('text/html')) {
            throw new Error('Unexpected response content type');
        }

        const doc = new DOMParser().parseFromString(
            await response.text(),
            'text/html'
        );
        const newWrapper = doc.querySelector('.fl-contact-form-wrapper');
        if (!newWrapper) {
            throw new Error('Response carried no form wrapper');
        }

        wrapper.innerHTML = newWrapper.innerHTML;
        wrapper.scrollIntoView({ block: 'start' });
        startDocumentDownload(wrapper);
    } catch (err) {
        // Network error, or a response shape the client-side swap can't
        // handle (e.g. a non-HTML error page). Falling through to a real
        // submit re-triggers the browser's own handling, at the cost of the
        // in-progress field values. A worthwhile trade only while this stays
        // rare; revisit with an inline error message if it doesn't.
        form.action = action;
        form.submit();
    } finally {
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}

/**
 * @returns {void}
 */
function initSubmitHandler() {
    document.addEventListener('submit', (e) => {
        const wrapper = e.target.closest('.fl-contact-form-wrapper');
        if (!wrapper || Date.now() < readyAt) {
            return;
        }
        e.preventDefault();
        handleSubmit(e.target, wrapper);
    });
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
export default function setupContactForms() {
    initSubmitHandler();
    initDocumentDownloads();
}
