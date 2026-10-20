/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Picks the visitor's state on the partner download page and, when the
 * partner has a build for this system and language, starts that download.
 * The server renders one block per possible state; this sets `data-state`
 * on the container so CSS shows the matching one.
 */

import Plausible from '../../base/plausible/plausible.es6';

const PartnerDownload = {};

// How long to wait for client hints to report 64-bit Windows.
PartnerDownload.BITNESS_CAP_MS = 500;
// The download starts this long after DOM ready, as on /thanks/.
PartnerDownload.DOWNLOAD_DELAY_MS = 1000;
// The latest the download starts while waiting for attribution signing.
PartnerDownload.ATTRIBUTION_CAP_MS = 2000;

/**
 * Choose the Windows build. A 64-bit build only goes to a machine detected as 64-bit.
 * @param {Boolean} x64 - whether the machine was detected as 64-bit.
 * @param {Object} links - partner links keyed by `os` (`win64`, `win`).
 * @returns {Object|null} the link to download, or null.
 */
PartnerDownload.chooseWindowsLink = (x64, links) => {
    if (x64) {
        return links.win64 || links.win || null;
    }
    return links.win || null;
};

/**
 * Work out which state to show. The first match wins.
 * @param {Object} signals - `platform`, `isFirefox`, `fxSupported`, `x64`.
 * @param {Object} options - per-platform `state` plus partner `links` keyed by `os`.
 * @returns {Object} `state` (1-10), with `reason` when no partner build is offered,
 *     or `link` for a partner download.
 */
PartnerDownload.getState = (signals, options) => {
    const platform = signals.platform;
    const isDesktopRepackPlatform =
        platform === 'windows' || platform === 'osx';

    if (platform === 'android' || platform === 'ios') {
        return { state: 1, reason: 'device' };
    }
    if (signals.isFirefox) {
        return { state: 2, reason: 'firefox' };
    }
    if (isDesktopRepackPlatform && signals.fxSupported === false) {
        return { state: 3, reason: 'unsupported_os' };
    }
    if (isDesktopRepackPlatform) {
        const option = platform === 'windows' ? options.windows : options.mac;
        if (option.state === 'available') {
            const link =
                platform === 'windows'
                    ? PartnerDownload.chooseWindowsLink(
                          signals.x64,
                          options.links
                      )
                    : options.links.osx || null;
            return link
                ? { state: 4, link: link }
                : { state: 6, reason: 'device' };
        }
        return option.state === 'language'
            ? { state: 5, reason: 'language' }
            : { state: 6, reason: 'device' };
    }
    if (platform === 'linux') {
        if (options.linux.state === 'available') {
            return { state: 7 };
        }
        return options.linux.state === 'language'
            ? { state: 8, reason: 'language' }
            : { state: 9, reason: 'device' };
    }
    return { state: 10, reason: 'device' };
};

/**
 * Read each platform's state and the partner links from the page.
 * @param {HTMLElement} container
 * @returns {Object} options for `getState`.
 */
PartnerDownload.readOptions = (container) => {
    const links = {};
    for (const link of container.querySelectorAll(
        '.c-partner-download-links a[data-download-version]'
    )) {
        links[link.getAttribute('data-download-version')] = link;
    }
    return {
        windows: { state: container.getAttribute('data-windows') },
        mac: { state: container.getAttribute('data-mac') },
        linux: { state: container.getAttribute('data-linux') },
        links: links
    };
};

/**
 * Wait for client hints to report the machine's bitness, up to `capMs`.
 * `site.js` reads the same hints but doesn't announce when they arrive.
 * @param {Number} capMs
 * @returns {Promise<Boolean>} whether the machine counts as 64-bit.
 */
PartnerDownload.waitForBitness = (capMs = PartnerDownload.BITNESS_CAP_MS) => {
    const site = window.site;
    const currentlyX64 = () => site.archSize === 64;
    const userAgentData = navigator.userAgentData;

    if (
        !userAgentData ||
        typeof userAgentData.getHighEntropyValues !== 'function'
    ) {
        return Promise.resolve(currentlyX64());
    }

    return new Promise((resolve) => {
        const timer = setTimeout(() => resolve(currentlyX64()), capMs);
        userAgentData.getHighEntropyValues(['bitness']).then(
            (values) => {
                clearTimeout(timer);
                resolve(site.getArchSizeClientHint(values.bitness) === 64);
            },
            () => {
                clearTimeout(timer);
                resolve(currentlyX64());
            }
        );
    });
};

/**
 * Wait for attribution signing that's in progress on this page, up to `capMs`.
 * Resolves at once when nothing is signing, for example without consent.
 * @param {Number} capMs
 * @returns {Promise<String|null>} 'success' or 'timeout' when it waited, otherwise null.
 */
