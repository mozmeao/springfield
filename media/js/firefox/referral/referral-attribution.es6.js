/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Referral attribution checkbox module for the /get-firefox/?invitation=<code> page.
 *
 * The checkbox ("Let Mozilla count your install as a referral") is default-checked
 * (opt-out). When checked, the invitation code is carried as utm_content=fxrefer:<code>
 * in download attribution:
 *  - Desktop (Windows/macOS): via the referral pipeline defined below, which decorates
 *    Bouncer download links without touching the shared first-touch analytics cookies.
 *  - Android: the Play Store badge href is rewritten to include utm_content in the
 *    referrer string.
 *  - iOS: does not participate; the checkbox is hidden on iOS UAs.
 *
 * Attribution state is held in memory only (_cachedResponseData). This is sufficient
 * because the referral pipeline is confined to this page — a page reload re-runs the
 * XHR, and within a session the cache makes uncheck/re-check instant.
 */

const REFERRAL_CAMPAIGN = 'firefox-referral';
const UNCHECKED_CAMPAIGN = 'get-firefox';

const ReferralAttribution = {};

ReferralAttribution.REFERRAL_CAMPAIGN = REFERRAL_CAMPAIGN;
// Save signed response
ReferralAttribution._cachedResponseData = null;

/**
 * Reads the invitation code from the data attribute rendered by the template.
 * @return {String|null}
 */
ReferralAttribution.getInvitationCode = () => {
    const el = document.querySelector('[data-referral-code]');
    return el ? el.getAttribute('data-referral-code') || null : null;
};

/**
 * Rewrites Android store badges to include (or exclude) the referral utm_content.
 * Delegates URL construction to MobileAttribution.getStoreUrl.
 * @param {String|null} referralContent - e.g. "fxrefer:1HR4FZ672Z8Y0E4HW", or null to strip.
 */
ReferralAttribution.rewriteAndroidLinks = (referralContent) => {
    const campaign = referralContent ? REFERRAL_CAMPAIGN : UNCHECKED_CAMPAIGN;
    const storeUrl = window.Mozilla.MobileAttribution.getStoreUrl(
        campaign,
        true,
        referralContent
    );
    const badges = document.querySelectorAll('.fl-store-button-android');
    for (const badge of badges) {
        badge.setAttribute('href', storeUrl);
    }
};

/**
 * Applies or removes referral attribution based on checkbox state.
 * @param {Boolean} checked - Whether referral attribution should be applied.
 */
ReferralAttribution.processAttributionRequest = (checked) => {
    const code = ReferralAttribution.getInvitationCode();
    if (!code) {
        return;
    }

    const isAndroid = window.site.platform === 'android';

    if (checked) {
        if (isAndroid) {
            ReferralAttribution.rewriteAndroidLinks('fxrefer:' + code);
        } else {
            ReferralAttribution.applyReferral(code);
        }
    } else {
        if (isAndroid) {
            ReferralAttribution.rewriteAndroidLinks(null);
        } else {
            ReferralAttribution.removeReferral();
        }
    }
};

/**
 * Handles checkbox change event.
 * @param {Object} e - change event object.
 */
ReferralAttribution.handleChangeEvent = (e) => {
    ReferralAttribution.setCheckboxState(e.target.checked);
    ReferralAttribution.processAttributionRequest(e.target.checked);
};

/**
 * Binds checkbox change event listeners.
 */
ReferralAttribution.bindEvents = () => {
    const checkboxes = document.querySelectorAll('.referral-consent-checkbox');
    for (const checkbox of checkboxes) {
        checkbox.addEventListener(
            'change',
            ReferralAttribution.handleChangeEvent,
            false
        );
        checkbox.disabled = false;
    }
};

/**
 * Sets the checked state of all referral consent checkboxes.
 * @param {Boolean} checked
 */
ReferralAttribution.setCheckboxState = (checked) => {
    const checkboxes = document.querySelectorAll('.referral-consent-checkbox');
    for (const checkbox of checkboxes) {
        checkbox.checked = checked;
    }
};

/**
 * Reveals the checkbox labels and sets them to checked.
 */
