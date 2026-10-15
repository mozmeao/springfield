/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import MarketingOptOut from '../../../../../media/js/firefox/landing/get/marketing-opt-out-v2.es6';

const labelSelector = '.marketing-opt-out-checkbox-label.hidden';
const checkboxSelector = '.marketing-opt-out-checkbox-input:checked';

describe('marketing-opt-out.es6.js', function () {
    beforeEach(function () {
        const optOut = `<div id="opt-out">
            <label for="marketing-opt-out-primary" class="marketing-opt-out-checkbox-label hidden">
                <input type="checkbox" id="marketing-opt-out-primary" class="marketing-opt-out-checkbox-input">.
            </label>
            <label for="marketing-opt-out-secondary" class="marketing-opt-out-checkbox-label hidden">
                <input type="checkbox" id="marketing-opt-out-secondary" class="marketing-opt-out-checkbox-input">.
            </label>
        </div>
        <aside id="opt-out-banner" class="fl-marketing-opt-out-banner hidden">
            <button type="button" class="marketing-opt-out-banner-dismiss">Close</button>
        </aside>
        <div id="opt-out-download-links" class="c-button-download-thanks">
        <a class="download-link"
        href="https://download.mozilla.org/?product=firefox&os=win64&lang=en-US">
         Download
        </a>
        <a class="download-link"
            href="https://download.mozilla.org/?product=firefox&os=win64&lang=en-US">
            Download
        </a>
        </div>`;

        document.body.insertAdjacentHTML('beforeend', optOut);

        // Mock initAnalytics to avoid real XHR request
        spyOn(window.Mozilla.DownloadAttribution, 'initAnalytics');
    });

    afterEach(function () {
        const optOut = document.getElementById('opt-out');
        optOut.parentNode.removeChild(optOut);
        const optOutDownloadLinks = document.getElementById(
            'opt-out-download-links'
        );
        optOutDownloadLinks.parentNode.removeChild(optOutDownloadLinks);
        const optOutBanner = document.getElementById('opt-out-banner');
        optOutBanner.parentNode.removeChild(optOutBanner);

        document
            .getElementsByTagName('html')[0]
            .removeAttribute('data-needs-consent');
    });

    describe('init()', function () {
        it('should return false if attribution requirements are not satisfied', function () {
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(false);

            const result = MarketingOptOut.init();
            expect(result).toBeFalse();

            const labels = document.querySelectorAll(labelSelector);
            expect(labels.length).toEqual(2);

            const checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(0);
        });

        it('should remove attribution data and reject analytics when visitor unchecks input', function () {
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(MarketingOptOut, 'shouldShowCheckbox').and.returnValue(true);
            spyOn(window.Mozilla.DownloadAttribution, 'removeAttributionData');
            spyOn(window.Mozilla.Cookies, 'setItem');

            const result = MarketingOptOut.init();
            expect(result).toBeTrue();

            const labels = document.querySelectorAll(labelSelector);
            expect(labels.length).toEqual(0);

            let checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(2);

            document.getElementById('marketing-opt-out-primary').click();
            expect(
                window.Mozilla.DownloadAttribution.removeAttributionData
            ).toHaveBeenCalled();
            expect(window.Mozilla.Cookies.setItem).toHaveBeenCalledWith(
                'moz-consent-pref',
                '{"analytics":false,"preference":true}',
                jasmine.any(String),
                '/',
                null,
                false,
                'lax'
            );

            checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(0);
        });

        it('should opt back into analytics and init attribution if visitor re-checks input', function () {
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(MarketingOptOut, 'shouldShowCheckbox').and.returnValue(true);
            spyOn(window.Mozilla.Cookies, 'setItem');

            const result = MarketingOptOut.init();
            expect(result).toBeTrue();

            const labels = document.querySelectorAll(labelSelector);
            expect(labels.length).toEqual(0);

            let checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(2);

            // Opt out
            document.getElementById('marketing-opt-out-primary').click();

            checkboxes = document.querySelectorAll(
                '.marketing-opt-out-checkbox-input:checked'
            );
            expect(checkboxes.length).toEqual(0);

            // Opt in
            document.getElementById('marketing-opt-out-secondary').click();
            expect(
                window.Mozilla.DownloadAttribution.initAnalytics
            ).toHaveBeenCalled();
            expect(window.Mozilla.Cookies.setItem).toHaveBeenCalledWith(
                'moz-consent-pref',
                '{"analytics":true,"preference":true}',
                jasmine.any(String),
                '/',
                null,
                false,
                'lax'
            );

            checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(2);
        });

        it('should remember a previous preference cookie choice if it exists', function () {
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(MarketingOptOut, 'shouldShowCheckbox').and.returnValue(true);
            spyOn(
                window.Mozilla.DownloadAttribution,
                'hasSignedCookie'
            ).and.returnValue(false);
            spyOn(window.Mozilla.DownloadAttribution, 'removeAttributionData');
            spyOn(window.Mozilla.Cookies, 'hasItem').and.returnValue(true);
            spyOn(window.Mozilla.Cookies, 'setItem');

            const obj = {
                analytics: true,
                preference: false
            };
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify(obj)
            );

            const result = MarketingOptOut.init();
            expect(result).toBeTrue();

            const labels = document.querySelectorAll(labelSelector);
            expect(labels.length).toEqual(0);

            let checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(2);

            document.getElementById('marketing-opt-out-primary').click();
            expect(
                window.Mozilla.DownloadAttribution.removeAttributionData
            ).toHaveBeenCalled();
            expect(window.Mozilla.Cookies.setItem).toHaveBeenCalledWith(
                'moz-consent-pref',
                '{"analytics":false,"preference":false}',
                jasmine.any(String),
                '/',
                null,
                false,
                'lax'
            );

            checkboxes = document.querySelectorAll(checkboxSelector);
            expect(checkboxes.length).toEqual(0);
        });
    });

    describe('banner visibility', function () {
        beforeEach(function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(false);
            window.Mozilla.dntEnabled = sinon.stub().returns(false);
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(
                window.Mozilla.DownloadAttribution,
                'hasSignedCookie'
            ).and.returnValue(false);
            spyOn(window.Mozilla.Cookies, 'hasItem').and.returnValue(false);
        });

        afterEach(function () {
            delete window.Mozilla.gpcEnabled;
            delete window.Mozilla.dntEnabled;
        });

        it('should keep the banner hidden for EU/EEA visitors without a consent cookie', function () {
            document
                .getElementsByTagName('html')[0]
                .setAttribute('data-needs-consent', 'True');

            expect(MarketingOptOut.init()).toBeFalse();
            expect(
                document
                    .getElementById('opt-out-banner')
                    .classList.contains('hidden')
            ).toBeTrue();
        });

        it('should keep the banner hidden when Global Privacy Control is on', function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);

            expect(MarketingOptOut.init()).toBeFalse();
            expect(
                document
                    .getElementById('opt-out-banner')
                    .classList.contains('hidden')
            ).toBeTrue();
        });

        it('should show the banner to visitors outside the EU/EEA', function () {
            expect(MarketingOptOut.init()).toBeTrue();
            expect(
                document
                    .getElementById('opt-out-banner')
                    .classList.contains('hidden')
            ).toBeFalse();
        });
    });

    describe('showCheckbox()', function () {
        it('should reveal the opt-out banner, and hide it on "Close" without storing anything', function () {
            spyOn(window.Mozilla.Cookies, 'setItem');
            const banner = document.getElementById('opt-out-banner');

            MarketingOptOut.showCheckbox();
            expect(banner.classList.contains('hidden')).toBeFalse();

            banner.querySelector('.marketing-opt-out-banner-dismiss').click();
            expect(banner.classList.contains('hidden')).toBeTrue();
            expect(window.Mozilla.Cookies.setItem).not.toHaveBeenCalled();
        });

        it('should move focus to the element before the banner when "Close" is used from the keyboard', function () {
            const banner = document.getElementById('opt-out-banner');
            const close = banner.querySelector(
                '.marketing-opt-out-banner-dismiss'
            );

            MarketingOptOut.showCheckbox();
            close.focus();
            close.click();

            expect(document.activeElement).toBe(banner.previousElementSibling);
        });

        it('should add marketing_consent=1 param to all download links', function () {
            MarketingOptOut.showCheckbox();
            const links = document.querySelectorAll('.download-link');
            links.forEach(function (link) {
                expect(link.getAttribute('href')).toContain(
                    'marketing_consent=1'
                );
            });
        });
    });

    describe('processAttributionRequest()', function () {
        beforeEach(function () {
            spyOn(window.Mozilla.DownloadAttribution, 'removeAttributionData');
            spyOn(window.Mozilla.Cookies, 'setItem');
            // mock the addition of the param from showCheckbox
            const links = document.querySelectorAll('.download-link');
            links.forEach(function (link) {
                const href = link.getAttribute('href');
                link.setAttribute('href', href + '&marketing_consent=1');
            });
        });

        it('should remove marketing_consent param from all download links when unchecked', function () {
            MarketingOptOut.processAttributionRequest(false);
            const links = document.querySelectorAll('.download-link');
            links.forEach(function (link) {
                expect(link.getAttribute('href')).not.toContain(
                    'marketing_consent'
                );
            });
        });

        it('should not remove marketing_consent param when checked (opt-in path)', function () {
            MarketingOptOut.processAttributionRequest(true);
            const links = document.querySelectorAll('.download-link');
            links.forEach(function (link) {
                expect(link.getAttribute('href')).toContain(
                    'marketing_consent=1'
                );
            });
        });
    });
});