PartnerDownload.waitForAttribution = (
    capMs = PartnerDownload.ATTRIBUTION_CAP_MS
) => {
    if (
        document.documentElement.getAttribute('data-download-attribution') !==
        'pending'
    ) {
        return Promise.resolve(null);
    }

    return new Promise((resolve) => {
        const finish = (status) => {
            clearTimeout(timer);
            window.removeEventListener('mozDownloadAttribution', onSigned);
            window.dataLayer.push({
                event: 'widget_action',
                type: 'direct-attribution',
                action: status,
                non_interaction: true
            });
            resolve(status);
        };
        const onSigned = (event) =>
            finish(event.detail.status === 'success' ? 'success' : 'timeout');

        window.addEventListener('mozDownloadAttribution', onSigned);
        const timer = setTimeout(() => finish('timeout'), capMs);
    });
};

/**
 * Add the signed attribution parameters to a partner download URL, replacing
 * any already there. Returns the URL unchanged when there's nothing to add.
 * @param {String} url
 * @returns {String}
 */
PartnerDownload.getAttributedURL = (url) => {
    const attribution = window.Mozilla.DownloadAttribution;
    if (
        !attribution ||
        !attribution.meetsFunctionalRequirements() ||
        !attribution.hasSignedCookie()
    ) {
        return url;
    }
    return attribution.appendToDownloadURL(
        attribution.removeLinkAttributionParams(url),
        attribution.getSignedCookie()
    );
};

/**
 * Record that the visitor can't get the partner's build, and why.
 * Sent to the dataLayer and to Plausible as `partner_download_unavailable`.
 * @param {HTMLElement} container
 * @param {String} reason - 'language', 'device', 'firefox' or 'unsupported_os'.
 */
PartnerDownload.sendUnavailableEvent = (container, reason) => {
    const platform = window.site.platform;
    const props = {
        partner: container.getAttribute('data-partner'),
        platform: platform === 'osx' ? 'macos' : platform,
        download_language: container.getAttribute('data-lang'),
        reason: reason
    };

    try {
        window.dataLayer.push(
            Object.assign({ event: 'partner_download_unavailable' }, props, {
                non_interaction: true
            })
        );
        Plausible.trackEvent('partner_download_unavailable', props);
    } catch (error) {
        // Analytics must never block the page.
    }
};

/**
 * Go to the download URL.
 * @param {String} url
 */
PartnerDownload.navigate = (url) => {
    window.location.href = url;
};

/**
 * Track and start the partner download, and point "try again" at the same URL.
 * @param {HTMLElement} link - the chosen partner link.
 * @returns {String} the URL that was downloaded.
 */
PartnerDownload.startDownload = (link) => {
    const url = PartnerDownload.getAttributedURL(link.href);
    const tryAgain = document.getElementById('partner-download-try-again');

    if (tryAgain) {
        tryAgain.href = url;
        tryAgain.addEventListener('click', (event) => {
            try {
                window.Mozilla.TrackProductDownload.handleLink(event);
            } catch (error) {
                return;
            }
        });
    }

    try {
        window.Mozilla.TrackProductDownload.sendEventFromURL(url);
    } catch (error) {
        // Tracking must never block the download.
    }

    PartnerDownload.navigate(url);
    return url;
};

/**
 * Pick and show the state, then start the partner download when there is one.
 * Call on DOM ready: the download delay and the attribution cap both run from here.
 * @returns {Promise<Object>} the chosen state.
 */
PartnerDownload.begin = () => {
    const container = document.querySelector('.c-partner-download');
    if (!container) {
        return Promise.resolve(null);
    }

    const site = window.site;
    const startedAt = Date.now();
    const remaining = (ms) => Math.max(0, ms - (Date.now() - startedAt));
    const bitness =
        site.platform === 'windows'
            ? PartnerDownload.waitForBitness()
            : Promise.resolve(site.archSize === 64);

    return bitness.then((x64) => {
        const result = PartnerDownload.getState(
            {
                platform: site.platform,
                isFirefox: site.isFirefox(),
                fxSupported: site.fxSupported,
                x64: x64
            },
            PartnerDownload.readOptions(container)
        );
        container.setAttribute('data-state', result.state);

        if (result.reason) {
            PartnerDownload.sendUnavailableEvent(container, result.reason);
        }

        if (result.state !== 4) {
            return result;
        }

        const delay = new Promise((resolve) =>
            setTimeout(resolve, remaining(PartnerDownload.DOWNLOAD_DELAY_MS))
        );
        const attribution = PartnerDownload.waitForAttribution(
            remaining(PartnerDownload.ATTRIBUTION_CAP_MS)
        );

        return Promise.all([delay, attribution]).then(() => {
            PartnerDownload.startDownload(result.link);
            return result;
        });
    });
};

export default PartnerDownload;