ReferralAttribution.showCheckbox = () => {
    const labels = document.querySelectorAll('.referral-consent-label');
    for (const label of labels) {
        label.classList.remove('hidden');
    }
    ReferralAttribution.setCheckboxState(true);
};

/**
 * Determines if the referral attribution checkbox should be shown and
 * whether the attribution machinery is available.
 *  - iOS: excluded (App Store does not support this referral mechanism).
 *  - Android: participates via Play Store referrer; requires MobileAttribution.
 *  - Desktop: requires standard DownloadAttribution functional requirements
 *    (Windows/macOS, cookies enabled, relevant globals present).
 * @return {Boolean}
 */
ReferralAttribution.meetsRequirements = () => {
    const platform = window.site.platform;

    if (platform === 'ios') {
        return false;
    }

    if (platform === 'android') {
        return (
            typeof window.Mozilla !== 'undefined' &&
            typeof window.Mozilla.MobileAttribution !== 'undefined' &&
            typeof window.Mozilla.MobileAttribution.getStoreUrl === 'function'
        );
    }

    return (
        typeof window.Mozilla !== 'undefined' &&
        typeof window.Mozilla.DownloadAttribution !== 'undefined' &&
        window.Mozilla.DownloadAttribution.meetsFunctionalRequirements()
    );
};

/**
 * Entry point. Checks requirements, reads the invitation code, shows the
 * checkbox, then fires the initial attribution request and binds checkboxes
 * @return {Boolean} - Whether init ran successfully.
 */
ReferralAttribution.init = () => {
    if (!ReferralAttribution.meetsRequirements()) {
        return false;
    }

    const code = ReferralAttribution.getInvitationCode();
    if (!code) {
        return false;
    }

    const checkboxes = document.querySelectorAll('.referral-consent-checkbox');
    if (checkboxes.length === 0) {
        return false;
    }

    ReferralAttribution.showCheckbox();
    ReferralAttribution.bindEvents();
    ReferralAttribution.processAttributionRequest(true);

    return true;
};

// -------------------------------------------------------------------------
// Referral signing pipeline.
// -------------------------------------------------------------------------

/**
 * Builds the referral attribution data object for the given invitation code.
 * @param {String} code - The invitation code (e.g. "1HR4FZ672Z8Y0E4HW").
 * @return {Object} - Referral attribution data.
 */
ReferralAttribution.getReferralData = (code) => {
    return {
        utm_source: 'www.firefox.com',
        utm_medium: 'referral',
        utm_campaign: REFERRAL_CAMPAIGN,
        utm_content: 'fxrefer:' + code
    };
};

/**
 * XHR request to the stub_attribution_code service. Uses an independent
 * URL from download-attribution.es6.js.
 * @param {Object} data - Referral attribution data to sign.
 * @param {Function} successCallback - Optional.
 * @param {Function} timeoutCallback - Optional.
 */
ReferralAttribution.requestReferralAuthentication = (
    data,
    successCallback,
    timeoutCallback
) => {
    const SERVICE_URL =
        window.location.protocol +
        '//' +
        window.location.host +
        '/en-US/stub_attribution_code/';
    const xhr = new window.XMLHttpRequest();
    const timeoutValue = 10000;
    const timeout = setTimeout(() => {
        if (typeof timeoutCallback === 'function') {
            timeoutCallback();
        }
    }, timeoutValue);

    xhr.open(
        'GET',
        SERVICE_URL + '?' + window._SearchParams.objectToQueryString(data)
    );
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            const status = xhr.status;
            if (status && status >= 200 && status < 400) {
                try {
                    const responseData = JSON.parse(xhr.responseText);
                    clearTimeout(timeout);
                    if (
                        responseData.attribution_code &&
                        responseData.attribution_sig
                    ) {
                        // Cache in memory so re-check within this page session
                        // skips the GA wait and XHR round-trip.
                        ReferralAttribution._cachedResponseData = responseData;
                        // Only decorate links if the user still has the
                        // referral box checked.
                        if (Mozilla.DownloadAttribution.referralActive) {
                            Mozilla.DownloadAttribution.cleanBouncerLinks();
                            Mozilla.DownloadAttribution.updateBouncerLinks(
                                responseData
                            );
                        }
                    }
                    if (typeof successCallback === 'function') {
                        successCallback();
                    }
                } catch (e) {
                    clearTimeout(timeout);
                    if (typeof timeoutCallback === 'function') {
                        timeoutCallback();
                    }
                }
            } else {
                // Network error (status 0), CORS block, or server error — treat
                // as a timeout so the caller gets immediate feedback.
                clearTimeout(timeout);
                if (typeof timeoutCallback === 'function') {
                    timeoutCallback();
                }
            }
        }
    };

    xhr.send();
};

