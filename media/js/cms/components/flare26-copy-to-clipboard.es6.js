/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const COPY_RESET_DELAY_MS = 2000;

function initCopyToClipboardButton(buttonEl) {
    const value = buttonEl.dataset.copyValue;
    const labelEl = buttonEl.querySelector('.fl-copy-to-clipboard-label');
    const successLabelEl = buttonEl.querySelector(
        '.fl-copy-to-clipboard-label-success'
    );
    const iconDefault = buttonEl.querySelector(
        '.fl-copy-to-clipboard-icon-default'
    );
    const iconSuccess = buttonEl.querySelector(
        '.fl-copy-to-clipboard-icon-success'
    );

    if (!value || !labelEl || !successLabelEl || !iconDefault || !iconSuccess) {
        return;
    }

    // Lock in the initial rendered width so the button doesn't resize when
    // the label swaps to a shorter success text.
    buttonEl.style.minInlineSize = `${buttonEl.offsetWidth}px`;

    let resetTimer = null;

    function resetButton() {
        labelEl.classList.remove('opacity-0');
        labelEl.removeAttribute('aria-hidden');
        successLabelEl.classList.add('opacity-0');
        successLabelEl.setAttribute('aria-hidden', 'true');
        iconDefault.classList.remove('hidden');
        iconDefault.removeAttribute('aria-hidden');
        iconSuccess.classList.add('hidden');
        buttonEl.disabled = false;
        resetTimer = null;
    }

    buttonEl.addEventListener('click', () => {
        navigator.clipboard.writeText(value).then(() => {
            labelEl.classList.add('opacity-0');
            labelEl.setAttribute('aria-hidden', 'true');
            successLabelEl.classList.remove('opacity-0');
            successLabelEl.removeAttribute('aria-hidden');
            iconDefault.classList.add('hidden');
            iconDefault.setAttribute('aria-hidden', 'true');
            iconSuccess.classList.remove('hidden');
            buttonEl.disabled = true;

            if (resetTimer) {
                clearTimeout(resetTimer);
            }
            resetTimer = setTimeout(resetButton, COPY_RESET_DELAY_MS);
        });
    });
}

export default function setupCopyToClipboardButtons() {
    document.addEventListener('DOMContentLoaded', () => {
        document
            .querySelectorAll('[data-js="fl-copy-to-clipboard"]')
            .forEach(initCopyToClipboardButton);
    });
}
