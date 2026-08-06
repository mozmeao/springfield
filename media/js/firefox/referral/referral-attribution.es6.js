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

const ReferralAttribution = {};

ReferralAttribution.REFERRAL_CAMPAIGN = REFERRAL_CAMPAIGN;
// Own in-flight XHR handle — never shared with DownloadAttribution.inFlightXHR
// so rapid checkbox toggles and the standard analytics request never race.
ReferralAttribution.referralInFlightXHR = null;
// In-memory cache of the last successful signed response. Lets re-check skip
// the GA wait and XHR round-trip within the same page session.
ReferralAttribution._cachedResponseData = null;
// Snapshot of Android link hrefs taken before the first referral rewrite.
// Used to restore original URLs when the user opts out.
ReferralAttribution._savedAndroidHrefs = null;

/**
 * Reads the invitation code from the data attribute rendered by the template.
 * The code is already validated server-side (crypto decryptable) before being
 * placed in the attribute, so no client-side re-validation is needed.
 * @return {String|null}
 */
ReferralAttribution.getInvitationCode = () => {
    const el = document.querySelector('[data-referral-code]');
    return el ? el.getAttribute('data-referral-code') || null : null;
};

/**
 * Rewrites Android store badge and mobile-rewritten download links to include
 * (or exclude) the referral utm_content in the Play Store referrer string.
 * Delegates URL construction to MobileAttribution.getStoreUrl so the format
 * stays byte-identical to the server-rendered value.
 * @param {String|null} referralContent - e.g. "fxrefer:1HR4FZ672Z8Y0E4HW", or null to strip.
 */
ReferralAttribution.rewriteAndroidLinks = (referralContent) => {
    const badges = document.querySelectorAll('.fl-store-button-android');
    const downloadLinks = document.querySelectorAll(
        '.c-button-download-thanks-link, .c-button-download-thanks > .download-link'
    );

    if (referralContent === null) {
        // Restore original hrefs saved before the first referral rewrite.
        if (ReferralAttribution._savedAndroidHrefs) {
            for (let i = 0; i < badges.length; i++) {
                badges[i].setAttribute(
                    'href',
                    ReferralAttribution._savedAndroidHrefs.badges[i] || ''
                );
            }
            for (let i = 0; i < downloadLinks.length; i++) {
                const href = downloadLinks[i].getAttribute('href') || '';
                if (href.indexOf('play.google.com') !== -1) {
                    downloadLinks[i].setAttribute(
                        'href',
                        ReferralAttribution._savedAndroidHrefs.downloadLinks[
                            i
                        ] || href
                    );
                }
            }
        }
        return;
    }

    // Snapshot original hrefs before the first rewrite so opt-out restores them.
    if (!ReferralAttribution._savedAndroidHrefs) {
        const saved = { badges: [], downloadLinks: [] };
        for (let i = 0; i < badges.length; i++) {
            saved.badges.push(badges[i].getAttribute('href') || '');
        }
        for (let i = 0; i < downloadLinks.length; i++) {
            saved.downloadLinks.push(
                downloadLinks[i].getAttribute('href') || ''
            );
        }
        ReferralAttribution._savedAndroidHrefs = saved;
    }

    const storeUrl = window.Mozilla.MobileAttribution.getStoreUrl(
        REFERRAL_CAMPAIGN,
        true,
        referralContent
    );

    // Rewrite the explicit Android store badge.
    for (let i = 0; i < badges.length; i++) {
        badges[i].setAttribute('href', storeUrl);
    }

    // Rewrite any /thanks/-bound download buttons that mobile-attribution has
    // already converted to Play Store URLs (they now contain 'play.google.com').
    for (let i = 0; i < downloadLinks.length; i++) {
        const href = downloadLinks[i].getAttribute('href') || '';
        if (href.indexOf('play.google.com') !== -1) {
            downloadLinks[i].setAttribute('href', storeUrl);
        }
    }
};

/**
 * Applies or removes referral attribution based on checkbox state.
 * On desktop: delegates to ReferralAttribution.initReferral / .removeReferral.
 * On Android: rewrites store button hrefs directly (no XHR path).
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
            ReferralAttribution.initReferral(code);
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
 * Handles checkbox change event. Syncs all checkboxes (in case there are
 * multiple instances on the page).
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
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].addEventListener(
            'change',
            ReferralAttribution.handleChangeEvent,
            false
        );
        checkboxes[i].disabled = false;
    }
};

/**
 * Sets the checked state of all referral consent checkboxes.
 * @param {Boolean} checked
 */
ReferralAttribution.setCheckboxState = (checked) => {
    const checkboxes = document.querySelectorAll('.referral-consent-checkbox');
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = checked;
    }
};

/**
 * Reveals the unsupported-browser message (hidden by default).
 * Shown when meetsRequirements() returns false so the user knows why
 * there is no referral checkbox, while still being able to download.
 */
ReferralAttribution.showUnsupportedMessage = () => {
    const messages = document.querySelectorAll('.referral-unsupported-message');
    for (let i = 0; i < messages.length; i++) {
        messages[i].classList.remove('hidden');
    }
};

