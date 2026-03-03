/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    // Subnav menu
    const buttonEl = document.querySelector('.fl-subnav-toggle');
    const subnavListEl = document.querySelector('.fl-subnav-list');

    const handleKeyboardNavigation = () => {
        // close if we tab back from first element
        buttonEl.addEventListener('keydown', function (event) {
            if (event.key === 'Tab' && event.shiftKey) {
                buttonEl.setAttribute('aria-expanded', 'false');
            }
        });

        const subnavLinks = document.querySelectorAll('.fl-subnav-list a');

        if (subnavLinks.length > 0) {
            // close if we tab forward from last element
            subnavLinks[subnavLinks.length - 1].addEventListener(
                'keydown',
                function (event) {
                    if (event.key === 'Tab' && !event.shiftKey) {
                        buttonEl.setAttribute('aria-expanded', 'false');
                    }
                }
            );
        }
    };

    if (buttonEl && subnavListEl) {
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();

            if (e.currentTarget.getAttribute('aria-expanded') === 'true') {
                buttonEl.setAttribute('aria-expanded', 'false');
            } else {
                buttonEl.setAttribute('aria-expanded', 'true');

                handleKeyboardNavigation();
            }
        });
    }
})();
