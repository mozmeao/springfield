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
            const mobileSubnavIsOpen =
                e.currentTarget.classList.contains('is-open');
            const elements = [e.currentTarget, subnavListEl];

            if (mobileSubnavIsOpen) {
                elements.forEach(function (el) {
                    el.classList.remove('is-open');
                });
                document.body.classList.remove('fl-modal-open');
                subnavListEl.removeAttribute('role');
                subnavListEl.removeAttribute('aria-modal');
                trap.deactivate();
            } else {
                elements.forEach(function (el) {
                    el.classList.add('is-open');
                });
                document.body.classList.add('fl-modal-open');
                subnavListEl.setAttribute('role', 'dialog');
                subnavListEl.setAttribute('aria-modal', 'true');
                trap.activate();
            }
        });
    }
})();
