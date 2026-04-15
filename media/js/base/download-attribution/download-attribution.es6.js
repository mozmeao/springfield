/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

window.dataLayer = window.dataLayer || [];

/**
 * Constructs attribution data based on utm parameters, referrer information, and
 * essential product context / install options for relay to the Firefox stub installer.
 * Data is first signed and encoded via an XHR request to the `stub_attribution_code` service,
 * before being appended to Bouncer download URLs as query parameters. Data returned from the
 * service is also stored in a cookie to save multiple requests when navigating pages.
 * Original Bug https://bugzilla.mozilla.org/show_bug.cgi?id=1279291
 *
 * In 2026, this file was renamed from Stub Attribution to Download Attribution to more
 * clearly indicate this is information provided through the download. References to the Stub
 * Attribution Service remain as the website code connects to an external service that uses
 * this name: https://github.com/mozilla-services/stubattribution.
 * Refactor task: https://mozilla-hub.atlassian.net/browse/WT-964
 *
 * Essential and marketing attribution are driven by independent triggers and know
 * nothing about each other:
 *  - Essential (rtamo, download_as_default, smart_window) is required for functional
 *    post-download behavior. It runs without consent gating or sample-rate limiting,
 *    triggered by a `data-stub-attribution-campaign-force` attribute on the current page.
 *  - Marketing is consent-gated and sample-rated, triggered by a `gtm-marketing-consent`
 *    event dispatched from GTM.
 * Each trigger reads the other's last-captured raw data from a side cookie so it can
 * re-sign the combined payload without the other trigger having fired on this page.
 */
