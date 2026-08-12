/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { batch, effect, signal, computed } from '@preact/signals-core';

const OS = {
    IOS: 'ios',
    MACOS: 'osx',
    MACOSPKG: 'osx-pkg',

    ANDROID: 'android',

    WINDOWS32: 'win',
    WINDOWS32MSI: 'win-msi',
    WINDOWS64: 'win64',
    WINDOWS64MSI: 'win64-msi',
    WINDOWS64ARM: 'win64-aarch64',

    LINUX32: 'linux',
    LINUX64: 'linux64',
    LINUX64ARM: 'linux64-aarch64'
};

const RELEASES = {
    STABLE: 'stable',
    BETA: 'beta',
    DEV: 'dev',
    NIGHTLY: 'nightly',
    ESR: 'esr',
    ESR_NEXT: 'esr-next',
    ESR_115: 'esr-115'
};

const UNSUPPORTED_PLATFORMS_BY_RELEASE = JSON.parse(
    unsupportedPlatformsByRelease.textContent
);

const IOS_APP_STORE_LINKS = {
    [RELEASES.STABLE]:
        'https://apps.apple.com/us/app/apple-store/id989804926?mz_pr=firefox_mobile&pt=373246&ct=firefox-all&mt=8',
    [RELEASES.BETA]: 'https://www.firefox.com/channel/ios/testflight/'
};

const MOBILE_SYSTEM_REQUIREMENTS =
    'https://support.mozilla.org/kb/will-firefox-work-my-mobile-device';

const ANDROID_PLAY_STORE_LINKS = {
    [RELEASES.STABLE]:
        'https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-all',
    [RELEASES.BETA]:
        'https://play.google.com/store/apps/details?id=org.mozilla.firefox_beta&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-all',
    [RELEASES.NIGHTLY]:
        'https://play.google.com/store/apps/details?id=org.mozilla.fenix&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-all'
};

const MICROSOFT_STORE_LINKS = {
    [RELEASES.STABLE]:
        'https://apps.microsoft.com/detail/9nzvdkpmr9rd?mode=mini&cid=firefox-all&mz_cn=release',
    [RELEASES.BETA]:
        'https://apps.microsoft.com/detail/9nzw26frndln?mode=mini&cid=firefox-all&mz_cn=beta'
};

function isMobileOS(os) {
    return os === OS.IOS || os === OS.ANDROID;
}

class SystemRequirementsURL extends URL {
    static #resolveURL(choices) {
        const path = [
            'firefox',
            {
                [RELEASES.STABLE]: '',
                [RELEASES.ESR]: 'organizations',
                [RELEASES.BETA]: 'beta',
                [RELEASES.DEV]: 'developer',
                [RELEASES.NIGHTLY]: 'nightly'
            }[choices.release],
            'system-requirements'
        ];

