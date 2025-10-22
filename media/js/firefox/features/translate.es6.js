/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Initialize language names using Intl.DisplayNames API
 * This replaces hardcoded language names with dynamically generated ones
 * based on the user's current locale and CLDR data
 */
function initTranslateLanguageNames() {
    // Return early if the browser doesn't support Intl.DisplayNames or Intl.Locale
    if (
        typeof Intl === 'undefined' ||
        typeof Intl.Locale === 'undefined' ||
        typeof Intl.DisplayNames === 'undefined'
    ) {
        return;
    }

    const langList = document.querySelector('.c-translate-lang-list');

    const currentLocale = document.documentElement.lang || 'en';

    const supportedLanguages = [...langList.querySelectorAll('li')]
        .map(li => li.dataset.lang.trim());

    const displayNames = new Intl.DisplayNames([currentLocale], {
        type: 'language',
        languageDisplay: 'standard'
    });

    const languageNames = supportedLanguages
        .map((langCode) => {
            const locale = new Intl.Locale(langCode);

            let displayCode;
            // For Chinese, include script to distinguish variants and remove region (e.g. "Cinese (semplificato)")
            if (locale.language === 'zh' && !locale.script) {
                const maximized = locale.maximize();
                displayCode = `${maximized.language}-${maximized.script}`;
            } else {
                // For most cases, just use the language portion
                displayCode = locale.language;
            }

            const languageName = displayNames.of(displayCode);
            return languageName.charAt(0).toUpperCase() + languageName.slice(1);
        })
        .sort((a, b) => a.localeCompare(b));

    langList.textContent = '';
    languageNames.forEach((languageName) => {
        const li = document.createElement('li');
        li.textContent = languageName;
        langList.appendChild(li);
    });
}

if (typeof Mozilla.Utils !== 'undefined') {
    Mozilla.Utils.onDocumentReady(initTranslateLanguageNames);
}
