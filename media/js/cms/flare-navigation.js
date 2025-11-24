/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';
    const buttonEl = document.querySelector('.fl-hamburger');

    buttonEl.addEventListener('click', function (e) {
        e.preventDefault();
        const mobileNavIsOpen = e.target.classList.contains('is-open');
        const elements = [e.target, document.querySelector('.fl-nav')];

        if (mobileNavIsOpen) {
            elements.forEach(function (el) {
                el.classList.remove('is-open');
            });
            document.body.classList.remove('fl-modal-open');
        } else {
            elements.forEach(function (el) {
                el.classList.add('is-open');
            });
            document.body.classList.add('fl-modal-open');
        }
    });
})();
