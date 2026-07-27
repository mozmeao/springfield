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
    shouldAutoDownload,
    getDownloadURL
} from '../../../../../media/js/firefox/download/auto-download.es6';

describe('auto-download.es6.js', function () {
    describe('shouldAutoDownload', function () {
        it('should return true for supported platforms', function () {
            expect(shouldAutoDownload('windows', true)).toBeTruthy();
            expect(shouldAutoDownload('osx', true)).toBeTruthy();
            expect(shouldAutoDownload('android', true)).toBeTruthy();
            expect(shouldAutoDownload('ios', true)).toBeTruthy();
        });

        it('should return false for linux platforms', function () {
            expect(shouldAutoDownload('linux', true)).toBeFalsy();
        });

        it('should return false for unknown platforms', function () {
            expect(shouldAutoDownload('other', true)).toBeFalsy();
        });

        it('should return false for non-supported Windows versions', function () {
            expect(shouldAutoDownload('windows', false)).toBeFalsy();
        });

        it('should return false for non-supported macOS versions', function () {
            expect(shouldAutoDownload('osx', false)).toBeFalsy();
        });
    });

    describe('getDownloadURL', function () {
        beforeEach(function () {
            const button = `<ul class="download-list">
                    <li><a id="thanks-download-button-win64" href="https://download.mozilla.org/?product=firefox-stub&amp;os=win64&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-win64-msi" href="https://download.mozilla.org/?product=firefox-msi-latest-ssl&amp;os=win64&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-win64-aarch64" href="https://download.mozilla.org/?product=firefox-latest-ssl&amp;os=win64-aarch64&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-win" href="https://download.mozilla.org/?product=firefox-stub&amp;os=win&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-win-msi" href="https://download.mozilla.org/?product=firefox-msi-latest-ssl&amp;os=win&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-osx" href="https://download.mozilla.org/?product=firefox-latest-ssl&amp;os=osx&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-linux64" href="https://download.mozilla.org/?product=firefox-latest-ssl&amp;os=linux64&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-linux" href="https://download.mozilla.org/?product=firefox-latest-ssl&amp;os=linux&amp;lang=en-US">Download Firefox</a></li>
                    <li><a id="thanks-download-button-android" href="https://play.google.com/store/apps/details?id=org.mozilla.firefox">Firefox for Android</a></li>
                    <li><a id="thanks-download-button-ios" href="https://itunes.apple.com/us/app/firefox-private-safe-browser/id989804926" data-cta-text="Firefox for iOS" data-cta-type="firefox_mobile">Firefox for iOS</a></li>
                </ul>`;

            document.body.insertAdjacentHTML('beforeend', button);
        });

        afterEach(function () {
            document.querySelectorAll('.download-list').forEach((e) => {
                e.parentNode.removeChild(e);
            });
        });

        it('should return the correct download for Windows', function () {
            const site = {
                platform: 'windows'
            };
            const result = getDownloadURL(site);
            expect(result).toEqual(
                'https://download.mozilla.org/?product=firefox-stub&os=win&lang=en-US'
            );
        });

        it('should return the correct download for macOS', function () {
            const site = {
                platform: 'osx'
            };
            const result = getDownloadURL(site);
            expect(result).toEqual(
                'https://download.mozilla.org/?product=firefox-latest-ssl&os=osx&lang=en-US'
            );
        });

        it('should not return a download for Linux', function () {
            const site = {
                platform: 'linux',
                archSize: 32
            };
            const result = getDownloadURL(site);
            expect(result).toBeFalsy();
        });

        it('should return the correct download for Android', function () {
            const site = {
                platform: 'android'
            };
            const result = getDownloadURL(site);
            expect(result).toEqual(
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox'
            );
        });

        it('should return the correct download for iOS', function () {
            const site = {
                platform: 'ios'
            };
            const result = getDownloadURL(site);
            expect(result).toEqual(
                'https://itunes.apple.com/us/app/firefox-private-safe-browser/id989804926'
            );
        });
    });
});
