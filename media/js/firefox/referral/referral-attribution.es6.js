/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Referral attribution checkbox module for the /get-firefox/?invitation=<code> page.
 *
 * The checkbox ("Let Mozilla count your install as a referral") is default-checked
 * (opt-out). When checked, the invitation code is carried as utm_content=fxrefer<code>
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
// Desktop click-hold state (reset to false each time applyReferral starts).
ReferralAttribution._pendingClick = null;
ReferralAttribution._signingComplete = false;

/**
 * Reads the invitation code from the data attribute rendered by the template.
 * @return {String|null}
 */
ReferralAttribution.getInvitationCode = () => {
    const el = document.querySelector('[data-referral-code]');
    return el ? el.getAttribute('data-referral-code') || null : null;
};

/**
 * Reads the Play Store package id (e.g. "org.mozilla.firefox" or
 * "org.mozilla.fenix") off a badge's current href, so rewrites preserve
 * whichever channel the server originally rendered (e.g. via the
 * REFERRAL_FORCE_NIGHTLY_QA switch) instead of assuming Release.
 * @param {String|null} href
 * @return {String|null}
 */
ReferralAttribution.getPackageIdFromHref = (href) => {
    if (!href) {
        return null;
    }
    const match = href.match(/[?&]id=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : null;
};

/**
 * Rewrites Android store badges to include (or exclude) the referral utm_content.
 * Delegates URL construction to MobileAttribution.getStoreUrl. Preserves each
 * badge's existing Play Store package id rather than assuming Release.
 * @param {String|null} referralContent - e.g. "fxrefer1HR4FZ672Z8Y0E4HW", or null to strip.
 */
ReferralAttribution.rewriteAndroidLinks = (referralContent) => {
    const campaign = referralContent ? REFERRAL_CAMPAIGN : UNCHECKED_CAMPAIGN;
    const badges = document.querySelectorAll('.fl-store-button-android');
    for (const badge of badges) {
        const packageId = ReferralAttribution.getPackageIdFromHref(
            badge.getAttribute('href')
        );
        const storeUrl = window.Mozilla.MobileAttribution.getStoreUrl(
            campaign,
            true,
            referralContent,
            packageId
        );
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
            ReferralAttribution.rewriteAndroidLinks('fxrefer' + code);
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
        utm_content: 'fxrefer' + code
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

/** Navigation seam — separated so tests can spy without navigating. */
ReferralAttribution._navigate = (href) => {
    window.location.href = href;
};

/**
 * Attaches a capturing click interceptor to all .download-link elements.
 * Called at the start of every signing round so clicks during the GA wait
 * and XHR are queued rather than dispatched against an un-attributed link.
 */
ReferralAttribution._holdDesktopLinks = () => {
    ReferralAttribution._signingComplete = false;
    const links = document.querySelectorAll('.download-link');
    for (const link of links) {
        link.addEventListener(
            'click',
            ReferralAttribution._interceptClick,
            true
        );
    }
};

/**
 * Capturing click handler attached by _holdDesktopLinks.
 * Prevents default and saves the element; _releaseDesktopLinks navigates
 * using its then-current href once the signed URL is ready.
 * @param {Event} e
 */
ReferralAttribution._interceptClick = (e) => {
    if (ReferralAttribution._signingComplete) {
        return;
    }
    e.preventDefault();
    ReferralAttribution._pendingClick = e.currentTarget;
};

/**
 * Releases held download links after signing completes (success or failure).
 * Idempotent — safe to call from both applyReferral and removeReferral.
 * If a click was queued, navigates to the link's current href: decorated on
 * success, undecorated on failure — the download still proceeds either way.
 */
ReferralAttribution._releaseDesktopLinks = () => {
    if (ReferralAttribution._signingComplete) {
        return;
    }
    ReferralAttribution._signingComplete = true;
    const links = document.querySelectorAll('.download-link');
    for (const link of links) {
        link.removeEventListener(
            'click',
            ReferralAttribution._interceptClick,
            true
        );
    }
    if (ReferralAttribution._pendingClick) {
        const href =
            ReferralAttribution._pendingClick.href ||
            ReferralAttribution._pendingClick.getAttribute('href');
        ReferralAttribution._pendingClick = null;
        if (href) {
            ReferralAttribution._navigate(href);
        }
    }
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

    // Hold desktop download links until the signed URL is ready. Any click
    // that arrives during the GA wait or XHR is queued and replayed against
    // the decorated href once signing completes.
    ReferralAttribution._holdDesktopLinks();

    const onSuccess = () => {
        ReferralAttribution._releaseDesktopLinks();
        if (typeof successCallback === 'function') {
            successCallback();
        }
    };
    const onTimeout = () => {
        ReferralAttribution._releaseDesktopLinks();
        if (typeof timeoutCallback === 'function') {
            timeoutCallback();
        }
    };

    // Same-session re-check — reuse the in-memory signed response.
    if (ReferralAttribution._cachedResponseData) {
        Mozilla.DownloadAttribution.cleanBouncerLinks();
        Mozilla.DownloadAttribution.updateBouncerLinks(
            ReferralAttribution._cachedResponseData
        );
        onSuccess();
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
            onSuccess,
            onTimeout
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

    // Unblock any click held during a concurrent signing round — the user
    // opted out, so navigate immediately with the un-attributed href.
    ReferralAttribution._releaseDesktopLinks();

    // Strip referral attribution_code/sig from download links on this page.
    Mozilla.DownloadAttribution.cleanBouncerLinks();
    // Re-apply the standard first-touch cookie (no-op if it doesn't exist).
    Mozilla.DownloadAttribution.applyAttributionDataToLinks();

    if (typeof successCallback === 'function') {
        successCallback();
    }
};

export default ReferralAttribution;
