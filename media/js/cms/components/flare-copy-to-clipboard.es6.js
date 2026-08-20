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

    let resetTimer = null;

    function showLabel(labelToShow, labelToHide) {
        labelToShow.classList.remove('is-hidden');
        labelToShow.removeAttribute('aria-hidden');
        labelToHide.classList.add('is-hidden');
        labelToHide.setAttribute('aria-hidden', 'true');
    }

    function setCopiedState(isCopied) {
        if (isCopied) {
            showLabel(successLabelEl, labelEl);
        } else {
            showLabel(labelEl, successLabelEl);
        }

        iconDefault.classList.toggle('is-hidden', isCopied);
        iconSuccess.classList.toggle('is-hidden', !isCopied);
        buttonEl.disabled = isCopied;
    }

    buttonEl.addEventListener('click', () => {
        navigator.clipboard.writeText(value).then(() => {
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