/**
 * Builds a full referral attribution payload
 * (utm_source/medium/campaign/content + GA client_id/session_id), signs it
 * via the referral pipeline, and decorates this page's download links.
 * Waits for GA (≤2s) so client_id_ga4 can be captured; signs without it
 * if GA is unavailable or consent was not granted.
 * @param {String} code - The invitation code.
 * @param {Function} successCallback - Optional.
 * @param {Function} timeoutCallback - Optional.
 */
ReferralAttribution.applyReferral = (
    code,
    successCallback,
    timeoutCallback
) => {
    if (!Mozilla.DownloadAttribution.meetsFunctionalRequirements()) {
        return;
    }

    const referralData = ReferralAttribution.getReferralData(code);

    // Referral takes ownership of this page's links for the session - block
    // the standard analytics pipeline from overwriting them.
    Mozilla.DownloadAttribution.referralActive = true;

    // Same-session re-check — reuse the in-memory signed response.
    if (ReferralAttribution._cachedResponseData) {
        Mozilla.DownloadAttribution.cleanBouncerLinks();
        Mozilla.DownloadAttribution.updateBouncerLinks(
            ReferralAttribution._cachedResponseData
        );
        if (typeof successCallback === 'function') {
            successCallback();
        }
        return;
    }

    Mozilla.DownloadAttribution.waitForGoogleAnalyticsThen(() => {
        const analyticsRaw = Mozilla.DownloadAttribution.getRawCookie(
            Mozilla.DownloadAttribution.COOKIE_ANALYTICS_RAW_ID
        );

        // Reuse the existing analytics session_id so the referral install
        // record joins to the same GA session as other site analytics.
        // If analytics hasn't fired yet, create a fresh session_id.
        const reusingAnalyticsSession = analyticsRaw && analyticsRaw.session_id;
        const sessionID = reusingAnalyticsSession
            ? analyticsRaw.session_id
            : Mozilla.DownloadAttribution.createSessionID();

        const clientIDGA4 = Mozilla.DownloadAttribution.getGtagClientID();

        const payload = Object.assign({}, referralData, {
            session_id: sessionID
        });

        if (clientIDGA4) {
            payload.client_id_ga4 = clientIDGA4;

            // Only push stub_session_set when we created a new session_id.
            // If analytics already pushed this event we must not duplicate it.
            if (!reusingAnalyticsSession && Array.isArray(window.dataLayer)) {
                window.dataLayer.push({
                    event: 'stub_session_set',
                    id: sessionID
                });
            }
        }

        ReferralAttribution.requestReferralAuthentication(
            payload,
            successCallback,
            timeoutCallback
        );
    });
};

/**
 * Removes referral attribution: strips referral params from this page's
 * download links, then re-applies any pre-existing standard first-touch
 * attribution.
 * @param {Function} successCallback - Optional.
 */
ReferralAttribution.removeReferral = (successCallback) => {
    // Release ownership so applyAttributionDataToLinks() below can restore
    // standard first-touch attribution from the cookie if one exists.
    Mozilla.DownloadAttribution.referralActive = false;

    // Strip referral attribution_code/sig from download links on this page.
    Mozilla.DownloadAttribution.cleanBouncerLinks();
    // Re-apply the standard first-touch cookie (no-op if it doesn't exist).
    Mozilla.DownloadAttribution.applyAttributionDataToLinks();

    if (typeof successCallback === 'function') {
        successCallback();
    }
};

export default ReferralAttribution;
