/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Mobile attribution: rewrites /thanks/-bound download buttons to attributed
 * store URLs on mobile UAs so the page-level campaign survives the click.
 * Desktop is unaffected — those clicks continue through the stub-attribution
 * cookie/installer flow.
 *
 * Campaign resolution mirrors stub-attribution.js exactly:
 *   force > override > URL utm_campaign > default.
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
     * Resolve the campaign value using the same cascade as stub-attribution.js:
     * force > override > URL utm_campaign > default.
     * @param {HTMLElement} html - typically document.documentElement.
     * @param {String} search - typically window.location.search.
     * @returns {String|null}
     */
    MobileAttribution.getCampaign = function (html, search) {
        // IE9-safe URL parse (avoids URLSearchParams).
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
     * Build the attributed store URL for the given campaign + platform.
     * Mirrors springfield/firefox/templatetags/misc.py app_store_url /
     * play_store_url so the rewritten URL is byte-identical to what the CMS
     * download_firefox_button block emits server-side.
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
     * Find /thanks/-bound download buttons, rewrite their HREFs to the given
     * store URL, and attach a click handler that fires the
     * `firefox_mobile_download` + legacy `product_download` GA4 events that
     * /thanks/ would have fired today (via thanks-init.js calling
     * sendEventFromURL after the auto-redirect).
     *
     * Selector covers both shapes:
     *   - `.c-button-download-thanks-link` (set on buttons when
     *     exclude_unsupported_content is False)
     *   - `.c-button-download-thanks > .download-link` (the broader pattern,
     *     covers nav + pre-footer where exclude_unsupported_content is True
     *     and the `-link` class is omitted)
     * Path A store buttons (rendered by show_store_button) use
     * `.fl-store-button-*` classes and are not matched.
     *
     * Why sendEventFromURL with a closure-captured URL (vs. attaching
     * handleLink directly): mozilla-utils.js's initMobileDownloadLinks
     * mutates Android Play Store hrefs to `market://details?...` on DOM
     * ready. TrackProductDownload's marketURL regex requires the URL to
     * start with `market://play.google.com` (which mozilla-utils.js never
     * produces), so reading event.target.href at click time would not
     * match. Capturing the original https:// URL bypasses the regex
     * mismatch entirely.
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
     * Attach a click listener that fires the GA4 + legacy download events
     * AND navigates to the closure-captured https:// store URL.
     *
     * Why navigate via JS instead of letting the browser follow the HREF:
     * mozilla-utils.js mutates Android Play Store hrefs to `market://...`
     * on DOM ready. `market://` resolves correctly on real Android (the
     * Play Store app is registered for the scheme) but fails in desktop
     * browsers (including Chrome with Android UA emulation), surfacing a
     * "scheme has no registered handler" error and breaking dev testing.
     *
     * Navigating to the https:// URL works in both contexts: on real
     * Android, Android App Links open the Play Store app from the https
     * URL automatically; in any browser, it loads play.google.com /
     * apps.apple.com directly. This mirrors how thanks-init.js navigates
     * via window.location.href after capturing the URL synchronously, so
     * /thanks/ has been graceful in both environments today.
     *
     * Factored out so the closure over `storeUrl` is created per-button
     * (avoids the classic `var i` loop-closure trap).
     */
    MobileAttribution._attachTrackingClick = function (button, storeUrl) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            window.Mozilla.TrackProductDownload.sendEventFromURL(storeUrl);
            MobileAttribution._navigate(storeUrl);
        });
    };

    /**
     * Navigation seam. Factored into a named method so tests can spy on it
     * without actually navigating the test runner away from its harness.
     */
    MobileAttribution._navigate = function (url) {
        window.location.href = url;
    };

    /**
     * Entry point. Strict no-op on desktop UAs.
     *
     * Two responsibilities on mobile:
     *   1. Path A: ensure Android clicks on CMS download_firefox_button
     *      store buttons fire the firefox_mobile_download GA4 event. The
     *      existing datalayer-productdownload-init.es6.js attaches
     *      handleLink to all `.ga-product-download` elements, but on
     *      Android the href has been mutated to `market://details?...` by
     *      DOM-ready time and the tracker's marketURL regex doesn't match
     *      it, so the event silently drops. (iOS Path A is unaffected:
     *      mozilla-utils.js only mutates Android URLs, so the existing
     *      handler fires the event correctly.) We supplement Android with
     *      a handler that uses the captured https:// URL.
     *   2. Path B: rewrite /thanks/-bound download CTAs (nav, pre-footer,
     *      smart-window, etc.) to attributed store URLs and attach click
     *      tracking. Gated on a campaign being declared (CMS stub_attr or
     *      URL utm_campaign).
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

    /**
     * Path A Android fix. Supplements the existing handleLink listener
     * (attached by datalayer-productdownload-init.es6.js to all
     * `.ga-product-download` elements) with one that uses the captured
     * https://play.google.com URL, since by click time the href has been
     * mutated to market://details?... by mozilla-utils.js — which the
     * tracker's marketURL regex doesn't recognize. Selector intentionally
     * matches Android only; iOS Path A already fires correctly via the
     * existing handler, and adding ours there would double-fire.
     */
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
