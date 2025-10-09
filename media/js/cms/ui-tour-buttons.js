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

        // Find any buttons that should open about:preferences to any of the panes.
        const openPreferencesButtons = document.querySelectorAll('[class*="ui-tour-open-about-preferences"]');
        // Clicking any of the openPreferencesButtons should open the about:preferences to a
        // particular pane (if no specific pane is specified, then open without specifying a pane).
        openPreferencesButtons.forEach((button) => {
            button.addEventListener(
                'click',
                (e) => {
                    e.preventDefault();

                    // Find the class that starts with "ui-tour-open-about-preferences-"
                    const classList = Array.from(button.classList);
                    const preferencesClass = classList.find(cls => cls.startsWith('ui-tour-open-about-preferences-'));
                    // Extract the pane name (the part after "ui-tour-open-about-preferences-")
                    const pane = preferencesClass ? preferencesClass.replace('ui-tour-open-about-preferences-', '') : null;
                    // Open preferences to the relevant pane.
                    if (pane === null) {
                        Mozilla.UITour.openPreferences();
                    } else {
                        Mozilla.UITour.openPreferences(pane);
                    }
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