const DownloadAttribution = {
    COOKIE_CODE_ID: 'moz-download-attribution-code',
    COOKIE_SIGNATURE_ID: 'moz-download-attribution-sig',
    COOKIE_ESSENTIAL_RAW_ID: 'moz-download-attribution-essential-raw',
    COOKIE_MARKETING_RAW_ID: 'moz-download-attribution-marketing-raw',
    DLSOURCE: 'fxdotcom',

    /**
     * Custom event handler callback globals. These can be defined as functions when
     * calling DownloadAttribution.initEssential() or .initMarketing().
     */
    successCallback: undefined,
    timeoutCallback: undefined,
    requestComplete: false,

    /**
     * Determines if session falls within the predefined download attribution sample rate.
     * @return {Boolean}.
     */
    withinAttributionRate: () => {
        return Math.random() < DownloadAttribution.getAttributionRate();
    },

    /**
     * Returns download attribution value used for rate limiting.
     * @return {Number} float between 0 and 1.
     */
    getAttributionRate: () => {
        const rate = document
            .getElementsByTagName('html')[0]
            .getAttribute('data-stub-attribution-rate');
        return isNaN(rate) || !rate
            ? 0
            : Math.min(Math.max(parseFloat(rate), 0), 1);
    },

    /**
     * Returns true if both signed cookies exist.
     * @return {Boolean} data.
     */
    hasSignedCookie: () => {
        return (
            Mozilla.Cookies.hasItem(DownloadAttribution.COOKIE_CODE_ID) &&
            Mozilla.Cookies.hasItem(DownloadAttribution.COOKIE_SIGNATURE_ID)
        );
    },

    /**
     * Stores the signed download attribution data values.
     * @param {Object} data - attribution_code, attribution_sig.
     */
    setSignedCookie: (data) => {
        if (!data.attribution_code || !data.attribution_sig) {
            return;
        }

        // set cookie to expire in 24 hours
        const date = new Date();
        date.setTime(date.getTime() + 1 * 24 * 60 * 60 * 1000);
        const expires = date.toUTCString();

        Mozilla.Cookies.setItem(
            DownloadAttribution.COOKIE_CODE_ID,
            data.attribution_code,
            expires,
            '/',
            undefined,
            false,
            'lax'
        );
        Mozilla.Cookies.setItem(
            DownloadAttribution.COOKIE_SIGNATURE_ID,
            data.attribution_sig,
            expires,
            '/',
            undefined,
            false,
            'lax'
        );
    },

    /**
     * Removes the signed download attribution cookies.
     */
    removeSignedCookie: () => {
        window.Mozilla.Cookies.removeItem(
            DownloadAttribution.COOKIE_CODE_ID,
            '/',
            undefined,
            false,
            'lax'
        );

        window.Mozilla.Cookies.removeItem(
            DownloadAttribution.COOKIE_SIGNATURE_ID,
            '/',
            undefined,
            false,
            'lax'
        );
    },

    /**
     * Gets signed download attribution data from cookie.
     * @return {Object} - attribution_code, attribution_sig.
     */
    getSignedCookie: () => {
        return {
            attribution_code: Mozilla.Cookies.getItem(
                DownloadAttribution.COOKIE_CODE_ID
            ),
            attribution_sig: Mozilla.Cookies.getItem(
                DownloadAttribution.COOKIE_SIGNATURE_ID
            )
        };
    },

    /**
     * Stores a raw attribution data object as a JSON-encoded cookie.
     * Raw cookies preserve the inputs used to build the signed payload so
     * either trigger (essential or marketing) can re-sign the combined
     * payload without the other having fired on the current page.
     * @param {String} id - COOKIE_ESSENTIAL_RAW_ID or COOKIE_MARKETING_RAW_ID.
     * @param {Object} data - Raw attribution data to preserve.
     */
    setRawCookie: (id, data) => {
        const date = new Date();
        date.setTime(date.getTime() + 1 * 24 * 60 * 60 * 1000);
        const expires = date.toUTCString();

        Mozilla.Cookies.setItem(
            id,
            JSON.stringify(data),
            expires,
            '/',
            undefined,
            false,
            'lax'
        );
    },

    /**
     * Gets a raw attribution data object from cookie.
     * @param {String} id - Cookie id.
     * @return {Object | null} - Parsed data, or null if missing or unparseable.
     */
    getRawCookie: (id) => {
        const raw = Mozilla.Cookies.getItem(id);
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    },

    /**
     * Removes a raw attribution data cookie.
     * @param {String} id - Cookie id.
     */
    removeRawCookie: (id) => {
        window.Mozilla.Cookies.removeItem(id, '/', undefined, false, 'lax');
    },

    /**
     * Updates all download links on the page with additional query params for
     * download attribution.
     * @param {Object} data - attribution_code, attribution_sig.
     */
    updateBouncerLinks: (data) => {
        /**
         * If data is missing or the browser does not meet requirements for
         * download attribution, then do nothing.
         */
        if (
            !data.attribution_code ||
            !data.attribution_sig ||
            !DownloadAttribution.meetsFunctionalRequirements()
        ) {
            return;
        }

        // target download buttons and other-platforms modal links.
        const downloadLinks = document.querySelectorAll('.download-link');

        for (const link of downloadLinks) {
            let version;
            let directLink;
            // Append download attribution data to direct download links.
            if (
                link.href &&
                (link.href.indexOf('https://download.mozilla.org') !== -1 ||
                    link.href.indexOf(
                        'https://bouncer-bouncer.stage.mozaws.net/'
                    ) !== -1 ||
                    link.href.indexOf(
                        'https://stage.bouncer.nonprod.webservices.mozgcp.net'
                    ) !== -1 ||
                    link.href.indexOf(
                        'https://dev.bouncer.nonprod.webservices.mozgcp.net'
                    ) !== -1)
            ) {
                version = link.getAttribute('data-download-version');

                // Append attribution params to Windows links.
                if (version && /win/.test(version)) {
                    link.href = DownloadAttribution.appendToDownloadURL(
                        link.href,
                        data
                    );
                }
                // Append attribution params to macOS links (excluding ESR for now).
                if (
                    version &&
                    /osx/.test(version) &&
                    !/product=firefox-esr/.test(link.href)
                ) {
                    link.href = DownloadAttribution.appendToDownloadURL(
                        link.href,
                        data
                    );
                }
            } else if (link.href && link.href.indexOf('/thanks/') !== -1) {
                // Append download data to direct-link data attributes on transitional links for old IE browsers (Issue #9350)
                directLink = link.getAttribute('data-direct-link');

                if (directLink) {
                    link.setAttribute(
                        'data-direct-link',
                        DownloadAttribution.appendToDownloadURL(
                            directLink,
                            data
                        )
                    );
                }
            }
        }
    },

    removeLinkAttributionParams: (href) => {
        if (href.indexOf('?') > 0) {
            const params = new window._SearchParams(href.split('?')[1]);
            const origin = href.split('?')[0];

            if (
                params.has('attribution_code') &&
                params.has('attribution_sig')
            ) {
                params.remove('attribution_code');
                params.remove('attribution_sig');
                return (
                    origin + '?' + window.decodeURIComponent(params.toString())
                );
            }
        }

        return href;
    },

    cleanBouncerLinks: () => {
        const downloadLinks = document.querySelectorAll('.download-link');

        for (const link of downloadLinks) {
            link.href = DownloadAttribution.removeLinkAttributionParams(
                link.href
            );

            if (link.hasAttribute('data-direct-link')) {
                const attribute =
                    DownloadAttribution.removeLinkAttributionParams(
                        link.getAttribute('data-direct-link')
                    );
                link.setAttribute('data-direct-link', attribute);
            }
        }
    },

    removeAttributionData: () => {
        DownloadAttribution.removeSignedCookie();
        DownloadAttribution.removeRawCookie(
            DownloadAttribution.COOKIE_ESSENTIAL_RAW_ID
        );
        DownloadAttribution.removeRawCookie(
            DownloadAttribution.COOKIE_MARKETING_RAW_ID
        );
        DownloadAttribution.cleanBouncerLinks();
        DownloadAttribution.requestComplete = false;
    },

    /**
     * Appends download attribution data as URL parameters.
     * Note: data is already URI encoded when returned via the service.
     * @param {String} url - URL to append data to.
     * @param {Object} data - attribution_code, attribution_sig.
     * @return {String} url + additional parameters.
     */
    appendToDownloadURL: (url, data) => {
        if (!data.attribution_code || !data.attribution_sig) {
            return url;
        }

        // append download attribution query params.
        for (const key of Object.keys(data)) {
            if (key === 'attribution_code' || key === 'attribution_sig') {
                url +=
                    (url.indexOf('?') > -1 ? '&' : '?') + key + '=' + data[key];
            }
        }

        return url;
    },

    /**
     * Handles XHR request from `stub_attribution_code` service.
     * @param {Object} data - attribution_code, attribution_sig.
     */
    onRequestSuccess: (data) => {
        if (
            data.attribution_code &&
            data.attribution_sig &&
            !DownloadAttribution.requestComplete
        ) {
            // Update download links on the current page.
            DownloadAttribution.updateBouncerLinks(data);
            // Store attribution data in a cookie should the user navigate.
            DownloadAttribution.setSignedCookie(data);

            DownloadAttribution.requestComplete = true;

            if (typeof DownloadAttribution.successCallback === 'function') {
                DownloadAttribution.successCallback();
            }
        }
    },

    onRequestTimeout: () => {
        if (!DownloadAttribution.requestComplete) {
            DownloadAttribution.requestComplete = true;

            if (typeof DownloadAttribution.timeoutCallback === 'function') {
                DownloadAttribution.timeoutCallback();
            }
        }
    },

    /**
     * AJAX request to springfield service to authenticate download attribution request.
     * @param {Object} data - utm params and referrer.
     */
    requestAuthentication: (data) => {
        const SERVICE_URL =
            window.location.protocol +
            '//' +
            window.location.host +
            '/en-US/stub_attribution_code/';
        const xhr = new window.XMLHttpRequest();
        const timeoutValue = 10000;
        const timeout = setTimeout(
            DownloadAttribution.onRequestTimeout,
            timeoutValue
        );

        xhr.open(
            'GET',
            SERVICE_URL + '?' + window._SearchParams.objectToQueryString(data)
        );
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        // use readystate change over onload for IE8 support.
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4) {
                const status = xhr.status;
                if (status && status >= 200 && status < 400) {
                    try {
                        const responseData = JSON.parse(xhr.responseText);
                        clearTimeout(timeout);
                        DownloadAttribution.onRequestSuccess(responseData);
                    } catch (e) {
                        // something went wrong, fallback to the timeout handler.
                        DownloadAttribution.onRequestTimeout();
                    }
                }
            }
        };

        // must come after open call above for IE 10 & 11
        xhr.timeout = timeoutValue;
        xhr.send();
    },

    /**
     * Returns a browser name based on coarse UA string detection for only major browsers.
     * Other browsers (or modified UAs) that have strings that look like one of the top default user agent strings are treated as false positives.
     * @param {String} ua - Optional user agent string to facilitate testing.
     * @returns {String} - Browser name.
     */
    getUserAgent: (ua) => {
        ua = typeof ua !== 'undefined' ? ua : navigator.userAgent;

        if (/MSIE|Trident/i.test(ua)) {
            return 'ie';
        }

        if (/Edg|Edge/i.test(ua)) {
            return 'edge';
        }

        if (/Firefox/.test(ua)) {
            return 'firefox';
        }

        if (/Chrome/.test(ua)) {
            return 'chrome';
        }

        return 'other';
    },

    /**
     * Attempts to retrieve the GA4 client from the dataLayer
     * The GTAG GET API tag will write it to the dataLayer once GTM has loaded it
     * https://www.simoahava.com/gtmtips/write-client-id-other-gtag-fields-datalayer/
     */
    getGtagClientID: (dataLayer) => {
        // need to pass in dataLayer for testing purposes, use global dataLayer if it's not passed
        dataLayer =
            typeof dataLayer !== 'undefined' ? dataLayer : window.dataLayer;

        let clientID = null;

        const _findAPI = (obj) => {
            for (const key in obj) {
                if (
                    typeof obj[key] === 'object' &&
                    Object.prototype.hasOwnProperty.call(obj, key)
                ) {
                    if (key === 'gtagApiResult') {
                        if (typeof obj[key].client_id === 'string') {
                            clientID = obj[key].client_id;
                        } else {
                            return clientID;
                        }
                        break;
                    } else {
                        _findAPI(obj[key]);
                    }
                }
            }
        };

        try {
            if (typeof dataLayer === 'object') {
                dataLayer.forEach((layer) => {
                    _findAPI(layer);
                });
            }
        } catch (e) {
            // GA4
            window.dataLayer.push({
                event: 'log',
                label: 'getGtagClientID error: ' + e
            });
            return null;
        }

        return clientID;
    },

    /**
     * Returns a random identifier that we use to associate a
     * visitor's website GA data with their Telemetry attribution
     * data. This identifier is sent as a non-interaction event
     * to GA, and also to the stub attribution service as session_id.
     * @returns {String} session ID.
     */
    createSessionID: () => {
        return Math.floor(1000000000 + Math.random() * 9000000000).toString();
    },

    /**
     * A crude check to see if Google Analytics has loaded.
     * @param {Function} callback
     */
    waitForGoogleAnalyticsThen: (callback) => {
        let timeout;
        let pollRetry = 0;
        const interval = 100;
        const limit = 20; // (100 x 20) / 1000 = 2 seconds

        // Tries to get client IDs at a set interval
        const _checkGA = () => {
            clearTimeout(timeout);
            const clientIDGA4 = DownloadAttribution.getGtagClientID();

            if (clientIDGA4) {
                callback(true);
            } else {
                if (pollRetry <= limit) {
                    pollRetry += 1;
                    timeout = window.setTimeout(_checkGA, interval);
                } else {
                    if (clientIDGA4) {
                        callback(true);
                    } else {
                        callback(false);
                    }
                }
            }
        };

        _checkGA();
    },

    /**
     * Gets the forced campaign value used for essential attribution flows.
     * This value triggers specific functionality after download
     * i.e. "rtamo" redirects a user to install the extension they have chosen
     * whilst browsing AMO using a different browser.
     * @return {String | null} - Campaign value, or null if unset.
     */
    getEssentialCampaign: () => {
        return document.documentElement.getAttribute(
            'data-stub-attribution-campaign-force'
        );
    },

    /**
     * Gets the marketing campaign value: utm_campaign from the URL, falling
     * back to the page-level default campaign attribute.
     * @param {Object} params - URL params.
     * @return {String | null} - Campaign value, or null.
     */
    getMarketingCampaign: (params) => {
        const utms = params.utmParams();
        if (utms.utm_campaign !== undefined) {
            return utms.utm_campaign;
        }
        return document.documentElement.getAttribute(
            'data-stub-attribution-campaign'
        );
    },

    /**
     * Gets essential data for download.
     * Until the stub attribution service is updated to accept dedicated
     * essential fields, essential data carries its campaign in utm_campaign;
     * essential wins on key collisions with marketing when merged.
     * @return {Object} - Essential data object, or {} if the current page
     *   does not carry a recognized essential campaign.
     */
    getEssentialData: () => {
        // NOTE: in future, this will return product context and install
        // options fields based on data attributes.
        const campaign = DownloadAttribution.getEssentialCampaign();
        if (campaign) {
            return {
                utm_campaign: campaign
            };
        }
        return {};
    },

    /**
     * Gets marketing data for download. Requires GA4 wait.
     * @param {String} ref - Optional referrer to facilitate testing.
     * @param {Object} params - URL params.
     * @return {Object} - Marketing download attribution data object.
     */
    getMarketingData: (ref, params) => {
        const utms = params.utmParams();
        return {
            utm_source: utms.utm_source,
            utm_medium: utms.utm_medium,
            utm_campaign: DownloadAttribution.getMarketingCampaign(params),
            utm_content: utms.utm_content,
            referrer: typeof ref === 'string' ? ref : document.referrer,
            ua: DownloadAttribution.getUserAgent(),
            experiment: params.get('experiment'),
            variation: params.get('variation'),
            client_id_ga4: DownloadAttribution.getGtagClientID(),
            session_id: DownloadAttribution.createSessionID(),
            dlsource: DownloadAttribution.DLSOURCE
        };
    },

    hasValidData: (data) => {
        if (
            typeof data.utm_content === 'string' &&
            typeof data.referrer === 'string'
        ) {
            let content = data.utm_content;
            const charLimit = 150;

            // If utm_content is unusually long, return false early.
            if (content.length > charLimit) {
                return false;
            }

            // Attribution data can be double encoded
            while (content.indexOf('%') !== -1) {
                try {
                    const result = decodeURIComponent(content);
                    if (result === content) {
                        break;
                    }
                    content = result;
                } catch (e) {
                    break;
                }
            }

            // If RTAMO data does not originate from AMO, drop attribution (Issues 10337, 10524).
            if (
                /^rta:/.test(content) &&
                data.referrer.indexOf('https://addons.mozilla.org') === -1
            ) {
                return false;
            }
        }
        return true;
    },

    /**
     * Merges essential and marketing data and requests an updated signed
     * payload from the stub attribution service. Essential keys override
     * marketing on collision (today only utm_campaign collides; a pending
     * service update will give essential dedicated fields).
     * @param {Object | null} essential - Essential data, or null.
     * @param {Object | null} marketing - Marketing data, or null.
     */
    requestCombinedAuth: (essential, marketing) => {
        const combined = Object.assign({}, marketing || {}, essential || {});

        // Remove undefined / null values.
        for (const key of Object.keys(combined)) {
            if (
                typeof combined[key] === 'undefined' ||
                combined[key] === null
            ) {
                delete combined[key];
            }
        }

        if (Object.keys(combined).length === 0) {
            return;
        }

        if (!DownloadAttribution.hasValidData(combined)) {
            return;
        }

        DownloadAttribution.requestComplete = false;
        DownloadAttribution.requestAuthentication(combined);
    },

    /**
     * Determines if requirements for download attribution to work are satisfied.
     * Download attribution is only applicable to Windows/macOS users on desktop.
     * @return {Boolean}.
     */
    meetsFunctionalRequirements: () => {
        if (
            typeof window.site === 'undefined' ||
            typeof Mozilla.Cookies === 'undefined' ||
            typeof window._SearchParams === 'undefined'
        ) {
            return false;
        }

        if (!Mozilla.Cookies.enabled()) {
            return false;
        }

        if (!/windows|osx/i.test(window.site.platform)) {
            return false;
        }

        return true;
    },

    /**
     * Applies existing attribution data to download links. Safe to call on
     * every page; does nothing if no signed cookie is present.
     */
    applyAttributionDataToLinks: () => {
        if (!DownloadAttribution.meetsFunctionalRequirements()) {
            return;
        }

        if (DownloadAttribution.hasSignedCookie()) {
            const data = DownloadAttribution.getSignedCookie();
            DownloadAttribution.updateBouncerLinks(data);
        }
    },

    /**
     * Essential trigger entry point. Runs on pages that carry essential
     * download data (functional post-download behavior such as rtamo).
     * Does not gate on marketing consent or sample rate: essential data
     * must always be carried so the installer can deliver its promised
     * functionality after download.
     * @param {Function} successCallback - Optional.
     * @param {Function} timeoutCallback - Optional.
     */
    initEssential: (successCallback, timeoutCallback) => {
        if (!DownloadAttribution.meetsFunctionalRequirements()) {
            return;
        }

        if (typeof successCallback === 'function') {
            DownloadAttribution.successCallback = successCallback;
        }

        if (typeof timeoutCallback === 'function') {
            DownloadAttribution.timeoutCallback = timeoutCallback;
        }

        const essential = DownloadAttribution.getEssentialData();

        if (Object.keys(essential).length === 0) {
            return;
        }

        const marketing = DownloadAttribution.getRawCookie(
            DownloadAttribution.COOKIE_MARKETING_RAW_ID
        );

        DownloadAttribution.setRawCookie(
            DownloadAttribution.COOKIE_ESSENTIAL_RAW_ID,
            essential
        );

        DownloadAttribution.requestCombinedAuth(essential, marketing);
    },

    /**
     * Marketing trigger entry point. Called in response to a GTM
     * `gtm-marketing-consent` event. On 'granted', captures marketing data
     * from the current URL and re-signs the combined payload. On 'denied',
     * clears marketing data; if essential data is also absent, the full
     * attribution state is removed.
     * @param {String} consentState - 'granted' or 'denied'.
     * @param {Function} successCallback - Optional.
     * @param {Function} timeoutCallback - Optional.
     */
    initMarketing: (consentState, successCallback, timeoutCallback) => {
        if (!DownloadAttribution.meetsFunctionalRequirements()) {
            return;
        }

        if (typeof successCallback === 'function') {
            DownloadAttribution.successCallback = successCallback;
        }

        if (typeof timeoutCallback === 'function') {
            DownloadAttribution.timeoutCallback = timeoutCallback;
        }

        if (consentState === 'granted') {
            if (!DownloadAttribution.withinAttributionRate()) {
                return;
            }

            DownloadAttribution.waitForGoogleAnalyticsThen(() => {
                const params = new window._SearchParams();
                const marketing = DownloadAttribution.getMarketingData(
                    null,
                    params
                );

                DownloadAttribution.setRawCookie(
                    DownloadAttribution.COOKIE_MARKETING_RAW_ID,
                    marketing
                );

                const essential = DownloadAttribution.getRawCookie(
                    DownloadAttribution.COOKIE_ESSENTIAL_RAW_ID
                );

                DownloadAttribution.requestCombinedAuth(essential, marketing);

                if (marketing.client_id_ga4) {
                    window.dataLayer.push({
                        event: 'stub_session_set',
                        id: marketing.session_id
                    });
                }
            });
        } else if (consentState === 'denied') {
            DownloadAttribution.removeRawCookie(
                DownloadAttribution.COOKIE_MARKETING_RAW_ID
            );

            const essential = DownloadAttribution.getRawCookie(
                DownloadAttribution.COOKIE_ESSENTIAL_RAW_ID
            );

            if (essential) {
                DownloadAttribution.requestCombinedAuth(essential, null);
            } else {
                DownloadAttribution.removeAttributionData();
            }
        }
    }
};

window.Mozilla.DownloadAttribution = DownloadAttribution;

export default DownloadAttribution;
