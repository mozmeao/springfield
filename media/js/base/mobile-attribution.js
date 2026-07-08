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
     */
    MobileAttribution.getStoreUrl = function (campaign, isAndroid) {
        var encoded = encodeURIComponent(campaign);
        if (isAndroid) {
            return (
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox' +
                '&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral' +
                '%26utm_campaign%3D' +
                encoded
            );
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
            window.Mozilla.TrackProductDownload.sendEventFromURL(storeUrl);
            MobileAttribution._navigate(storeUrl);
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
     *      Gated on a declared campaign (CMS stub_attr or URL utm_campaign).
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

        var campaign = MobileAttribution.getCampaign(
            html,
            window.location.search
        );
        if (!campaign) {
            return;
        }

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
