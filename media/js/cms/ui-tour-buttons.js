/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function init() {
    Mozilla.UITour.ping(() => {
        // Find any buttons that should open a new tab.
        const openNewTabButtons = document.querySelectorAll('.ui-tour-open-new-tab');
        // Clicking any of the openNewTabButtons should open a new tab.
        openNewTabButtons.forEach((button) => {
            button.addEventListener(
                'click',
                (e) => {
                    e.preventDefault();

                    Mozilla.UITour.showNewTab();
                },
                false
            );
        });
    });
}

function hideUITourElements() {
    const uiTourElements = document.querySelectorAll('.ui-tour');
    uiTourElements.forEach((element) => {
        element.style.display = "none";
    });
}

if (
    typeof window.Mozilla.Client !== 'undefined' &&
    typeof window.Mozilla.UITour !== 'undefined' &&
    window.Mozilla.Client.isFirefoxDesktop
) {
    init();
} else {
    hideUITourElements();
}