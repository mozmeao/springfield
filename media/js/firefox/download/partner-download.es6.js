/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Plausible from '../../base/plausible/plausible.es6';

const BITNESS_WAIT_MS = 500;
const DOWNLOAD_DELAY_MS = 1000;
const ATTRIBUTION_WAIT_MS = 2000;

const UNAVAILABLE_REASONS = {
    device: 'device',
    linux_device: 'device',
    language: 'language',
    linux_language: 'language',
    firefox: 'firefox',
    unsupported_os: 'unsupported_os'
};

const PartnerDownload = {};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Resolve whether a Windows machine is 64-bit, giving client hints a moment to answer.
 * @returns {Promise<Boolean>}
 */
PartnerDownload.isX64 = () => {
    const site = window.site;
    const userAgentData = navigator.userAgentData;
    const fromUserAgent = () => site.getArchSize() === 64;
    if (
        site.platform !== 'windows' ||
        !userAgentData ||
        typeof userAgentData.getHighEntropyValues !== 'function'
    ) {
        return Promise.resolve(fromUserAgent());
    }
    return Promise.race([
        userAgentData
            .getHighEntropyValues(['bitness'])
            .then(
                (values) => site.getArchSizeClientHint(values.bitness) === 64,
                fromUserAgent
            ),
        wait(BITNESS_WAIT_MS).then(fromUserAgent)
    ]);
};

/**
 * Find the partner build for this machine. A 64-bit build only goes to a machine detected as 64-bit.
 * @param {HTMLElement} container
 * @param {String} platform
 * @param {Boolean} x64
 * @returns {HTMLAnchorElement|null}
 */
PartnerDownload.findLink = (container, platform, x64) => {
    const link = (os) =>
        container.querySelector(
            `.c-partner-download-links [data-download-version="${os}"]`
        );
    if (platform === 'osx') {
        return link('osx');
    }
    if (platform === 'windows') {
        return (x64 && link('win64')) || link('win');
    }
    return null;
};

/**
 * Whether this is an ARM machine, which can't run a partner's 64-bit Linux build.
 * @returns {Boolean}
 */
PartnerDownload.isArm = () =>
    /\b(arm|aarch64)/i.test(navigator.platform) ||
    /\b(arm|aarch64)/i.test(navigator.userAgent);

/**
 * Pick the state to show: the partner download, or why the visitor can't have it.
 * @param {Object} site - `window.site`
 * @param {Object} builds - each platform's build state: "available", "language" or "device"
 * @param {HTMLAnchorElement|null} link - the partner build for this machine
 * @returns {String}
 */
PartnerDownload.getState = (site, builds, link) => {
    const platform = site.platform;
    if (platform === 'android' || platform === 'ios') {
        return 'device';
    }
    if (site.isFirefox()) {
        return 'firefox';
    }
    if (platform === 'linux') {
        if (builds.linux === 'available') {
            return PartnerDownload.isArm() ? 'linux_device' : 'linux';
        }
        return `linux_${builds.linux}`;
    }
    if (platform !== 'windows' && platform !== 'osx') {
        return 'device';
    }
    if (site.fxSupported === false) {
        return 'unsupported_os';
    }
    if (link) {
        return 'download';
    }
    return builds[platform] === 'language' ? 'language' : 'device';
};

/**
 * Wait until `deadline` for attribution signing already in progress.
 * @param {Promise} deadline
 * @returns {Promise}
 */
PartnerDownload.waitForAttribution = (deadline) => {
    const attribution = window.Mozilla.DownloadAttribution;
    const signing =
        attribution &&
        (attribution.gettingAnalyticsData ||
            (attribution.inFlightXHR && !attribution.requestComplete));
    if (!signing) {
        return Promise.resolve();
    }
    // Chain any callbacks already registered, so other scripts still get them.
    const previousSuccess = attribution.successCallback;
    const previousTimeout = attribution.timeoutCallback;
    const signed = new Promise((resolve) => {
        attribution.successCallback = () => {
            if (typeof previousSuccess === 'function') {
                previousSuccess();
            }
            resolve('success');
        };
        attribution.timeoutCallback = () => {
            if (typeof previousTimeout === 'function') {
                previousTimeout();
            }
            resolve('timeout');
        };
    });
    return Promise.race([signed, deadline.then(() => 'timeout')]).then(
        (action) => {
            try {
                window.dataLayer.push({
                    event: 'widget_action',
                    type: 'direct-attribution',
                    action: action,
                    non_interaction: true
                });
            } catch (error) {
                // Analytics never blocks the download.
            }
        }
    );
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
    } catch (error) {
        // Analytics never blocks the page.
    }
    try {
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
 * Start and track the download, and point "try again" at the same build.
 * @param {HTMLAnchorElement} link - the partner build for this machine
 */
PartnerDownload.startDownload = (link) => {
    const url = PartnerDownload.getAttributedURL(link.href);
    const tryAgain = document.getElementById('partner-download-try-again');
    if (tryAgain) {
        tryAgain.href = link.href;
        // Attribute at click time, so a later consent change is respected.
        tryAgain.addEventListener('click', (event) => {
            tryAgain.href = PartnerDownload.getAttributedURL(link.href);
            window.Mozilla.TrackProductDownload.handleLink(event);
        });
    }
    try {
        window.Mozilla.TrackProductDownload.sendEventFromURL(url);
    } catch (error) {
        // Analytics never blocks the download.
    }
    PartnerDownload.navigate(url);
};

/**
 * Unhide the section for `state` and hide the rest.
 * @param {HTMLElement} container
 * @param {String} state
 */
PartnerDownload.showState = (container, state) => {
    for (const section of container.querySelectorAll('section[data-state]')) {
        section.hidden = section.getAttribute('data-state') !== state;
    }
};

/**
 * Show the visitor's state, and download the partner build when there's one for their machine.
 * @returns {Promise<String>} the state shown
 */
PartnerDownload.begin = () => {
    const container = document.querySelector('.c-partner-download');
    if (!container) {
        return Promise.resolve(null);
    }
    const downloadDelay = wait(DOWNLOAD_DELAY_MS);
    const attributionDeadline = wait(ATTRIBUTION_WAIT_MS);

    return Promise.resolve()
        .then(() => PartnerDownload.isX64())
        .then((x64) => {
            const link = PartnerDownload.findLink(
                container,
                window.site.platform,
                x64
            );
            const state = PartnerDownload.getState(
                window.site,
                container.dataset,
                link
            );
            PartnerDownload.showState(container, state);

            if (state === 'download') {
                return Promise.all([
                    downloadDelay,
                    PartnerDownload.waitForAttribution(attributionDeadline)
                ]).then(() => {
                    PartnerDownload.startDownload(link);
                    return state;
                });
            }
            if (UNAVAILABLE_REASONS[state]) {
                PartnerDownload.sendUnavailableEvent(
                    container,
                    UNAVAILABLE_REASONS[state]
                );
            }
            return state;
        })
        .catch(() => {
            // Never leave the page blank: fall back to the regular Firefox download.
            if (!container.querySelector('section[data-state]:not([hidden])')) {
                PartnerDownload.showState(container, 'device');
                return 'device';
            }
            return null;
        });
};

export default PartnerDownload;
