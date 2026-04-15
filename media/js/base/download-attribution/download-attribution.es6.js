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
 * Refactor task: https://mozilla-hub.atlassian.net/browse/WT-964
 * In 2026, this file was renamed from Stub Attribution to Download Attribution to more
 * clearly indicate this is information provided through the download. References to the Stub
 * Attribution Service remain as the website code connects to an external service that uses
 * this name: https://github.com/mozilla-services/stubattribution.
 */
const DownloadAttribution = {
    COOKIE_CODE_ID: 'moz-download-attribution-code',
    COOKIE_SIGNATURE_ID: 'moz-download-attribution-sig',
    DLSOURCE: 'fxdotcom',

    /**
     * Experiment name and variation globals. These values can be set directly by a
     * page's JS instead of relying on supplied URL query parameters.
     */
    experimentName: undefined,
    experimentVariation: undefined,

    /**
     * Custom event handler callback globals. These can be defined as functions when
     * calling DownloadAttribution.init();
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
            .getAttribute('data-download-attribution-rate');
        return isNaN(rate) || !rate
            ? 0
            : Math.min(Math.max(parseFloat(rate), 0), 1);
    },

    /**
     * Returns true if both cookies exist.
     * @return {Boolean} data.
     */
    hasCookie: () => {
        return (
            Mozilla.Cookies.hasItem(DownloadAttribution.COOKIE_CODE_ID) &&
            Mozilla.Cookies.hasItem(DownloadAttribution.COOKIE_SIGNATURE_ID)
        );
    },

    /**
     * Stores a cookie with download attribution data values.
     * @param {Object} data - attribution_code, attribution_sig.
     */
    setCookie: (data) => {
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
     * Removes download attribution cookie.
     */
    removeCookie: () => {
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
     * Gets download attribution data from cookie.
     * @return {Object} - attribution_code, attribution_sig.
     */
    getCookie: () => {
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
            !DownloadAttribution.meetsRequirements()
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
        DownloadAttribution.removeCookie();
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
            DownloadAttribution.setCookie(data);

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
     * Gets utm parameters and referrer information from the web page if they exist.
     * @param {String} ref - Optional referrer to facilitate testing.
     * @param {Boolean} omitNonEssentialFields - Optional flag to omit fields that are nonEssential.
     * @return {Object} - Download attribution data object.
     */
    getAttributionData: (ref, omitNonEssentialFields) => {
        const params = new window._SearchParams();
        const utms = params.utmParams();
        const experiment = omitNonEssentialFields
            ? null
            : params.get('experiment') || DownloadAttribution.experimentName;
        const variation = omitNonEssentialFields
            ? null
            : params.get('variation') ||
              DownloadAttribution.experimentVariation;
        const referrer = typeof ref === 'string' ? ref : document.referrer;
        const ua = omitNonEssentialFields
            ? 'other'
            : DownloadAttribution.getUserAgent();
        const clientIDGA4 = omitNonEssentialFields
            ? null
            : DownloadAttribution.getGtagClientID();

        const campaignForce = document.documentElement.getAttribute(
            'data-download-attribution-campaign-force'
        );
        const campaignOverride = document.documentElement.getAttribute(
            'data-download-attribution-campaign-override'
        );
        const campaignDefault = document.documentElement.getAttribute(
            'data-download-attribution-campaign'
        );
        let utmCampaign;

        if (campaignForce !== null) {
            // Force always wins and clears existing cookie
            utmCampaign = campaignForce;
        } else if (campaignOverride !== null) {
            // Explicit override via data attribute
            utmCampaign = campaignOverride;
        } else if (
            typeof utms.utm_campaign !== 'undefined' &&
            utms.utm_campaign !== null
        ) {
            // URL param wins over default data attribute, even if falsy like 0
            utmCampaign = utms.utm_campaign;
        } else {
            utmCampaign = campaignDefault;
        }

        const data = {
            utm_source: utms.utm_source,
            utm_medium: utms.utm_medium,
            utm_campaign: utmCampaign,
            utm_content: utms.utm_content,
            referrer: referrer,
            ua: ua,
            experiment: experiment,
            variation: variation,
            client_id_ga4: clientIDGA4,
            session_id: clientIDGA4
                ? DownloadAttribution.createSessionID()
                : null,
            dlsource: DownloadAttribution.DLSOURCE
        };

        // Remove any undefined values.
        for (const key of Object.keys(data)) {
            if (typeof data[key] === 'undefined' || data[key] === null) {
                delete data[key];
            }
        }

        return data;
    },

    checkDataAndRequestAuth: (omitNonEssentialFields = false) => {
        // get attribution data
        const data = DownloadAttribution.getAttributionData(
            null,
            omitNonEssentialFields
        );

        if (
            data &&
            DownloadAttribution.withinAttributionRate() &&
            DownloadAttribution.hasValidData(data)
        ) {
            // if data is valid and we are in sample rate:
            // request authentication from stub attribution service
            DownloadAttribution.requestAuthentication(data);

            // Send the session ID to GA4
            if (!omitNonEssentialFields && data.client_id_ga4) {
                window.dataLayer.push({
                    event: 'stub_session_set',
                    id: data.session_id
                });
            }
        }
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
     * Determine if the current page is /download/thanks
     * This is needed as /thanks auto-initiates the download. There is little point
     * trying to make an XHR request here before the download begins, and we don't
     * want to make the request a dependency on the download starting.
     * @return {Boolean}.
     */
    isFirefoxDownloadThanks: (location) => {
        location =
            typeof location !== 'undefined' ? location : window.location.href;
        return location.indexOf('/thanks/') > -1;
    },

    /**
     * Determines if requirements for download attribution to work are satisfied.
     * Download attribution is only applicable to Windows/macOS users on desktop.
     * @return {Boolean}.
     */
    meetsRequirements: () => {
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
     * Determines whether to make a request to the stub authentication service.
     */
    init: (
        successCallback,
        timeoutCallback,
        omitNonEssentialFields = false
    ) => {
        let data = {};

        if (!DownloadAttribution.meetsRequirements()) {
            return;
        }

        // Support custom callback functions for success and timeout.
        if (typeof successCallback === 'function') {
            DownloadAttribution.successCallback = successCallback;
        }

        if (typeof timeoutCallback === 'function') {
            DownloadAttribution.timeoutCallback = timeoutCallback;
        }

        /**
         * If the page forces a campaign value, invalidate any
         * existing cookie so the forced value is picked up.
         */
        if (
            DownloadAttribution.hasCookie() &&
            document.documentElement.getAttribute(
                'data-download-attribution-campaign-force'
            )
        ) {
            DownloadAttribution.removeCookie();
        }

        /**
         * If cookie already exists, update download links on the page,
         * else make a request to the service if within attribution rate.
         */
        if (DownloadAttribution.hasCookie()) {
            data = DownloadAttribution.getCookie();
            DownloadAttribution.updateBouncerLinks(data);
            // As long as the user is not already on the automatic download page,
            // make the XHR request to the stub authentication service.
        } else if (!DownloadAttribution.isFirefoxDownloadThanks()) {
            if (omitNonEssentialFields) {
                // Skip GA4 wait if we're only doing essential fields
                DownloadAttribution.checkDataAndRequestAuth(
                    omitNonEssentialFields
                );
            } else {
                // Wait for GA4 to load and return client IDs
                DownloadAttribution.waitForGoogleAnalyticsThen(() => {
                    DownloadAttribution.checkDataAndRequestAuth(
                        omitNonEssentialFields
                    );
                });
            }
        }
    }
};

window.Mozilla.DownloadAttribution = DownloadAttribution;

export default DownloadAttribution;
