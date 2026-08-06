/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * On mobile UAs, rewrites /thanks/-bound download buttons to attributed
 * store URLs so the page-level campaign survives the click, and fires the
 * same firefox_mobile_download GA4 event /thanks/ fires today. Desktop is
 * unaffected. Campaign cascade mirrors stub-attribution.js:
 * force > override > URL utm_campaign > default.
 */

if (typeof window.Mozilla === 'undefined') {
    window.Mozilla = {};
}

(function (Mozilla) {
    'use strict';

    var MobileAttribution = {};

    var ANDROID_RE = /\bAndroid\b/i;
    var IOS_RE = /\b(iPhone|iPad|iPod)\b/i;

    // Fallback campaign for mobile users with no campaign declared on the
    // page or in the URL. Distinct from "download" (the value baked into
    // the server-rendered Path A Play Store URL) so attribution dashboards
    // can tell "firefox.com mobile fallback" apart from explicit campaigns
    // named "download".
    var DEFAULT_CAMPAIGN = 'fxcomdefault';

    /**
     * Resolve the campaign value: force > override > URL utm_campaign > default.
     * IE9-safe parse avoids URLSearchParams.
     * @param {HTMLElement} html
     * @param {String} search
     * @returns {String|null}
     */
    MobileAttribution.getCampaign = function (html, search) {
        var urlMatch = (search || '').match(/[?&]utm_campaign=([^&]+)/);
        var urlCampaign = urlMatch ? decodeURIComponent(urlMatch[1]) : null;

        return (
            html.getAttribute('data-stub-attribution-campaign-force') ||
            html.getAttribute('data-stub-attribution-campaign-override') ||
            urlCampaign ||
            html.getAttribute('data-stub-attribution-campaign') ||
            null
        );
    };

    /**
     * Build an attributed store URL byte-identical to what
     * springfield/firefox/templatetags/misc.py app_store_url / play_store_url
     * emits server-side.
     * @param {String} campaign - utm_campaign value.
     * @param {Boolean} isAndroid - True for Android/Play Store, false for iOS/App Store.
     * @param {String} [referralContent] - Optional utm_content for referral attribution
     *   (e.g. "fxrefer:1HR4FZ672Z8Y0E4HW"). When provided, appended to the Android
     *   Play Store referrer string. Has no effect on iOS.
     */
    MobileAttribution.getStoreUrl = function (
        campaign,
        isAndroid,
        referralContent
    ) {
        var encoded = encodeURIComponent(campaign);
        if (isAndroid) {
            var url =
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox' +
                '&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral' +
                '%26utm_campaign%3D' +
                encoded;
            if (referralContent) {
                url +=
                    '%26utm_content%3D' + encodeURIComponent(referralContent);
            }
            return url;
        }
        return (
            'https://apps.apple.com/app/apple-store/id989804926' +
            '?mz_pr=firefox_mobile&pt=373246&ct=' +
            encoded +
            '&mt=8'
        );
    };

    /**
     * Rewrite /thanks/-bound download buttons to the given attributed store
     * URL and attach click tracking. Selector covers the two CTA shapes:
     *   - .c-button-download-thanks-link (exclude_unsupported_content=false)
     *   - .c-button-download-thanks > .download-link (nav + pre-footer pattern)
     * Path A store buttons (.fl-store-button-*) are not matched.
     */
    MobileAttribution.rewriteLinks = function (root, storeUrl) {
        var buttons = root.querySelectorAll(
            '.c-button-download-thanks-link, .c-button-download-thanks > .download-link'
        );
        for (var i = 0; i < buttons.length; i++) {
            var href = buttons[i].getAttribute('href') || '';
            if (href.indexOf('/thanks') === -1) continue;

            buttons[i].setAttribute('href', storeUrl);

            if (
                window.Mozilla &&
                window.Mozilla.TrackProductDownload &&
                typeof window.Mozilla.TrackProductDownload.sendEventFromURL ===
                    'function'
            ) {
                MobileAttribution._attachTrackingClick(buttons[i], storeUrl);
            }
        }
    };

    /**
     * Click handler: fire the GA4 + legacy download events and navigate to
     * the closure-captured https:// URL. We navigate via JS (mirroring
     * auto-download.js) because mozilla-utils.js mutates Android Play Store
     * hrefs to `market://details?...` on DOM ready — that scheme works on
     * real Android but fails in desktop browsers, breaking dev testing.
     * The https:// URL works in both contexts (Android App Links open the
     * Play Store app; browsers load the web page).
     */
    MobileAttribution._attachTrackingClick = function (button, storeUrl) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            // Prefer the element's current href if it has been rewritten to an
            // https://play.google.com URL after this listener was bound (e.g. by
            // referral attribution). Fall back to the captured storeUrl — which
            // may be a market:// URL set by initMobileDownloadLinks — otherwise.
            var currentHref = button.getAttribute('href') || '';
            var url =
                currentHref.indexOf('https://play.google.com') === 0
                    ? currentHref
                    : storeUrl;
            window.Mozilla.TrackProductDownload.sendEventFromURL(url);
            MobileAttribution._navigate(url);
        });
    };

    /** Navigation seam — separated so tests can spy without navigating. */
    MobileAttribution._navigate = function (url) {
        window.location.href = url;
    };

    /**
     * Entry point. No-op on desktop. On mobile:
     *   1. Android-only: supplement the existing .ga-product-download click
     *      handler on Path A Play Store badges (CMS download_firefox_button
     *      block). The existing handler reads event.target.href, which
     *      mozilla-utils.js has mutated to market://details?... by click time,
     *      and the tracker's marketURL regex doesn't recognize that shape —
     *      so the event silently drops. We supplement with a handler using
     *      the captured https:// URL. iOS Path A is unaffected and not
     *      supplemented (would double-fire).
     *   2. Path B: rewrite /thanks/-bound CTAs to attributed store URLs.
     *      Falls back to DEFAULT_CAMPAIGN when no campaign is declared so
     *      mobile users never route through /thanks/, which renders desktop-
     *      stub-installer copy and serves no purpose pre-install on mobile.
     */
    MobileAttribution.init = function () {
        var html = document.documentElement;
        var ua = navigator.userAgent || '';
        var isAndroid = ANDROID_RE.test(ua);
        var isIOS = IOS_RE.test(ua);
        if (!isAndroid && !isIOS) {
            return;
        }

        if (isAndroid) {
            MobileAttribution.attachAndroidStoreButtonTracking(document);
        }

        var campaign =
            MobileAttribution.getCampaign(html, window.location.search) ||
            DEFAULT_CAMPAIGN;

        var storeUrl = MobileAttribution.getStoreUrl(campaign, isAndroid);
        MobileAttribution.rewriteLinks(document, storeUrl);
    };

    /** Path A Android-only supplement (see init docstring for rationale). */
    MobileAttribution.attachAndroidStoreButtonTracking = function (root) {
        if (
            !window.Mozilla ||
            !window.Mozilla.TrackProductDownload ||
            typeof window.Mozilla.TrackProductDownload.sendEventFromURL !==
                'function'
        ) {
            return;
        }
        var buttons = root.querySelectorAll('.fl-store-button-android');
        for (var i = 0; i < buttons.length; i++) {
            var href = buttons[i].getAttribute('href');
            if (!href) continue;
            MobileAttribution._attachTrackingClick(buttons[i], href);
        }
    };

    Mozilla.MobileAttribution = MobileAttribution;

    // Auto-run unless a test or another caller suppresses it.
    if (!Mozilla.MobileAttribution.suppressAutoInit) {
        MobileAttribution.init();
    }
})(window.Mozilla);
