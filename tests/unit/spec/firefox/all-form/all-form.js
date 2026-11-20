/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import {
    downloadURL,
    init,
    releaseHasLanguage,
    releaseSupportsPlatform
} from '../../../../../media/js/firefox/all-form/all-form.js';

const RELEASE_LABELS = {
    stable: 'Firefox',
    beta: 'Firefox Beta',
    dev: 'Firefox Developer Edition',
    nightly: 'Firefox Nightly',
    esr: 'Firefox ESR'
};

const OS_LABELS = {
    osx: 'macOS',
    ios: 'iOS',
    android: 'Android',
    win64: 'Windows 64-bit',
    'win64-msi': 'Windows 64-bit MSI',
    linux64: 'Linux 64-bit'
};

const LANGUAGE_LABELS = {
    'en-US': 'English (US)',
    de: 'German - Deutsch',
    ja: 'Japanese - 日本語',
    ckb: 'Central Kurdish'
};

function byRelease(value) {
    return Object.fromEntries(
        Object.keys(RELEASE_LABELS).map((release) => [release, value(release)])
    );
}

// The shape all_form.get_client_data() serializes, cut down to what these
// specs select.
const DATA = {
    osValues: Object.keys(OS_LABELS),
    unsupportedPlatformsByRelease: {
        stable: [],
        beta: [],
        dev: ['ios', 'android'],
        nightly: ['ios'],
        esr: ['ios', 'android'],
        'esr-next': ['ios', 'android'],
        'esr-115': ['ios', 'android', 'linux64']
    },
    mobileOS: ['android', 'ios'],
    microsoftStoreOS: ['win64'],
    languagesByRelease: {
        stable: ['de', 'en-US', 'ja'],
        beta: ['de', 'en-US', 'ja'],
        dev: ['de', 'en-US', 'ja'],
        nightly: ['ckb', 'de', 'en-US', 'ja'],
        esr: ['de', 'en-US', 'ja'],
        'esr-next': [],
        'esr-115': ['de', 'en-US', 'ja']
    },
    bouncerUrl: 'https://download.mozilla.org/',
    bouncerChannels: {
        stable: '',
        beta: 'beta',
        nightly: 'nightly',
        dev: 'devedition',
        esr: 'esr',
        'esr-next': 'esr-next',
        'esr-115': 'esr115'
    },
    options: {
        primary: Object.fromEntries(
            ['desktop', 'ios', 'android'].map((family) => [
                family,
                byRelease((release) => ({
                    label: `Download ${RELEASE_LABELS[release]}`,
                    icon: 'downloads',
                    ctaText: `Download ${RELEASE_LABELS[release]}`
                }))
            ])
        ),
        apt: {
            label: 'Set up the APT repository',
            ctaText: 'Set up the APT repository',
            icon: 'external-link',
            classes: ['button-secondary'],
            href: 'https://support.mozilla.org/kb/install-firefox-linux'
        },
        esrNext: {
            available: false,
            label: 'Download Firefox ESR next',
            ctaText: 'Download Firefox ESR next',
            icon: 'downloads',
            classes: ['button-primary']
        },
        esr115: {
            label: 'Download Firefox ESR 115',
            ctaText: 'Download Firefox ESR 115',
            icon: 'downloads',
            classes: ['button-secondary', 'fl-button-small'],
            recommendations: {
                windows: 'Recommended for Windows 7/8/8.1',
                macos: 'Recommended for macOS 10.12–10.14'
            }
        },
        apk: {
            label: 'Download the APK',
            ctaText: 'Download the APK',
            icon: 'downloads',
            classes: ['button-secondary', 'fl-button-small'],
            hrefs: byRelease((release) =>
                release === 'stable'
                    ? 'https://ftp.mozilla.org/fenix.apk'
                    : null
            )
        },
        microsoftStore: {
            label: 'Download from the Microsoft Store',
            ctaText: 'Download from the Microsoft Store',
            icon: 'external-link',
            classes: ['button-secondary', 'fl-button-small'],
            hrefs: byRelease((release) =>
                release === 'stable'
                    ? 'https://apps.microsoft.com/firefox'
                    : null
            )
        }
    },
    storeUrls: {
        ios: byRelease((release) =>
            release === 'stable' ? 'https://apps.apple.com/firefox' : null
        ),
        android: byRelease((release) =>
            release === 'stable' ? 'https://play.google.com/firefox' : null
        )
    },
    supportLinks: {
        releaseNotes: {
            label: 'Release notes',
            urls: { desktop: byRelease(() => '/notes/'), ios: {}, android: {} }
        },
        systemRequirements: {
            label: 'System requirements',
            urls: { desktop: byRelease(() => '/sysreq/'), ios: {}, android: {} }
        },
        privacy: { label: 'Privacy notice', url: '/privacy/' }
    },
    messages: {
        releaseUnavailable: '{release} is not available for {os}.',
        languageUnavailable: '{language} is not available for {release}.',
        divider: 'or',
        languageIgnored: 'Matches your phone’s language.',
        conflict: 'There are no downloads for this combination.',
        fallback: 'See download options'
    }
};

