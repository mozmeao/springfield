/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

const OS = {
    IOS: 'ios',
    MACOS: 'osx',
    MACOSPKG: 'osx-pkg',

    ANDROID: 'android',

    WINDOWS: 'win',
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
    STABLE: 'firefox-latest-ssl',
    BETA: 'firefox-beta-latest-ssl',
    DEV: 'firefox-devedition-latest-ssl',
    NIGHTLY: 'firefox-nightly-latest-ssl',
    ESR: 'firefox-esr-latest-ssl',
    ESR115: 'firefox-esr115-latest-ssl'
};

const UNSUPPORTED_PLATFORMS_BY_RELEASE = {
    [RELEASES.STABLE]: [OS.LINUX32],
    [RELEASES.ESR]: [OS.IOS, OS.ANDROID],
    [RELEASES.ESR115]: [
        OS.IOS,
        OS.ANDROID,
        OS.WINDOWS64ARM,
        OS.LINUX32,
        OS.LINUX64ARM
    ],
    [RELEASES.BETA]: [OS.LINUX32],
    [RELEASES.DEV]: [OS.IOS, OS.ANDROID, OS.LINUX32],
    [RELEASES.NIGHTLY]: [OS.IOS, OS.LINUX32]
};

class FirefoxDownloadFormElement extends HTMLElement {
    get form() {
        return this.querySelector(':scope > form:first-child');
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
                // Setup
                this.form.addEventListener('input', this);
                this.form.addEventListener('invalid', this, true);

                this.#setConditionalDisplay();
                this.#validate();
                break;
            case 'input':
                this.#handleInput(event);
                break;
            case 'invalid':
                this.#handleInvalid(event);
                break;
        }
    }

    #handleInput(event) {
        this.#setConditionalDisplay();
        this.#validate();

        const [selectedOption] = event.target.selectedOptions;

        if (!selectedOption.disabled) event.target.setCustomValidity('');
        else event.target.setCustomValidity('Chosen option not available');

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

    #handleInvalid(event) {
        event.preventDefault();

        const fieldWrap = event.target.closest('.fl-field-wrap');

        if (fieldWrap.querySelector('.fl-field-error-message')) return;

        const errorMessage = document.createElement('deferred-alert');
        errorMessage.textContent = event.target.validationMessage;
        errorMessage.classList.add('fl-field-error-message');

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

        const isMobile = os.value === 'ios' || os.value === 'android';

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
            const isNotSupported = UNSUPPORTED_PLATFORMS_BY_RELEASE[
                releaseOption
            ].includes(os.value);

            if (!release.options[releaseOption]) continue;

            release.options[releaseOption].disabled = isNotSupported;
            release.options[releaseOption].hidden = isNotSupported;
        }
    }

    #validate() {
        const { os, release } = this.form.elements;

        const chosenReleaseIsNotSupported = UNSUPPORTED_PLATFORMS_BY_RELEASE[
            release.value
        ].includes(os.value);

        if (chosenReleaseIsNotSupported) {
            release.setCustomValidity(
                'Chosen release type is not available for this platform.'
            );
            release.reportValidity();
        } else {
            release.setCustomValidity('');
        }
    }
}

customElements.define('firefox-download-form', FirefoxDownloadFormElement);
