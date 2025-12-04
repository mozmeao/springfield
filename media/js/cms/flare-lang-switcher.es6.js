/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Flare language switcher functionality
 * Adapted from Mozilla Protocol language switcher
 */

const FlareLangSwitcher = {};

/**
 * Returns URL pathname preceded by a new page locale.
 * Assumes first path immediately after hostname is the page locale.
 * @param {Object} Location interface
 * @param {String} Newly selected language code e.g. `de`
 * @return {String} pathname e.g. `/de/firefox/`
 */
FlareLangSwitcher.switchPath = function (location, newLang) {
    const parts = location.pathname.slice(1).split('/');
    const currentLang = '/' + parts[0] + '/';

    // check that first path is a valid lang code.
    if (!/^(\/\w{2}-\w{2}\/|\/\w{2,3}\/)/.test(currentLang)) {
        return false;
    }
    const urlpath = parts.slice(1).join('/');
    return '/' + newLang + '/' + urlpath + location.search;
};

/**
 * Redirect page to destination URL if valid
 * @param {String} destination
 */
FlareLangSwitcher.doRedirect = function (destination) {
    if (destination) {
        window.location.href = destination;
    }
};

/**
 * Initialize footer lang switcher.
 * @param {function} Custom callback for analytics.
 */
FlareLangSwitcher.init = function (callback) {
    const languageSelects = document.querySelectorAll(
        '.fl-language-switcher-select'
    );

    for (let i = 0; i < languageSelects.length; i++) {
        languageSelects[i].setAttribute(
            'data-previous-language',
            languageSelects[i].value
        );
        languageSelects[i].addEventListener(
            'change',
            function (e) {
                const newLanguage = e.target.value;
                const previousLanguage = e.target.getAttribute(
                    'data-previous-language'
                );

                // support custom callback for page analytics.
                if (typeof callback === 'function') {
                    callback(previousLanguage, newLanguage);
                }

                FlareLangSwitcher.doRedirect(
                    FlareLangSwitcher.switchPath(window.location, newLanguage)
                );
            },
            false
        );
    }
};

// Initialize with analytics tracking
FlareLangSwitcher.init(function (previousLanguage, newLanguage) {
    // GA4
    if (window.dataLayer) {
        window.dataLayer.push({
            event: 'widget_action',
            type: 'language selector',
            action: 'change to: ' + newLanguage
        });
    }
});