function options(labels, selected) {
    return Object.entries(labels)
        .map(
            ([value, label]) =>
                `<option name="${value}" value="${value}"${value === selected ? ' selected' : ''}>${label}</option>`
        )
        .join('');
}

// The markup firefox/all-form/base.html renders, with what the element reads.
function formMarkup({ os = '', release = 'stable', language = 'en-US' }) {
    return `<div class="fl-main" id="all-form-fixture">
        <firefox-download-form>
            <form name="download" method="get" action="/result/">
                <div class="c-choices">
                    <div class="fl-field-wrap">
                        <select id="os" name="os" required>
                            <option value=""${os ? '' : ' selected'}></option>
                            ${options(OS_LABELS, os)}
                        </select>
                    </div>
                    <div class="fl-field-wrap">
                        <div id="release-no-js-hint"></div>
                        <select id="release" name="release" required aria-describedby="release-no-js-hint">
                            ${options(RELEASE_LABELS, release)}
                        </select>
                    </div>
                    <div class="fl-field-wrap">
                        <select id="language" name="language" required>
                            ${options(LANGUAGE_LABELS, language)}
                        </select>
                        <p class="c-language-message c-message-hidden"></p>
                    </div>
                </div>
                <div class="c-results">
                    <div class="c-download-options">
                        <div class="c-download-option" data-download-option="fallback">
                            <button type="submit">See download options</button>
                        </div>
                        <div class="c-download-option" data-download-option="qr-code" hidden>
                            <button type="button">Scan QR code</button>
                        </div>
                    </div>
                    <div class="c-incompatible-choices" hidden></div>
                </div>
            </form>
        </firefox-download-form>
        <dialog id="qr-code-dialog">
            <button type="button" class="fl-dialog-close-button"></button>
        </dialog>
    </div>`;
}

