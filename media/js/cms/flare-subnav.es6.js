/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    // Subnav menu
    const buttonEl = document.querySelector('.fl-subnav-toggle');
    const subnavListEl = document.querySelector('.fl-subnav-list');

    const getLastSubnavLink = () => {
        const subnavLinks = document.querySelectorAll('.fl-subnav-list a');

        if (subnavLinks.length > 0) {
            return subnavLinks[subnavLinks.length - 1];
        }

        return false;
    };

    const handleToggleShiftTab = (event) => {
        if (event.key === 'Tab' && event.shiftKey) {
            closeSubnavList();
        }
    };

    const handleLastLinkTab = (event) => {
        if (event.key === 'Tab' && !event.shiftKey) {
            closeSubnavList();
        }
    };

    const handleOutsideClick = (event) => {
        if (!event.target.closest('.fl-subnav')) {
            closeSubnavList();
        }
    };

    const closeSubnavList = () => {
        // remove unnecessary listeners
        buttonEl.removeEventListener('keydown', handleToggleShiftTab);
        const lastLink = getLastSubnavLink();
        if (lastLink) {
            lastLink.removeEventListener('keydown', handleLastLinkTab);
        }
        document.removeEventListener('click', handleOutsideClick);

        // close subnav list
        buttonEl.setAttribute('aria-expanded', 'false');
    };

    if (buttonEl && subnavListEl) {
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();

            if (e.currentTarget.getAttribute('aria-expanded') === 'true') {
                closeSubnavList();
            } else {
                // open subnav list
                buttonEl.setAttribute('aria-expanded', 'true');

                // close if we tab back from first element
                buttonEl.addEventListener('keydown', handleToggleShiftTab);

                // close if we tab forward from first element
                const lastLink = getLastSubnavLink();
                if (lastLink) {
                    lastLink.addEventListener('keydown', handleLastLinkTab);
                }

                // close with outside click
                document.addEventListener('click', handleOutsideClick);
            }
        });
    }
})();
