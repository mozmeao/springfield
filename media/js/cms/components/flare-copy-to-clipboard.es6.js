/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const COPY_RESET_DELAY_MS = 2000;

function initCopyToClipboardButton(buttonEl) {
    const value = buttonEl.dataset.copyValue;
    const successMessage = buttonEl.dataset.labelSuccess;
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
    const statusEl = buttonEl.nextElementSibling;
    const hasStatusRegion =
        statusEl && statusEl.classList.contains('fl-copy-to-clipboard-status');

    if (
        !value ||
        !labelEl ||
        !successLabelEl ||
        !iconDefault ||
        !iconSuccess ||
        !hasStatusRegion
    ) {
        return;
    }

    let resetTimer = null;

    function setCopiedState(isCopied) {
        labelEl.classList.toggle('hidden', isCopied);
        successLabelEl.classList.toggle('hidden', !isCopied);
        iconDefault.classList.toggle('hidden', isCopied);
        iconSuccess.classList.toggle('hidden', !isCopied);
        buttonEl.classList.toggle('is-copied', isCopied);
        // Cleared on reset so a virtual cursor doesn't land on a stale message.
        statusEl.textContent = isCopied ? successMessage : '';
    }

    buttonEl.addEventListener('click', () => {
        navigator.clipboard.writeText(value).then(() => {
            buttonEl.dispatchEvent(
                new CustomEvent('fl-copy-success', { bubbles: true })
            );

            if (window.dataLayer) {
                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'copy to clipboard',
                    action: 'copy',
                    text: labelEl.textContent
                });
            }

            setCopiedState(true);

            clearTimeout(resetTimer);
            resetTimer = setTimeout(
                () => setCopiedState(false),
                COPY_RESET_DELAY_MS
            );
        });
    });
}

export default function setupCopyToClipboardButtons() {
    document
        .querySelectorAll('[data-js="fl-copy-to-clipboard"]')
        .forEach(initCopyToClipboardButton);
}
