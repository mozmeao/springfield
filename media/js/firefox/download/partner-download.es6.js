/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Picks the visitor's state on /get/ and starts the partner download when there is one.

import Plausible from '../../base/plausible/plausible.es6';

const PartnerDownload = {};

PartnerDownload.BITNESS_CAP_MS = 500;
PartnerDownload.DOWNLOAD_DELAY_MS = 1000;
PartnerDownload.ATTRIBUTION_CAP_MS = 2000;

/**
 * Pick the Windows link; 64-bit only goes to a machine detected as 64-bit.
 * @param {Boolean} x64
 * @param {Object} links - keyed by `os`
 * @returns {Object|null}
 */
PartnerDownload.chooseWindowsLink = (x64, links) => {
    if (x64) {
        return links.win64 || links.win || null;
    }
    return links.win || null;
};

/**
 * Pick the state to show; the first match wins.
 * @param {Object} signals - `platform`, `isFirefox`, `fxSupported`, `x64`
 * @param {Object} options - per-platform `state` and `links` keyed by `os`
 * @returns {Object} `state`, plus `reason` or the partner `link`
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
 * @returns {Object}
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
 * Resolve whether the machine is 64-bit, waiting up to `capMs` for client hints.
 * @param {Number} capMs
 * @returns {Promise<Boolean>}
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
 * Wait up to `capMs` for attribution signing in progress; resolves at once if none.
 * @param {Number} capMs
 * @returns {Promise<String|null>} 'success', 'timeout', or null if it didn't wait
 */
PartnerDownload.waitForAttribution = (
    capMs = PartnerDownload.ATTRIBUTION_CAP_MS
) => {
    const attribution = window.Mozilla.DownloadAttribution;
    const signing =
        attribution &&
        (attribution.gettingAnalyticsData ||
            (attribution.inFlightXHR && !attribution.requestComplete));

    if (!signing) {
        return Promise.resolve(null);
    }

    return new Promise((resolve) => {
        let finished = false;
        const finish = (status) => {
            if (finished) {
                return;
            }
            finished = true;
            clearTimeout(timer);
            attribution.successCallback = undefined;
            attribution.timeoutCallback = undefined;
            window.dataLayer.push({
                event: 'widget_action',
                type: 'direct-attribution',
                action: status,
                non_interaction: true
            });
            resolve(status);
        };

        attribution.successCallback = () => finish('success');
        attribution.timeoutCallback = () => finish('timeout');
        const timer = setTimeout(() => finish('timeout'), capMs);
    });
};

/**
 * Replace the URL's attribution params with the signed cookie's, if there is one.
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
 * @param {HTMLElement} container
 * @param {String} reason
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
        // Analytics never blocks the page.
    }
};

/**
 * @param {String} url
 */
PartnerDownload.navigate = (url) => {
    window.location.href = url;
};

/**
 * Start and track the download, and point "try again" at the same URL.
 * @param {HTMLElement} link
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
        // Analytics never blocks the page.
    }

    PartnerDownload.navigate(url);
};

/**
 * Show the visitor's state and start the partner download; call on DOM ready.
 * @returns {Promise<Object>} the chosen state
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
