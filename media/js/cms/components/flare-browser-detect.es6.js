/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Coarse detection of the visitor's browser.
 *
 * Every Chromium-based browser also reports "Chrome" in its user agent, and every
 * iOS browser is a WebKit wrapper reporting "Safari", so the order of these
 * checks matters: branded browsers have to be ruled out first, and Safari has to
 * come last. Browsers we have no comparison for return 'other' rather than
 * falling through to 'chrome' or 'safari', so callers fall back instead of
 * matching the wrong thing.
 *
 * Detection is best-effort, and 'safari' is the weakest answer it gives: it is
 * whatever WebKit is left after the known brands are excluded. A branded iOS
 * browser we don't know about - or an in-app webview such as Facebook's or
 * Instagram's - is reported as Safari rather than 'other'.
 *
 * Brave is deliberately indistinguishable from Chrome here - it ships Chrome's
 * user agent verbatim. Use isBrave() for that.
 *
 * @param {String} ua - Optional user agent string, to facilitate testing.
 * @returns {String} One of 'firefox', 'edge', 'opera', 'chrome', 'safari', 'other'.
 */
export const detectBrowser = function (ua) {
    ua = typeof ua !== 'undefined' ? ua : navigator.userAgent;

    // Firefox forks and iOS Firefox. Same exclusion list as site.isFirefox().
    if (
        /\s(Firefox|FxiOS)/.test(ua) &&
        !/Iceweasel|IceCat|SeaMonkey|Camino|like Firefox/i.test(ua)
    ) {
        return 'firefox';
    }

    // EdgA on Android, EdgiOS on iOS. Legacy Edge/EdgeHTML used "Edge".
    if (/Edg\/|EdgA\/|EdgiOS\/|Edge\//.test(ua)) {
        return 'edge';
    }

    // OPR on desktop and Android, OPT/OPiOS on iOS.
    if (/OPR\/|OPT\/|OPiOS\/|Opera Mini|Opera\//.test(ua)) {
        return 'opera';
    }

    // Branded browsers we have no comparison for. They have to be ruled out
    // before the Chrome and Safari checks below, because they all borrow one of
    // those two tokens: Chromium forks carry "Chrome", and on iOS every browser
    // is a WebKit wrapper carrying "Safari". Left to fall through they would be
    // reported as the browser they are built on rather than falling back.
    if (
        /Vivaldi|YaBrowser|SamsungBrowser|Whale|DuckDuckGo|Focus\/|Klar\/|Puffin/.test(
            ua
        )
    ) {
        return 'other';
    }

    // CriOS is Chrome on iOS.
    if (/Chrome\/|Chromium\/|CriOS\//.test(ua)) {
        return 'chrome';
    }

    // Best-effort Safari. This is a catch-all, not a positive identification:
    // genuine Safari and an unrecognised WebKit wrapper are indistinguishable
    // here, since the wrappers append their own token but keep Safari's intact.
    // A branded iOS browser missing from the list above is therefore read as
    // Safari - the failure mode is a plausible neighbouring tab, not a crash, so
    // it is left as a known limitation rather than guessed at more aggressively.
    if (/Safari\//.test(ua)) {
        return 'safari';
    }

    return 'other';
};

/**
 * Detect Brave, which reports Chrome's user agent verbatim and can only be
 * identified by the API it injects.
 *
 * @returns {Promise<Boolean>} Resolves false when the API is missing or throws.
 */
export const isBrave = function () {
    return new Promise(function (resolve) {
        try {
            if (
                !navigator.brave ||
                typeof navigator.brave.isBrave !== 'function'
            ) {
                resolve(false);
                return;
            }
            navigator.brave.isBrave().then(
                function (result) {
                    resolve(Boolean(result));
                },
                function () {
                    resolve(false);
                }
            );
        } catch (e) {
            resolve(false);
        }
    });
};