/**
 * Reveals the checkbox labels (hidden by default) and sets them to
 * checked (opt-out default).
 */
ReferralAttribution.showCheckbox = () => {
    const labels = document.querySelectorAll('.referral-consent-label');
    for (let i = 0; i < labels.length; i++) {
        labels[i].classList.remove('hidden');
        labels[i].querySelector('.referral-consent-checkbox').checked = true;
    }
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
 * checkbox (default checked = opt-out), then fires the initial attribution
 * request. Checkbox events are bound after the first async operation completes.
 * @return {Boolean} - Whether init ran successfully.
 */
ReferralAttribution.init = () => {
    if (!ReferralAttribution.meetsRequirements()) {
        ReferralAttribution.showUnsupportedMessage();
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
    // Default checked = opt-out; fire attribution immediately.
    ReferralAttribution.processAttributionRequest(true);

    return true;
};

// -------------------------------------------------------------------------
// Referral signing pipeline — independent of DownloadAttribution's shared
// first-touch cookies and XHR state. Only this module decorates download
// links with referral attribution, so page-scoping is structural rather than
// requiring active cleanup when the user navigates away.
// -------------------------------------------------------------------------

/**
 * Builds the referral attribution data object for the given invitation code.
 * utm fields match the Android Play Store referrer so both platforms are
 * attributed consistently.
 * @param {String} code - The invitation code (e.g. "1HR4FZ672Z8Y0E4HW").
 * @return {Object} - Referral attribution data, or {} if no code.
 */
ReferralAttribution.getReferralData = (code) => {
    if (!code) {
        return {};
    }
    return {
        utm_source: 'www.firefox.com',
        utm_medium: 'referral',
        utm_campaign: REFERRAL_CAMPAIGN,
        utm_content: 'fxrefer:' + code
    };
};

/**
 * XHR request to the stub_attribution_code service using the referral
 * pipeline's own in-flight handle so it never aborts the standard
 * analytics request or vice versa.
 * @param {Object} data - Referral attribution data to sign.
 * @param {Function} successCallback - Optional.
 * @param {Function} timeoutCallback - Optional.
 */
ReferralAttribution.requestReferralAuthentication = (
    data,
    successCallback,
    timeoutCallback
) => {
    if (ReferralAttribution.referralInFlightXHR) {
        ReferralAttribution.referralInFlightXHR.abort();
        ReferralAttribution.referralInFlightXHR = null;
    }

    // Mirrors the URL in download-attribution.es6.js; kept separate since both
    // modules maintain independent in-flight handles to avoid XHR racing.
    const SERVICE_URL =
        window.location.protocol +
        '//' +
        window.location.host +
        '/en-US/stub_attribution_code/';
    const xhr = new window.XMLHttpRequest();
    const timeoutValue = 10000;
    const timeout = setTimeout(() => {
        ReferralAttribution.referralInFlightXHR = null;
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
            const isCurrent = ReferralAttribution.referralInFlightXHR === xhr;
            if (isCurrent) {
                ReferralAttribution.referralInFlightXHR = null;
            } else {
                // Aborted by a newer toggle — drop the outdated response.
                return;
            }

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
                        // Replace any standard attribution on this page's
                        // links with the referral attribution so referral wins.
                        Mozilla.DownloadAttribution.cleanBouncerLinks();
                        Mozilla.DownloadAttribution.updateBouncerLinks(
                            responseData
                        );
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

    ReferralAttribution.referralInFlightXHR = xhr;
    xhr.send();
};

/**
 * Referral trigger entry point. Builds a full referral attribution payload
 * (utm_source/medium/campaign/content + GA client_id/session_id), signs it
 * via the referral pipeline, and decorates this page's download links.
 * Waits for GA (≤2s) so client_id_ga4 can be captured; signs without it
 * if GA is unavailable or consent was not granted.
 * @param {String} code - The invitation code.
 * @param {Function} successCallback - Optional.
 * @param {Function} timeoutCallback - Optional.
 */
ReferralAttribution.initReferral = (code, successCallback, timeoutCallback) => {
    if (!Mozilla.DownloadAttribution.meetsFunctionalRequirements()) {
        return;
    }

    const referralData = ReferralAttribution.getReferralData(code);
    if (Object.keys(referralData).length === 0) {
        return;
    }

    // Referral takes ownership of this page's links for the session: block
    // the standard analytics pipeline from overwriting them if its XHR
    // completes after ours.
    Mozilla.DownloadAttribution.referralActive = true;

    // Fast path: same-session re-check — reuse the in-memory signed response
    // without another GA wait or XHR.
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
 * Removes referral attribution: aborts any in-flight referral request,
 * strips referral params from this page's download links, then re-applies
 * any pre-existing standard first-touch attribution so unchecking the
 * referral box cleanly falls back.
 * @param {Function} successCallback - Optional.
 */
ReferralAttribution.removeReferral = (successCallback) => {
    if (ReferralAttribution.referralInFlightXHR) {
        ReferralAttribution.referralInFlightXHR.abort();
        ReferralAttribution.referralInFlightXHR = null;
    }

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