describe('all-form.js', function () {
    const originalURL = window.location.href;

    beforeAll(function () {
        init(DATA);
    });

    afterEach(function () {
        document.getElementById('all-form-fixture')?.remove();
        history.replaceState(null, '', originalURL);
    });

    // The element sets itself up when its form is slotted, which is async.
    async function renderForm(selection = {}) {
        document.body.insertAdjacentHTML('beforeend', formMarkup(selection));
        await new Promise((resolve) => setTimeout(resolve));
        return document.querySelector('#all-form-fixture form');
    }

    function choose(form, field, value) {
        form.elements[field].value = value;
        form.elements[field].dispatchEvent(
            new Event('input', { bubbles: true })
        );
    }

    function visibleError(form, field) {
        const error = document.getElementById(`${field}-error`);
        return error && !error.classList.contains('c-message-hidden')
            ? error.textContent.trim()
            : '';
    }

    function optionValues(select) {
        return [...select.options].map((option) => option.value);
    }

    function primaryHref(form) {
        return form.querySelector('[data-download-option="primary"] a').href;
    }

    describe('releaseSupportsPlatform', function () {
        it('treats an unchosen platform as no conflict', function () {
            expect(releaseSupportsPlatform('dev', '')).toBeTrue();
        });

        it('knows which platforms a release has builds for', function () {
            expect(releaseSupportsPlatform('dev', 'osx')).toBeTrue();
            expect(releaseSupportsPlatform('dev', 'ios')).toBeFalse();
        });

        it('rejects values the server did not send', function () {
            expect(() => releaseSupportsPlatform('aurora', 'osx')).toThrowError(
                RangeError
            );
            expect(() => releaseSupportsPlatform('dev', 'beos')).toThrowError(
                RangeError
            );
        });
    });

    describe('releaseHasLanguage', function () {
        it('knows which languages a release is built in', function () {
            expect(releaseHasLanguage('nightly', 'ckb')).toBeTrue();
            expect(releaseHasLanguage('stable', 'ckb')).toBeFalse();
            expect(releaseHasLanguage('esr-next', 'de')).toBeFalse();
        });
    });

    describe('downloadURL', function () {
        it('builds a bouncer URL for a desktop selection', function () {
            expect(downloadURL('win64', 'stable', 'de')).toBe(
                'https://download.mozilla.org/?os=win64&product=firefox-latest-ssl&lang=de'
            );
            expect(downloadURL('osx', 'beta', 'en-US')).toBe(
                'https://download.mozilla.org/?os=osx&product=firefox-beta-latest-ssl&lang=en-US'
            );
        });

        it('keeps the installer type in the product, not the OS', function () {
            expect(downloadURL('win64-msi', 'esr', 'de')).toBe(
                'https://download.mozilla.org/?os=win64&product=firefox-esr-msi-latest-ssl&lang=de'
            );
        });

        it('uses the localized product for Nightly outside en-US', function () {
            expect(downloadURL('linux64', 'nightly', 'de')).toBe(
                'https://download.mozilla.org/?os=linux64&product=firefox-nightly-latest-l10n-ssl&lang=de'
            );
            expect(downloadURL('linux64', 'nightly', 'en-US')).toBe(
                'https://download.mozilla.org/?os=linux64&product=firefox-nightly-latest-ssl&lang=en-US'
            );
        });

        it('uses the macOS locale for Japanese', function () {
            expect(downloadURL('osx', 'stable', 'ja')).toContain(
                'lang=ja-JP-mac'
            );
            expect(downloadURL('win64', 'stable', 'ja')).toContain('lang=ja');
        });

        it('has nothing to download for store apps or no platform', function () {
            expect(downloadURL('ios', 'stable', 'de')).toBe('');
            expect(downloadURL('', 'stable', 'de')).toBe('');
        });
    });

    describe('the form', function () {
        it('offers the bouncer download for the loaded selection', async function () {
            const form = await renderForm({ os: 'win64', language: 'de' });
            expect(primaryHref(form)).toBe(
                'https://download.mozilla.org/?os=win64&product=firefox-latest-ssl&lang=de'
            );
        });

        it('keeps a release the new OS lacks, disabled, and says why', async function () {
            const form = await renderForm({ os: 'osx', release: 'dev' });
            choose(form, 'os', 'ios');

            const release = form.elements.release;
            expect(release.value).toBe('dev');
            expect(release.selectedOptions[0].disabled).toBeTrue();
            expect(visibleError(form, 'release')).toBe(
                'Firefox Developer Edition is not available for iOS.'
            );
            expect(
                form.querySelector('.c-incompatible-choices').hidden
            ).toBeFalse();
        });

        it('only lists the releases the OS has, plus the kept selection', async function () {
            const form = await renderForm({ os: 'osx', release: 'dev' });
            choose(form, 'os', 'ios');
            expect(optionValues(form.elements.release)).toEqual([
                'stable',
                'beta',
                'dev'
            ]);

            choose(form, 'release', 'stable');
            expect(optionValues(form.elements.release)).toEqual([
                'stable',
                'beta'
            ]);
        });

        it('restores the choice and clears the error once it is valid again', async function () {
            const form = await renderForm({ os: 'osx', release: 'dev' });
            choose(form, 'os', 'ios');
            choose(form, 'os', 'osx');

            expect(
                form.elements.release.selectedOptions[0].disabled
            ).toBeFalse();
            expect(optionValues(form.elements.release)).toContain('nightly');
            expect(visibleError(form, 'release')).toBe('');
            expect(primaryHref(form)).toContain(
                'product=firefox-devedition-latest-ssl'
            );
        });

        it('keeps a language the new release lacks, disabled, and says why', async function () {
            const form = await renderForm({
                os: 'win64',
                release: 'nightly',
                language: 'ckb'
            });
            choose(form, 'release', 'stable');

            const language = form.elements.language;
            expect(language.value).toBe('ckb');
            expect(language.selectedOptions[0].disabled).toBeTrue();
            expect(visibleError(form, 'language')).toBe(
                'Central Kurdish is not available for Firefox.'
            );
            expect(
                form.querySelector('.c-incompatible-choices').hidden
            ).toBeFalse();

            choose(form, 'release', 'nightly');
            expect(visibleError(form, 'language')).toBe('');
            expect(primaryHref(form)).toContain('lang=ckb');
        });

        it('offers store links instead of downloads for mobile', async function () {
            const form = await renderForm({ os: 'android' });
            expect(primaryHref(form)).toBe('https://play.google.com/firefox');
            expect(
                form.querySelector('[data-download-option="apk"] a').href
            ).toBe('https://ftp.mozilla.org/fenix.apk');
        });

        it('updates the URL on edit and keeps campaign params', async function () {
            history.replaceState(null, '', '?utm_source=newsletter');
            const form = await renderForm({ os: 'win64' });
            choose(form, 'language', 'de');

            const params = new URLSearchParams(window.location.search);
            expect(params.get('utm_source')).toBe('newsletter');
            expect(params.get('os')).toBe('win64');
            expect(params.get('release')).toBe('stable');
            expect(params.get('language')).toBe('de');
        });
    });
});
