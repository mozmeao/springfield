/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

export function initDialogs() {
    const triggerButtons = document.querySelectorAll('.fl-dialog-trigger');

    if (triggerButtons.length) {
        triggerButtons.forEach(function (buttonEl) {
            const dialogEl = document.getElementById(buttonEl.dataset.targetId);

            if (dialogEl) {
                buttonEl.addEventListener('click', function () {
                    dialogEl.showModal();
                });
                const closeButtonEl = dialogEl.querySelector(
                    '.fl-dialog-close-button'
                );
                if (closeButtonEl) {
                    closeButtonEl.addEventListener('click', function () {
                        dialogEl.close();
                    });
                }
            }
        });
    }
}

export default function setupDialogs() {
    initDialogs();
}
