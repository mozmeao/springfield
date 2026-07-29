/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initDropdown(dropdownEl) {
    const triggerEl = dropdownEl.querySelector('.fl-dropdown-trigger');
    const panelEl = dropdownEl.querySelector('.fl-dropdown-panel');
    if (!triggerEl || !panelEl) return;

    triggerEl.setAttribute('aria-expanded', 'false');
    panelEl.setAttribute('aria-hidden', 'true');

    function open() {
        dropdownEl.classList.add('fl-is-open');
        triggerEl.setAttribute('aria-expanded', 'true');
        panelEl.setAttribute('aria-hidden', 'false');
    }

    function close() {
        dropdownEl.classList.remove('fl-is-open');
        triggerEl.setAttribute('aria-expanded', 'false');
        panelEl.setAttribute('aria-hidden', 'true');
    }

    triggerEl.addEventListener('click', () => {
        dropdownEl.classList.contains('fl-is-open') ? close() : open();
    });

    dropdownEl.addEventListener('keyup', (e) => {
        if (e.key === 'Escape') {
            close();
            triggerEl.focus();
        }
    });

    window.addEventListener('click', (e) => {
        if (!dropdownEl.contains(e.target)) {
            close();
        }
    });
}

export function init(selector = '.fl-dropdown') {
    document.querySelectorAll(selector).forEach(initDropdown);
}

export default function setupFlareDropdown() {
    init();
}