        return '/' + path.filter(Boolean).join('/') + '/';
    }
    constructor(choices) {
        super(
            ...(isMobileOS(choices.os)
                ? [MOBILE_SYSTEM_REQUIREMENTS]
                : [SystemRequirementsURL.#resolveURL(choices), window.location])
        );
    }
}

class ReleaseNotesURL extends URL {
    static #resolveURL(choices) {
        const path = [
            'firefox',
            {
                [RELEASES.STABLE]: '',
                [RELEASES.ESR]: 'organizations',
                [RELEASES.BETA]: 'beta',
                [RELEASES.DEV]: 'developer',
                [RELEASES.NIGHTLY]: 'nightly'
            }[choices.release],
            'notes'
        ];

        if (choices.os === OS.IOS || choices.os === OS.ANDROID) {
            path.splice(1, 0, choices.os);
        }

        return '/' + path.filter(Boolean).join('/') + '/';
    }
    constructor(choices) {
        super(ReleaseNotesURL.#resolveURL(choices), window.location);
    }
}

/**
 * Generate a Firefox download URL for desktop and Android APT based on the form choices.
 */
class FirefoxDownloadURL extends URL {
    static base = 'https://download.mozilla.org/';

    static releaseChoiceToDownloadChannel = {
        [RELEASES.STABLE]: '',
        [RELEASES.BETA]: 'beta',
        [RELEASES.NIGHTLY]: 'nightly',
        [RELEASES.DEV]: 'devedition',
        [RELEASES.ESR]: 'esr',
        [RELEASES.ESR_NEXT]: 'esr-next',
        [RELEASES.ESR_115]: 'esr115'
    };

    static resolveOS(choices) {
        return choices.os.endsWith('-msi') || choices.os.endsWith('-pkg')
            ? choices.os.slice(0, -4)
            : choices.os;
    }

    static resolveProduct(choices) {
        const name = ['firefox'];
        name.push(
            FirefoxDownloadURL.releaseChoiceToDownloadChannel[choices.release]
        );
        if (choices.os.endsWith('pkg')) name.push('pkg');
        if (choices.os.endsWith('msi')) name.push('msi');
        name.push('latest');
        if (
            choices.os !== 'android' &&
            choices.release === 'nightly' &&
            choices.language !== 'en-US'
        )
            name.push('l10n');
        name.push('ssl');
        return name.filter(Boolean).join('-');
    }

    static resolveLang(choices) {
        if (choices.os.startsWith('osx') && choices.language === 'ja')
            return 'ja-JP-mac';
        else if (choices.os === 'android') return 'multi';

        return choices.language;
    }

    constructor(choices) {
        super(FirefoxDownloadURL.base);
        this.searchParams.set('os', FirefoxDownloadURL.resolveOS(choices));
        this.searchParams.set(
            'product',
            FirefoxDownloadURL.resolveProduct(choices)
        );
        this.searchParams.set('lang', FirefoxDownloadURL.resolveLang(choices));
    }
}

// Condition for showing results: are the options compatible
// Otherwise, fallback.
//
// Goal: initially try to get the form to a compatible state.
// - Compatible prefill options
// - Platform detection
//
// Failure:
// - Incompatible prefill options (show errors)
// - Platform detection fails (don’t show errors)
//
// Condition for showing errors:
// - Was it the result of a user action:
//   - Incompatible prefill
//   - Incompatible option selection

class FirefoxDownloadFormElement extends HTMLElement {
    #os = signal();
    get os() {
        return this.#os.value;
    }
    set os(value) {
        this.#os.value = value;
    }

    #release = signal();
    get release() {
        return this.#release.value;
    }
    set release(value) {
        this.#release.value = value;
    }

    #language = signal();
    get language() {
        return this.#language.value;
    }
    set language(value) {
        this.#language.value = value;
    }

    #choices = computed(() => ({
        os: this.#os.value,
        release: this.#release.value,
        language: this.#language.value
    }));
    get choices() {
        return this.#choices.value;
    }

    get releaseNotesElement() {
        return this.querySelector('#release-notes');
    }
    get systemRequirementsElement() {
        return this.querySelector('#system-requirements');
    }

    get form() {
        return this.querySelector(':scope > form:first-child');
    }

    get resultsPane() {
        return this.querySelector('.c-results');
    }

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = '<slot></slot>';
        this.shadowRoot.addEventListener('slotchange', this);
    }

    handleEvent(event) {
        switch (event.type) {
            case 'slotchange':
                this.#handleSlotChange(event);
                break;
            case 'input':
                this.#handleInput(event);
                break;
            case 'invalid':
                this.#handleInvalid(event);
                break;
            case 'submit':
                event.preventDefault();
                // TODO: maybe since a submit is expected we just follow the
                // most prominent link? Or we direct users to the options?
                break;
        }
    }

    /**
     * Handle the initial form setup
     */
    #handleSlotChange() {
        if (!this.form) return;

        // Initialize the signals with the form values
        batch(() => {
            this.os = this.form.elements.os.value;
            this.release = this.form.elements.os.release;
            this.language = this.form.elements.os.language;
        });

        // Setup URL param syncing
        // Note: does not run during OS detection
        // TODO: determine if this should update when the form values are incompatible
        effect(() => {
            if (this.os && this.release) {
                const url = new URL(window.location);
                url.search = new URLSearchParams({
                    os: this.os,
                    release: this.release,
                    language: this.language
                });
                history.replaceState(null, '', url);
            }
        });

        // Setup
        this.form.addEventListener('submit', this);
        this.form.addEventListener('input', this);
        this.form.addEventListener('invalid', this, true);

        this.primaryAction = this.#createDownloadButton({
            label: 'Download',
            icon: 'downloads',
            additionalClasses: ['button-primary'],
            href: ''
        });

        document
            .querySelector('[data-primary-action]')
            .closest('.c-download-option')
            .replaceWith(this.primaryAction.element);

        effect(() => {
            switch (this.os) {
                case OS.IOS:
                    this.primaryAction.href.value =
                        IOS_APP_STORE_LINKS[this.release];
                    switch (this.release) {
                        case RELEASES.STABLE:
                            this.primaryAction.label.value =
                                'Download from the App Store';
                            this.primaryAction.icon.value = 'downloads';
                            break;
                        case RELEASES.BETA:
                            this.primaryAction.label.value =
                                'Sign up for TestFlight';
                            this.primaryAction.icon.value = 'forward';
                            break;
                    }
                    break;
                case OS.ANDROID:
                    this.primaryAction.href.value =
                        ANDROID_PLAY_STORE_LINKS[this.relase];
                    this.primaryAction.label.value =
                        'Download from the Play Store';
                    this.primaryAction.icon.value = 'downloads';
                    break;
                default:
                    this.primaryAction.label.value =
                        this.release === RELEASES.ESR
                            ? 'Download ESR 140'
                            : 'Download';

                    this.primaryAction.icon.value = 'downloads';

                    this.primaryAction.href.value = new FirefoxDownloadURL(
                        this.choices
                    );
                    break;
            }
        });

        this.storeAction = this.#createDownloadButton({
            label: 'Download from the Microsoft store',
            icon: 'external-link',
            additionalClasses: ['button-secondary', 'fl-button-small']
        });
        effect(() => {
            if (
                this.os.startsWith('win') &&
                [RELEASES.STABLE, RELEASES.BETA].includes(this.release)
            ) {
                this.storeAction.label.value =
                    'Download from the Microsoft Store';
                this.storeAction.href.value =
                    MICROSOFT_STORE_LINKS[this.release];
                if (!this.storeAction.element.isConnected) {
                    this.primaryAction.element.after(
                        this.#createOrDivider().element,
                        this.storeAction.element
                    );
                }
            } else {
                this.storeAction.label.value = '';
                this.storeAction.href.value = '';
                if (this.storeAction.element.isConnected) {
                    this.#removeOrDivider(this.storeAction.element, 'before');
                    this.storeAction.element.remove();
                }
            }
        });

        this.esrNextAction = this.#createDownloadButton({
            label: 'Download ESR 153',
            icon: 'downloads',
            additionalClasses: ['button-primary']
        });
        effect(() => {
            if (
                this.release === RELEASES.ESR &&
                this.#releaseSupportsPlatform(RELEASES.ESR_NEXT, this.os)
            ) {
                this.esrNextAction.href.value = new FirefoxDownloadURL({
                    os: this.os,
                    release: RELEASES.ESR_NEXT,
                    language: this.language
                });
                if (!this.esrNextAction.element.isConnected) {
                    this.primaryAction.element.before(
                        this.esrNextAction.element,
                        this.#createOrDivider().element
                    );
                }
            } else if (this.esrNextAction.element.isConnected) {
                this.#removeOrDivider(this.esrNextAction.element, 'after');
                this.esrNextAction.element.remove();
            }
        });

        this.esr115Action = this.#createDownloadButton({
            label: 'Download ESR 115',
            icon: 'downloads',
            additionalClasses: ['button-primary', 'fl-button-small'],
            withRecommendation: true
        });
        effect(() => {
            if (
                this.release === RELEASES.ESR &&
                this.#releaseSupportsPlatform(RELEASES.ESR_115, this.os)
            ) {
                this.esr115Action.href.value = new FirefoxDownloadURL({
                    os: this.os,
                    release: RELEASES.ESR_115,
                    language: this.language
                });
                if (this.os.startsWith('win')) {
                    this.esr115Action.recommendation.value =
                        'Recommended for Windows 7/8/8.1';
                } else if (this.os.startsWith('osx')) {
                    this.esr115Action.recommendation.value =
                        'Recommended for macOS 10.12–10.14';
                } else if (this.os.startsWith('linux')) {
                    this.esr115Action.recommendation.value =
                        'Recommended for older operating systems';
                }

                if (!this.esr115Action.element.isConnected) {
                    this.primaryAction.element.after(
                        this.#createOrDivider().element,
                        this.esr115Action.element
                    );
                }
            } else if (this.esr115Action.element.isConnected) {
                this.#removeOrDivider(this.esr115Action.element, 'before');
                this.esr115Action.element.remove();
            }
        });

        this.aptAction = this.#createDownloadButton({
            label: 'Set up the APT repository',
            href: 'https://support.mozilla.org/en-US/kb/install-firefox-linux#w_install-firefox-deb-package-for-debian-based-distributions',
            icon: 'external-link',
            additionalClasses: ['button-secondary']
        });
        effect(() => {
            if (
                this.os.startsWith('linux') &&
                !this.aptAction.element.isConnected
            ) {
                this.querySelector('.c-download-options').prepend(
                    this.aptAction.element
                );
            } else if (this.aptAction.element.isConnected) {
                this.aptAction.element.remove();
            }
        });

        this.releaseNotes = this.#createSupportLink({
            label: 'Release Notes',
            href: '/firefox/notes/'
        });
        effect(() => {
            this.releaseNotes.href.value = new ReleaseNotesURL(this.choices);
        });

        this.systemRequirements = this.#createSupportLink({
            label: 'System Requirements',
            href: '/firefox/system-requirements/'
        });
        effect(() => {
            this.systemRequirements.href.value = new SystemRequirementsURL(
                this.choices
            );
        });

        this.privacyPolicy = this.#createSupportLink({
            label: 'Privacy Policy',
            href: 'https://www.mozilla.org/privacy/firefox/'
        });

        const supportLinks = document.createElement('div');
        supportLinks.classList.add('c-support-links');
        supportLinks.append(
            this.releaseNotes.element,
            this.systemRequirements.element,
            this.privacyPolicy.element
        );
        this.resultsPane.append(supportLinks);

        this.compatible = signal();
        effect(() => {
            this.resultsPane.querySelector('.c-download-options').hidden =
                !this.compatible.value;
            this.resultsPane.querySelector('.c-support-links').hidden =
                !this.compatible.value;
            this.resultsPane.querySelector('.c-incompatible-choices').hidden =
                this.compatible.value;
        });

        this.#setConditionalDisplay();
        this.#validate();

        this.shadowRoot.removeEventListener('slotchange', this);
    }

    /**
     * Handle syncing the choices as signals, clearing irrelevant validation.
     */
    #handleInput(event) {
        // Sync the form state
        batch(() => {
            this.os = this.form.elements.os.value;
            this.release = this.form.elements.release.value;
            this.language = this.form.elements.language.value;
        });

        // TODO: switch to signals for conditional display
        this.#setConditionalDisplay();
        this.#validate();

        const [selectedOption] = event.target.selectedOptions;

        if (!selectedOption.disabled) event.target.setCustomValidity('');
        else event.target.setCustomValidity('Chosen option not available');

        // Clear the server rendered error messages
        for (const control of this.form.elements) {
            if (control.disabled || control.type !== 'select-one') continue;

            if (control.validity.valid) {
                const fieldWrap = control.closest('.fl-field-wrap');
                const errorMessage = fieldWrap.querySelector(
                    '.fl-field-error-message'
                );
                if (!errorMessage) continue;
                errorMessage.remove();
                control.removeAttribute('aria-describedby');
                fieldWrap.classList.remove('fl-field-error');
            }
        }
    }

    /**
     * Progressive enhancement for validation messages.
     */
    #handleInvalid(event) {
        event.preventDefault();

        if (!event.target.matches(':user-invalid')) return;

        const fieldWrap = event.target.closest('.fl-field-wrap');

        if (fieldWrap.querySelector('.fl-field-error-message')) return;

        const { element: errorMessage } = this.#createErrorMessage({
            message: event.target.validationMessage
        });

        // Since the validation is happening as the select element closes, the announcement-space is very busy and we risk our message being clobbered.
        // This is especially bad on iOS.
        // In order to circumvent these issues, we need to debounce the live region announcement.
        // For iOS VoiceOver, we need an extra long delay to avoid clobbering.
        // We can visually display the error immediately, but then wait for a timeout.
        // Safari tends to be quite aggressive with how it caches its accessibility tree, but if we use a shadow root to change the DOM structure, we can force it to invalidate.
        // TODO: use a more reliable/accurate way of checking for mobile.
        setTimeout(
            () => {
                errorMessage.attachShadow({ mode: 'open' });
                errorMessage.shadowRoot.innerHTML =
                    '<div role=alert><slot></slot></div>';
            },
            matchMedia('(pointer: coarse)').matches ? 1_400 : 250
        );

        fieldWrap.classList.add('fl-field-error');
        fieldWrap.append(errorMessage);

        event.target.ariaDescribedByElements = [errorMessage];
    }

    #setConditionalDisplay() {
        const { os, release, language } = this.form.elements;

        this.dataset.os = os.value;
        this.dataset.release = release.value;
        this.dataset.language = language.value;

        const isMobile = os.value === OS.IOS || os.value === OS.ANDROID;

        language.disabled = isMobile;

        const languageFieldWrap = language.closest('.fl-field-wrap');
        if (
            language.disabled &&
            !languageFieldWrap.querySelector('.language-message')
        ) {
            const languageMessage = Object.assign(
                document.createElement('div'),
                {
                    textContent:
                        'Language can be configured after installation.'
                }
            );
            languageMessage.classList.add('language-message');
            languageFieldWrap.append(languageMessage);
        } else if (!language.disabled) {
            languageFieldWrap.querySelector('.language-message')?.remove();
        }

        for (const releaseOption of Object.values(RELEASES)) {
            // TODO: find a better way to handle this (e.g. filter it earlier)
            if ([RELEASES.ESR_115, RELEASES.ESR_NEXT].includes(releaseOption))
                continue;
            const isSupported = this.#releaseSupportsPlatform(
                releaseOption,
                os.value
            );
            let optionElement = release.options[releaseOption];

            // Setting `hidden` on an option element has a number of issues:
            //
            // - Safari doesn’t respect it (unless using customizable select).
            // - Screen readers still seem to count them when presenting the
            //   item number of the current option.
            // - In NVDA + Firefox, the arrow key select navigation (form mode)
            //   becomes completely broken.
            //
            // So instead what we do here is store incompatible options as a
            // comment with the option value and label delimited with a `:`
            // (e.g. <!--esr:Firefox ESR-->).
            //
            // In the case where an incompatible option was selected, we keep it
            // in the DOM, but disable it until the user changes their
            // selection, so to avoid changing the user’s choice and to promote
            // an understanding of which option is incorrect.

            if (isSupported && !optionElement) {
                const comment = Array.from(release.childNodes).find(
                    (node) =>
                        node.nodeType === Node.COMMENT_NODE &&
                        node.data.split(':')[0] === releaseOption
                );
                if (!comment)
                    throw `Missing placeholder comment for option: ${releaseOption}`;

                optionElement = document.createElement('option');
                optionElement.value = releaseOption;
                optionElement.setAttribute('name', releaseOption);
                optionElement.textContent = comment.data.split(':')[1];
                comment.replaceWith(optionElement);
            } else if (!isSupported && optionElement) {
                if (optionElement.selected) {
                    optionElement.disabled = true;
                } else {
                    // Make sure the node is hidden
                    const comment = new Comment(
                        `${releaseOption}:${optionElement.textContent}`
                    );
                    optionElement.replaceWith(comment);
                }
            } else if (isSupported && optionElement) {
                if (optionElement.selected) {
                    optionElement.disabled = false;
                }
            }
        }
    }

    #releaseSupportsPlatform(release, platform) {
        if (!Object.values(RELEASES).includes(release))
            throw new RangeError(`Unknown release: ${release}`);
        if (!Object.values(OS).includes(platform))
            throw new RangeError(`Unknown platform: ${platform}`);

        const unsupported = UNSUPPORTED_PLATFORMS_BY_RELEASE[release];
        if (!unsupported) throw `unknown release type ${release}`;
        return !unsupported.includes(platform);
    }

    #validate() {
        const { os, release } = this.form.elements;

        release.setCustomValidity(
            this.#releaseSupportsPlatform(release.value, os.value)
                ? ''
                : 'Chosen release type is not available for this platform.'
        );

        if (!release.validity.valid) release.reportValidity();

        this.compatible.value = this.form.matches(':valid');
    }

    // TODO: if no search params, prefill based on detected OS.
    #detectOS() {
        const ua = navigator.userAgent;
        if (/Android|iPhone|iPad/.test(ua)) return null;
        if (/Windows/.test(ua))
            return /ARM|aarch64/i.test(ua) ? 'win64-aarch64' : 'win64';
        if (/Mac OS X/.test(ua)) return 'osx';
        if (/Linux/.test(ua))
            return /aarch64|arm64/i.test(ua) ? 'linux64-aarch64' : 'linux64';
        return null;
    }

    #createDownloadButton({
        label: initialLabel,
        additionalClasses,
        href: initialHref,
        icon: initialIcon,
        withRecommendation,
        recommendation: initialRecommendation
    } = {}) {
        const label = signal(initialLabel ?? '');
        const href = signal(initialHref ?? '');

        const element = document.createElement('div');
        element.classList.add('c-download-option');
        const link = document.createElement('a');

        let icon, iconElement;
        if (initialIcon) {
            icon = signal(initialIcon);

            iconElement = document.createElement('span');
            iconElement.setAttribute('aria-hidden', 'true');

            effect(() => {
                iconElement.className = `fl-icon fl-icon-${icon}`;
            });
        }

        let recommendation, recommendationElement;
        if (withRecommendation === true) {
            recommendation = signal(initialRecommendation ?? '');

            recommendationElement = document.createElement('p');
            recommendationElement.classList.add('c-recommendation');

            effect(() => {
                recommendationElement.textContent = recommendation.value;
            });
        }

        link.classList.add('fl-button');
        if (additionalClasses) link.classList.add(...additionalClasses);

        effect(() => {
            const [text] = link.childNodes;
            if (text) {
                text.data = label.value;
            } else {
                link.textContent = label.value;
            }
        });

        effect(() => {
            link.href = href.value;
        });

        if (icon) link.append(iconElement);
        element.append(link);
        if (recommendationElement) element.append(recommendationElement);

        return {
            element,
            label,
            href,
            recommendation,
            icon
        };
    }

    #createSupportLink({ label: initialLabel, href: initialHref } = {}) {
        const label = signal(initialLabel);
        const href = signal(initialHref);

        const element = document.createElement('a');

        effect(() => {
            element.textContent = label.value;
        });

        effect(() => {
            element.href = href.value;
        });

        return {
            element,
            label,
            href
        };
    }

    #createErrorMessage({ message: initialMessage }) {
        const message = signal(initialMessage);
        const element = document.createElement('deferred-alert');
        element.classList.add('fl-field-error-message');
        effect(() => {
            element.textContent = message.value;
        });
        return { element, message };
    }

    #createOrDivider() {
        const element = document.createElement('div');
        element.classList.add('c-or-divider');
        element.textContent = 'or';
        return { element };
    }

    #removeOrDivider(element, position) {
        const maybeDivider =
            element[
                {
                    before: 'previousElementSibling',
                    after: 'nextElementSibling'
                }[position]
            ];
        if (maybeDivider.matches('.c-or-divider')) {
            maybeDivider.remove();
        }
    }
}

function detectLang() {
    const localeKeys = Object.keys(DATA.languageNames);
    for (const lang of navigator.languages || [navigator.language]) {
        if (localeKeys.includes(lang)) return lang;
        // Try the base language tag (e.g. "fr-CA" → "fr")
        const base = lang.split('-')[0];
        const match = localeKeys.find(
            (l) => l === base || l.startsWith(base + '-')
        );
        if (match) return match;
    }
    return 'en-US';
}

customElements.define('firefox-download-form', FirefoxDownloadFormElement);
