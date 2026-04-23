/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const DownloadAsDefault = {};
DownloadAsDefault.CAMPAIGN = 'download_as_default';

window.Mozilla.DownloadAsDefault = DownloadAsDefault;

/**
 * Processes attribution changes depending on checkbox state
 * @param {Boolean} checked - checkbox target value.
 */
DownloadAsDefault.processAttributionRequest = (checked) => {
    /**
     * Update essential data based on checkbox state
     */
    if (!checked) {
        window.Mozilla.DownloadAttribution.initEssential(null, () => {
            DownloadAsDefault.bindEvents();
        });
    } else {
        window.Mozilla.DownloadAttribution.initEssential(
            DownloadAsDefault.CAMPAIGN,
            () => {
                DownloadAsDefault.bindEvents();
            }
        );
    }
};

/**
 * Handles checkbox change event. Because checkbox state must be
 * synced between all checkboxes on the page, we must temporarily
 * unbind event listeners to avoid triggering multiple change
 * events at once.
 * @param {Object} e - change event object.
 */
DownloadAsDefault.handleChangeEvent = (e) => {
    DownloadAsDefault.unbindEvents();
    DownloadAsDefault.setCheckboxState(e.target.checked);
    DownloadAsDefault.processAttributionRequest(e.target.checked);
};

/**
 * Unbinds checkbox change event listeners and disables
 * inputs when unbound.
 */
DownloadAsDefault.unbindEvents = () => {
    const checkboxes = document.querySelectorAll('.default-browser-checkbox');

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].removeEventListener(
            'change',
            DownloadAsDefault.handleChangeEvent,
            false
        );
        checkboxes[i].disabled = true;
    }
};

/**
 * Binds checkbox change event listeners and removes
 * disabled states on inputs when bound.
 */
DownloadAsDefault.bindEvents = () => {
    const checkboxes = document.querySelectorAll('.default-browser-checkbox');

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].addEventListener(
            'change',
            DownloadAsDefault.handleChangeEvent,
            false
        );
        checkboxes[i].disabled = false;
    }
};

/**
 * Sets the checked state of all checkbox inputs.
 * @param {Boolean} checked state
 */
DownloadAsDefault.setCheckboxState = (checked) => {
    const checkboxes = document.querySelectorAll('.default-browser-checkbox');

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = checked;
    }
};

/**
 * Displays checkboxes via CSS by removing the `hidden`
 * class on their corresponding `<label>` parent elements.
 */
DownloadAsDefault.showCheckbox = () => {
    const labels = document.querySelectorAll('.default-browser-label');
    for (let i = 0; i < labels.length; i++) {
        labels[i].classList.remove('hidden');
        labels[i].querySelector('.default-browser-checkbox').checked = true;
    }
};

/**
 * Determines if set-as-default checkbox should display.
 * @returns {Boolean}
 */
DownloadAsDefault.meetsRequirements = () => {
    if (
        typeof window.URL !== 'function' ||
        typeof window.URLSearchParams !== 'function' ||
        !window.history.replaceState
    ) {
        return false;
        // } else if (window.site.platform !== 'windows') {
        //     // Ensure the visitor is on Windows OS
        //     return false;
    } else if (!window.site.fxSupported) {
        // Ensure the visitor is on a supported version
        return false;
    } else if (
        // Ensure download attribution functionality available
        typeof window.Mozilla.DownloadAttribution === 'undefined' ||
        !window.Mozilla.DownloadAttribution.meetsFunctionalRequirements()
    ) {
        return false;
    }

    return true;
};

/**
 * Init Firefox set-as-default opt-out flow.
 * @returns {Boolean}.
 */
DownloadAsDefault.init = () => {
    if (!DownloadAsDefault.meetsRequirements()) {
        return false;
    }

    const checkboxes = document.querySelectorAll('.default-browser-checkbox');
    if (checkboxes.length > 0) {
        DownloadAsDefault.showCheckbox();
        DownloadAsDefault.processAttributionRequest(true);
        // processAttributionRequest will bind the events
    }

    return true;
};

export default DownloadAsDefault;
