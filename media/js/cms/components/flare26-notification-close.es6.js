/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initNotificationClose() {
    const closeButtons = document.querySelectorAll('.fl-notification-close');
    closeButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const wrapper = btn.closest('.fl-notification-wrapper');
            if (wrapper) {
                wrapper.remove();
            }
        });
    });
}

export default function setupNotificationClose() {
    initNotificationClose();
}
