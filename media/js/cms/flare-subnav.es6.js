/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
import { createFocusTrap } from 'focus-trap';

(function () {
    // Subnav menu
    const buttonEl = document.querySelector('.fl-subnav-toggle');
    const subnavListEl = document.querySelector('.fl-subnav-list');
    const trap = createFocusTrap(subnavListEl, {
        allowOutsideClick: true
    });

    if (buttonEl && subnavListEl) {
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();

            if (e.currentTarget.getAttribute('aria-expanded') === 'true') {
                buttonEl.setAttribute('aria-expanded', 'false');
                trap.deactivate();
            } else {
                buttonEl.setAttribute('aria-expanded', 'true');
                trap.activate();
            }
        });
    }
})();
