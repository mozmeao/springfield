/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

let timeout;
let requestComplete = false;

/**
 * Determine if browser should attempt to download Firefox on page load.
 * @param {String} platform
 * @param {Boolean} fxSupported
 * @returns {Boolean}
 */
function shouldAutoDownload(platform, fxSupported) {
    const supportedPlatforms = ['windows', 'osx', 'android', 'ios'];

    if (fxSupported && supportedPlatforms.indexOf(platform) !== -1) {
        return true;
    }

    return false;
}

/**
 * Get the Firefox download link for the appropriate platform.
 * @param {Object} window.site
 * @returns {String} download url
 */
function getDownloadURL(site) {
    // TODO: confirm if we want to hardcode 'thanks-' prefix here
    // It is part of a helper, but maybe unnecessarily specific to /thanks page?
    const prefix = 'thanks-download-button-';
    let link;
    let url;

    switch (site.platform) {
        case 'windows':
            link = document.getElementById(prefix + 'win');
            break;
        case 'osx':
            link = document.getElementById(prefix + 'osx');
            break;
        case 'linux':
            // Linux users get SUMO install instructions.
            link = null;
            break;
        case 'android':
            link = document.getElementById(prefix + 'android');
            break;
        case 'ios':
            link = document.getElementById(prefix + 'ios');
            break;
    }

    if (link && link.href) {
        url = link.href;
    }

    return url;
}

/**
 * Auto-start download
 */
function beginFirefoxDownload() {
    const directDownloadLink = document.getElementById('direct-download-link');
    let downloadURL;

    // Only auto-start the download if a supported platform is detected.
    if (
        shouldAutoDownload(window.site.platform, window.site.fxSupported) &&
        typeof Mozilla.Utils !== 'undefined'
    ) {
        downloadURL = getDownloadURL(window.site);

        if (downloadURL) {
            // Pull download link from the download button and add to the 'Try downloading again' link.
            // Make sure the 'Try downloading again' link is well formatted! (issue 9615)
            if (directDownloadLink && directDownloadLink.href) {
                directDownloadLink.href = downloadURL;
                directDownloadLink.addEventListener(
                    'click',
                    (event) => {
                        try {
                            Mozilla.TrackProductDownload.handleLink(event);
                        } catch (error) {
                            return;
                        }
                    },
                    false
                );
            }

            // Start the platform-detected download a second after DOM ready event.
            Mozilla.Utils.onDocumentReady(() => {
                setTimeout(() => {
                    try {
                        Mozilla.TrackProductDownload.sendEventFromURL(
                            downloadURL
                        );
                    } catch (error) {
                        return;
                    }
                    window.location.href = downloadURL;
                }, 1000);
            });
        }
    }
}

/**
 * On success of new download attribution request
 */
function onSuccess() {
    // Make sure we only initiate the download once!
    clearTimeout(timeout);
    if (requestComplete) {
        return;
    }
    requestComplete = true;

    // Fire GA event to log attribution success
    // GA4
    window.dataLayer.push({
        event: 'widget_action',
        type: 'direct-attribution',
        action: 'success',
        non_interaction: true
    });

    beginFirefoxDownload();
}

/**
 * On timeout of new download attribution request
 */
function onTimeout() {
    // Make sure we only initiate the download once!
    clearTimeout(timeout);
    if (requestComplete) {
        return;
    }
    requestComplete = true;

    // Fire GA event to log attribution timeout
    // GA4
    window.dataLayer.push({
        event: 'widget_action',
        type: 'direct-attribution',
        action: 'timeout',
        non_interaction: true
    });

    beginFirefoxDownload();
}

// Force cookie update if there is essential data to add
if (
    Mozilla.DownloadAttribution !== undefined &&
    document.documentElement.hasAttribute(
        'data-stub-attribution-campaign-force'
    )
) {
    // Custom success and timeout callbacks are only relevant for direct attribution
    // (i.e. when we have updated the cookie on the auto-download page)
    Mozilla.DownloadAttribution.successCallback = onSuccess;
    Mozilla.DownloadAttribution.timeoutCallback = onTimeout;
    // Don't wait too long before starting download
    // (even if it means we have to leave the essential information out)
    timeout = setTimeout(onTimeout, 2000);
    Mozilla.DownloadAttribution.initEssential();
} else {
    beginFirefoxDownload();
}

// Bug 1354334 - add a hint for test automation that page has loaded.
document.getElementsByTagName('html')[0].classList.add('download-ready');
