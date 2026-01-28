/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function init() {
    'use strict';
    Mozilla.UITour.ping(() => {
        // Find any buttons that should open a new tab.
        const openNewTabButtons = document.querySelectorAll(
            '.ui-tour-open-new-tab'
        );
        // Clicking any of the openNewTabButtons should open a new tab.
        openNewTabButtons.forEach((button) => {
            // Add an event listener to the button.
            button.addEventListener(
                'click',
                (e) => {
                    e.preventDefault();

                    Mozilla.UITour.showNewTab();
                },
                false
            );

            // If the button exists in a .fl-card element with an .expand-link class,
            // then the link is meant to expand to the entire .fl-card, so we add
            // the same event listener to the .fl-card.expand-link element.
            // TODO: remove the alternative class name when 2025 designs are fully rolled out.
            let card = button.closest('.fl-card.expand-link');
            if (!card) {
                card = button.closest('.fl-card-expand-link');
            }
            if (card) {
                card.addEventListener(
                    'click',
                    (e) => {
                        e.preventDefault();

                        Mozilla.UITour.showNewTab();
                    },
                    false
                );
            }
        });

        // Find any buttons that should open about:preferences to any of the panes.
        const openPreferencesButtons = document.querySelectorAll(
            '[class*="ui-tour-open-about-preferences"]'
        );
        // Clicking any of the openPreferencesButtons should open the about:preferences to a
        // particular pane (if no specific pane is specified, then open without specifying a pane).
        openPreferencesButtons.forEach((button) => {
            // Find the class that starts with "ui-tour-open-about-preferences-"
            const classList = Array.from(button.classList);
            const preferencesClass = classList.find((cls) =>
                cls.startsWith('ui-tour-open-about-preferences-')
            );
            // Extract the pane name (the part after "ui-tour-open-about-preferences-")
            const pane = preferencesClass
                ? preferencesClass.replace(
                      'ui-tour-open-about-preferences-',
                      ''
                  )
                : null;

            // Add an event listener to the button.
            button.addEventListener(
                'click',
                (e) => {
                    e.preventDefault();

                    // Open preferences to the relevant pane.
                    if (pane === null) {
                        Mozilla.UITour.openPreferences();
                    } else {
                        Mozilla.UITour.openPreferences(pane);
                    }
                },
                false
            );
            // If the button exists in a .fl-card element with an .expand-link class,
            // then the link is meant to expand to the entire .fl-card, so we add
            // the same event listener to the .fl-card.expand-link element.
            // TODO: remove the alternative class name when 2025 designs are fully rolled out.
            let card = button.closest('.fl-card.expand-link');
            if (!card) {
                card = button.closest('.fl-card-expand-link');
            }
            if (card) {
                card.addEventListener(
                    'click',
                    (e) => {
                        e.preventDefault();

                        // Open preferences to the relevant pane.
                        if (pane === null) {
                            Mozilla.UITour.openPreferences();
                        } else {
                            Mozilla.UITour.openPreferences(pane);
                        }
                    },
                    false
                );
            }
        });

        // Find any buttons that should open the protections report.
        const openProtectionsReportButtons = document.querySelectorAll(
            '.ui-tour-open-protections-report'
        );
        // Clicking any of the openProtectionsReportButtons should open the protections report.
        openProtectionsReportButtons.forEach((button) => {
            // Make sure that the window has a protection report datalayer.
            if (typeof window.dataLayer === 'undefined') {
                window.dataLayer = [];
            }
            window.dataLayer.push({
                event: 'widget_action',
                type: 'protection report',
                action: 'open',
                label: 'View your dashboard'
            });

            // Add an event listener to the button.
            button.addEventListener(
                'click',
                (e) => {
                    e.preventDefault();

                    // Show the protections report.
                    Mozilla.UITour.showProtectionReport();
                },
                false
            );
            // If the button exists in a .fl-card element with an .expand-link class,
            // then the link is meant to expand to the entire .fl-card, so we add
            // the same event listener to the .fl-card.expand-link element.
            // TODO: remove the alternative class name when 2025 designs are fully rolled out.
            let card = button.closest('.fl-card.expand-link');
            if (!card) {
                card = button.closest('.fl-card-expand-link');
            }
            if (card) {
                card.addEventListener(
                    'click',
                    (e) => {
                        e.preventDefault();

                        // Show the protections report.
                        Mozilla.UITour.showProtectionReport();
                    },
                    false
                );
            }
        });
    });
}

function hideUITourElements() {
    'use strict';
    const uiTourElements = document.querySelectorAll('.ui-tour');
    uiTourElements.forEach((element) => {
        element.style.display = 'none';
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
