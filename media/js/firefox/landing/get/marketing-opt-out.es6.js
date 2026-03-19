/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    hasConsentCookie,
    getConsentCookie,
    setConsentCookie,
    consentRequired,
    dntEnabled,
    gpcEnabled
} from '../../../base/consent/utils.es6';

const MarketingOptOut = {};

/**
 * Processes attribution changes depending on checkbox state.
 * @param {Boolean} checked - checkbox target value.
 */
MarketingOptOut.processAttributionRequest = (checked) => {
    let previousPreferenceCookie;

    /**
     * Preserve previous preference cookie consent state if one exists
     */
    if (hasConsentCookie()) {
        const cookie = getConsentCookie();
        previousPreferenceCookie = cookie.preference;
    }

    /**
     * If checked, consent to analytics and initiate attribution.
     */
    if (checked) {
        setConsentCookie({
            analytics: true,
            preference:
                previousPreferenceCookie !== undefined &&
                previousPreferenceCookie !== null
                    ? previousPreferenceCookie
                    : true
        });
        window.Mozilla.StubAttribution.init(() => {
            /**
             * Rebind event listeners only after attribution
             * request has been successful.
             */
            MarketingOptOut.bindEvents();
        });
    } else {
        /**
         * Else set a cookie that rejects analytics.
         * Remove all existing attribution data.
         */
        setConsentCookie({
            analytics: false,
            preference:
                previousPreferenceCookie !== undefined &&
                previousPreferenceCookie !== null
                    ? previousPreferenceCookie
                    : true
        });
        window.Mozilla.StubAttribution.removeAttributionData();
        MarketingOptOut.bindEvents();

        // Remove param to download /thanks links sharing consent state with /thanks page
        const downloadThanksLinks = document.querySelectorAll(
            '.c-button-download-thanks .download-link'
        );
        for (let i = 0; i < downloadThanksLinks.length; i++) {
            const href = downloadThanksLinks[i].getAttribute('href');
            if (href) {
                const linkUrl = new URL(href, window.location.href);
                linkUrl.searchParams.delete('marketing_consent');
                downloadThanksLinks[i].setAttribute('href', linkUrl.toString());
            }
        }
    }
};

/**
 * Handles checkbox change event. Because checkbox state must be
 * synced between all checkboxes on the page, we must temporarily
 * unbind event listeners to avoid triggering multiple change
 * events at once.
 * @param {Object} e - change event object.
 */
MarketingOptOut.handleChangeEvent = (e) => {
    MarketingOptOut.unbindEvents();
    MarketingOptOut.setCheckboxState(e.target.checked);
    MarketingOptOut.processAttributionRequest(e.target.checked);
};

/**
 * Unbinds checkbox change event listeners and disables
 * inputs when unbound.
 */
MarketingOptOut.unbindEvents = () => {
    const checkboxes = document.querySelectorAll(
        '.marketing-opt-out-checkbox-input'
    );

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].removeEventListener(
            'change',
            MarketingOptOut.handleChangeEvent,
            false
        );
        checkboxes[i].disabled = true;
    }
};

/**
 * Binds checkbox change event listeners and removes
 * disabled states on inputs when bound.
 */
MarketingOptOut.bindEvents = () => {
    const checkboxes = document.querySelectorAll(
        '.marketing-opt-out-checkbox-input'
    );

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].addEventListener(
            'change',
            MarketingOptOut.handleChangeEvent,
            false
        );
        checkboxes[i].disabled = false;
    }
};

/**
 * Sets the checked state of all checkbox inputs.
 * @param {Boolean} checked state
 */
MarketingOptOut.setCheckboxState = (checked) => {
    const checkboxes = document.querySelectorAll(
        '.marketing-opt-out-checkbox-input'
    );

    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = checked;
    }
};

/**
 * Determines if marketing opt-out checkboxes should
 * be displayed.
 * @returns {Boolean}
 */
MarketingOptOut.shouldShowCheckbox = () => {
    let show = false;

    /**
     * Has the visitor set a browser-level privacy flag?
     */
    if (dntEnabled() || gpcEnabled()) {
        show = false;
    } else if (window.Mozilla.StubAttribution.hasCookie()) {
        /**
         * Does the visitor have an existing attribution cookie?
         */
        show = true;
    } else if (hasConsentCookie()) {
        /**
         * Does the visitor have an existing analytics consent cookie?
         */
        const cookie = getConsentCookie();
        show = cookie.analytics ? true : false;
    } else {
        /**
         * Is the visitor in EU/EAA?
         */
        show = consentRequired() ? false : true;
    }

    return show;
};

/**
 * Displays checkboxes via CSS by removing the `hidden`
 * class on their corresponding `<label>` parent elements.
 * Also sets `checked=true` to enforce opt-out state.
 */
MarketingOptOut.showCheckbox = () => {
    const labels = document.querySelectorAll(
        '.marketing-opt-out-checkbox-label'
    );

    for (let i = 0; i < labels.length; i++) {
        labels[i].classList.remove('hidden');
        labels[i].querySelector('.marketing-opt-out-checkbox-input').checked =
            true;
    }

    // Add param to download /thanks links sharing consent state with /thanks page
    // This is only necessary on initial "show" of checked checkbox
    // User interaction with the checkbox will set a global pref cookie
    const downloadThanksLinks = document.querySelectorAll(
        '.c-button-download-thanks .download-link'
    );
    for (let i = 0; i < downloadThanksLinks.length; i++) {
        const href = downloadThanksLinks[i].getAttribute('href');
        if (href) {
            const linkUrl = new URL(href, window.location.href);
            linkUrl.searchParams.set('marketing_consent', '1');
            downloadThanksLinks[i].setAttribute('href', linkUrl.toString());
        }
    }
};

/**
 * Determines if marketing opt-out logic should run,
 * based on existing attribution requirements.
 * @returns {Boolean}
 */
MarketingOptOut.meetsRequirements = () => {
    return (
        typeof window.Mozilla.StubAttribution !== 'undefined' &&
        window.Mozilla.StubAttribution.meetsRequirements()
    );
};

/**
 * Initializes marketing opt-out flow
 * @returns {Boolean}.
 */
MarketingOptOut.init = () => {
    if (!MarketingOptOut.meetsRequirements()) {
        return false;
    }

    if (MarketingOptOut.shouldShowCheckbox()) {
        MarketingOptOut.showCheckbox();
        MarketingOptOut.bindEvents();
        return true;
    }

    return false;
};

export default MarketingOptOut;
