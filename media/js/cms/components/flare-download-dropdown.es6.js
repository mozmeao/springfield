/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initDownloadDropdown() {
    const dropdownEl = document.querySelector('.fl-platform-dropdown');

    if (dropdownEl) {
        const dropdownButtonEl = document.querySelector(
            '.fl-platform-dropdown-button'
        );
        dropdownButtonEl.addEventListener('click', function () {
            if (dropdownEl.classList.contains('dropdown-is-open')) {
                dropdownEl.classList.remove('dropdown-is-open');
                dropdownButtonEl.setAttribute('aria-expanded', false);
            } else {
                dropdownEl.classList.add('dropdown-is-open');
                dropdownButtonEl.setAttribute('aria-expanded', true);
            }
        });

        dropdownEl.addEventListener('keyup', function (e) {
            if (e.key === 'Escape') {
                dropdownEl.classList.remove('dropdown-is-open');
                dropdownButtonEl.setAttribute('aria-expanded', false);
            }
        });

        window.addEventListener('click', function (e) {
            if (!dropdownEl.contains(e.target)) {
                dropdownEl.classList.remove('dropdown-is-open');
                dropdownButtonEl.setAttribute('aria-expanded', false);
            }
        });
    }
}

export default function setupDownloadDropdown() {
    initDownloadDropdown();
}
