/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import ReferralAttribution from '../../../../../media/js/firefox/referral/referral-attribution.es6';

const INVITATION_CODE = '1HR4FZ672Z8Y0E4HW';

/**
 * Minimal page fixture: a container with the data-referral-code attribute,
 * a .download-link (Windows bouncer URL), an Android store badge, and
 * the hidden referral consent checkbox label.
 */
function buildFixture(code) {
    const fixture = document.createElement('div');
    fixture.setAttribute('data-referral-code', code || INVITATION_CODE);
    fixture.innerHTML = `
        <div class="c-button-download-thanks">
            <a id="dl-win" class="download-link c-button-download-thanks-link"
               href="https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US"
               data-download-version="win"
               data-direct-link="https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US">
               Download Firefox
            </a>
        </div>
        <a id="android-badge" class="fl-store-button fl-store-button-android"
           href="https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-referral">
           Google Play
        </a>
        <label for="referral-consent" class="referral-consent-label hidden">
            <input type="checkbox" id="referral-consent" class="referral-consent-checkbox">
            <span>Let Mozilla count your install as a referral</span>
        </label>
        <p class="referral-unsupported-message hidden"></p>
    `;
    document.body.appendChild(fixture);
    return fixture;
}

describe('referral-attribution.es6.js', function () {
    let fixture;

    beforeEach(function () {
        fixture = buildFixture(INVITATION_CODE);
        window.site.platform = 'windows';
    });

    afterEach(function () {
        document.body.removeChild(fixture);
        window.site.platform = 'other';
        Mozilla.DownloadAttribution.removeSignedCookie();
        Mozilla.DownloadAttribution.referralActive = false;
        ReferralAttribution.referralInFlightXHR = null;
        ReferralAttribution._cachedResponseData = null;
        ReferralAttribution._savedAndroidHrefs = null;
    });

    describe('getInvitationCode', function () {
        it('reads the code from the data-referral-code attribute', function () {
            expect(ReferralAttribution.getInvitationCode()).toEqual(
                INVITATION_CODE
            );
        });

        it('returns null when the attribute is absent', function () {
            fixture.removeAttribute('data-referral-code');
            expect(ReferralAttribution.getInvitationCode()).toBeNull();
        });

        it('returns null when the attribute is empty', function () {
            fixture.setAttribute('data-referral-code', '');
            expect(ReferralAttribution.getInvitationCode()).toBeNull();
        });
    });

    describe('meetsRequirements', function () {
        it('returns false on iOS (iOS cannot participate)', function () {
            window.site.platform = 'ios';
            expect(ReferralAttribution.meetsRequirements()).toBeFalse();
        });

        it('returns false on desktop when DownloadAttribution functional requirements are not met', function () {
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(false);
            expect(ReferralAttribution.meetsRequirements()).toBeFalse();
        });

        it('returns true on Windows desktop when all requirements are met', function () {
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            expect(ReferralAttribution.meetsRequirements()).toBeTrue();
        });

        it('returns true on Android (participates via Play Store referrer)', function () {
            window.site.platform = 'android';
            expect(ReferralAttribution.meetsRequirements()).toBeTrue();
        });
    });

    describe('showCheckbox', function () {
        it('removes the hidden class and sets checked=true (opt-out default)', function () {
            const label = fixture.querySelector('.referral-consent-label');
            const checkbox = fixture.querySelector(
                '.referral-consent-checkbox'
            );

            expect(label.classList.contains('hidden')).toBeTrue();
            expect(checkbox.checked).toBeFalse();

            ReferralAttribution.showCheckbox();

            expect(label.classList.contains('hidden')).toBeFalse();
            expect(checkbox.checked).toBeTrue();
        });
    });

    describe('bindEvents', function () {
        it('binds the change event handler to all checkboxes', function () {
            ReferralAttribution.bindEvents();
            const checkbox = fixture.querySelector(
                '.referral-consent-checkbox'
            );
            expect(checkbox.disabled).toBeFalse();
        });
    });

    describe('setCheckboxState', function () {
        it('sets all checkboxes to the given state', function () {
            const checkbox = fixture.querySelector(
                '.referral-consent-checkbox'
            );
            ReferralAttribution.setCheckboxState(true);
            expect(checkbox.checked).toBeTrue();
            ReferralAttribution.setCheckboxState(false);
            expect(checkbox.checked).toBeFalse();
        });
    });

    describe('processAttributionRequest (desktop)', function () {
        beforeEach(function () {
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
        });

        it('calls initReferral with the invitation code when checked', function () {
            spyOn(ReferralAttribution, 'initReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.initReferral).toHaveBeenCalledWith(
                INVITATION_CODE
            );
        });

        it('calls removeReferral when unchecked', function () {
            spyOn(ReferralAttribution, 'removeReferral');

            ReferralAttribution.processAttributionRequest(false);

            expect(ReferralAttribution.removeReferral).toHaveBeenCalled();
        });

        it('does nothing when no invitation code is present', function () {
            fixture.removeAttribute('data-referral-code');
            spyOn(ReferralAttribution, 'initReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.initReferral).not.toHaveBeenCalled();
        });
    });

    describe('processAttributionRequest (Android)', function () {
        beforeEach(function () {
            window.site.platform = 'android';
        });

        it('rewrites the Android badge href to include utm_content when checked', function () {
            ReferralAttribution.processAttributionRequest(true);

            const badge = fixture.querySelector('.fl-store-button-android');
            expect(badge.getAttribute('href')).toContain(
                'utm_content%3Dfxrefer%3A' + INVITATION_CODE
            );
        });

        it('rewrites the Android badge href without utm_content when unchecked', function () {
            // First apply referral...
            ReferralAttribution.processAttributionRequest(true);
            // ...then remove it.
            ReferralAttribution.processAttributionRequest(false);

            const badge = fixture.querySelector('.fl-store-button-android');
            expect(badge.getAttribute('href')).not.toContain('utm_content');
        });

        it('does not call ReferralAttribution.initReferral on Android', function () {
            spyOn(ReferralAttribution, 'initReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.initReferral).not.toHaveBeenCalled();
        });

        it('rewrites download links that mobile-attribution has already set to Play Store', function () {
            // Simulate mobile-attribution having rewritten the /thanks/ link.
            const dlLink = fixture.querySelector('#dl-win');
            dlLink.setAttribute(
                'href',
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_source%3Dwww.firefox.com%26utm_medium%3Dreferral%26utm_campaign%3Dfirefox-referral'
            );

            ReferralAttribution.processAttributionRequest(true);

            expect(dlLink.getAttribute('href')).toContain(
                'utm_content%3Dfxrefer%3A'
            );
        });
    });

    describe('init', function () {
        it('returns false on iOS', function () {
            window.site.platform = 'ios';
            expect(ReferralAttribution.init()).toBeFalse();
        });

        it('returns false when no invitation code is in the DOM', function () {
            fixture.removeAttribute('data-referral-code');
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);

            expect(ReferralAttribution.init()).toBeFalse();
        });

        it('returns false when there are no checkbox elements', function () {
            fixture.querySelector('.referral-consent-label').remove();
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);

            expect(ReferralAttribution.init()).toBeFalse();
        });

        it('shows the checkbox (opt-out = default checked) and fires the initial attribution on desktop', function () {
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(ReferralAttribution, 'initReferral');

            const result = ReferralAttribution.init();

            expect(result).toBeTrue();
            const checkbox = fixture.querySelector(
                '.referral-consent-checkbox'
            );
            expect(checkbox.checked).toBeTrue();
            expect(
                fixture
                    .querySelector('.referral-consent-label')
                    .classList.contains('hidden')
            ).toBeFalse();
            expect(ReferralAttribution.initReferral).toHaveBeenCalledWith(
                INVITATION_CODE
            );
        });

        it('shows the checkbox and rewrites Android links on Android', function () {
            window.site.platform = 'android';

            const result = ReferralAttribution.init();

            expect(result).toBeTrue();
            const badge = fixture.querySelector('.fl-store-button-android');
            expect(badge.getAttribute('href')).toContain('utm_content');
        });

        it('shows the unsupported message and returns false when requirements are not met', function () {
            window.site.platform = 'ios';

            const result = ReferralAttribution.init();

            expect(result).toBeFalse();
            expect(
                fixture
                    .querySelector('.referral-unsupported-message')
                    .classList.contains('hidden')
            ).toBeFalse();
            expect(
                fixture
                    .querySelector('.referral-consent-label')
                    .classList.contains('hidden')
            ).toBeTrue();
        });
    });

    // -------------------------------------------------------------------------
    // Referral signing pipeline
    // -------------------------------------------------------------------------

    describe('initReferral', function () {
        beforeEach(function () {
            spyOn(
                Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(Mozilla.DownloadAttribution, 'cleanBouncerLinks');
            spyOn(Mozilla.DownloadAttribution, 'updateBouncerLinks');
        });

        it('uses in-memory cached response without GA wait or XHR on re-check', function () {
            spyOn(Mozilla.DownloadAttribution, 'waitForGoogleAnalyticsThen');
            ReferralAttribution._cachedResponseData = {
                attribution_code: 'CACHED_CODE',
                attribution_sig: 'CACHED_SIG'
            };
            const success = jasmine.createSpy('success');

            ReferralAttribution.initReferral(INVITATION_CODE, success);

            expect(
                Mozilla.DownloadAttribution.waitForGoogleAnalyticsThen
            ).not.toHaveBeenCalled();
            expect(
                Mozilla.DownloadAttribution.cleanBouncerLinks
            ).toHaveBeenCalled();
            expect(
                Mozilla.DownloadAttribution.updateBouncerLinks
            ).toHaveBeenCalledWith({
                attribution_code: 'CACHED_CODE',
                attribution_sig: 'CACHED_SIG'
            });
            expect(success).toHaveBeenCalled();
        });

        it('falls through to GA wait and XHR when no cached response is present', function () {
            spyOn(Mozilla.DownloadAttribution, 'waitForGoogleAnalyticsThen');

            ReferralAttribution.initReferral(INVITATION_CODE);

            expect(
                Mozilla.DownloadAttribution.waitForGoogleAnalyticsThen
            ).toHaveBeenCalled();
        });

        it('sets referralActive to block the standard pipeline from overwriting links', function () {
            spyOn(Mozilla.DownloadAttribution, 'waitForGoogleAnalyticsThen');
            expect(Mozilla.DownloadAttribution.referralActive).toBeFalse();

            ReferralAttribution.initReferral(INVITATION_CODE);

            expect(Mozilla.DownloadAttribution.referralActive).toBeTrue();
        });
    });

    describe('getReferralData', function () {
        it('returns the full referral utm set for a given code', function () {
            const data =
                ReferralAttribution.getReferralData('1HR4FZ672Z8Y0E4HW');
            expect(data.utm_source).toEqual('www.firefox.com');
            expect(data.utm_medium).toEqual('referral');
            expect(data.utm_campaign).toEqual(
                ReferralAttribution.REFERRAL_CAMPAIGN
            );
            expect(data.utm_content).toEqual('fxrefer:1HR4FZ672Z8Y0E4HW');
        });

        it('returns an empty object when no code is provided', function () {
            expect(
                Object.keys(ReferralAttribution.getReferralData(null)).length
            ).toEqual(0);
            expect(
                Object.keys(ReferralAttribution.getReferralData('')).length
            ).toEqual(0);
        });
    });

    describe('removeReferral', function () {
        let container;

        beforeEach(function () {
            window.site.platform = 'windows';
            container = document.createElement('div');
            container.innerHTML = `
                <a id="referral-win" class="download-link"
                   href="https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US"
                   data-download-version="win"
                   data-direct-link="https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US">
                </a>`;
            document.body.appendChild(container);
        });

        afterEach(function () {
            window.site.platform = 'other';
            document.body.removeChild(container);
        });

        it('strips referral attribution from links', function () {
            Mozilla.DownloadAttribution.updateBouncerLinks({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });
            const link = document.getElementById('referral-win');
            expect(link.href).toContain('attribution_code=REFERRALCODE');

            ReferralAttribution.removeReferral();

            expect(link.href).not.toContain('attribution_code');
        });

        it('re-applies the standard first-touch cookie after removing referral', function () {
            Mozilla.DownloadAttribution.setSignedCookie({
                attribution_code: 'STANDARDCODE',
                attribution_sig: 'STANDARDSIG'
            });
            Mozilla.DownloadAttribution.updateBouncerLinks({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });

            ReferralAttribution.removeReferral();

            const link = document.getElementById('referral-win');
            expect(link.href).toContain('attribution_code=STANDARDCODE');
            expect(link.href).not.toContain('REFERRALCODE');
        });

        it('clears referralActive so the standard pipeline can restore first-touch', function () {
            Mozilla.DownloadAttribution.referralActive = true;

            ReferralAttribution.removeReferral();

            expect(Mozilla.DownloadAttribution.referralActive).toBeFalse();
        });

        it('calls the successCallback if provided', function () {
            const cb = jasmine.createSpy('callback');
            ReferralAttribution.removeReferral(cb);
            expect(cb).toHaveBeenCalled();
        });

        it('does not corrupt the standard signed cookies', function () {
            Mozilla.DownloadAttribution.setSignedCookie({
                attribution_code: 'STANDARDCODE',
                attribution_sig: 'STANDARDSIG'
            });
            ReferralAttribution.removeReferral();
            expect(
                Mozilla.Cookies.getItem(
                    Mozilla.DownloadAttribution.COOKIE_CODE_ID
                )
            ).toEqual('STANDARDCODE');
        });
    });

    describe('requestReferralAuthentication', function () {
        let xhrRequests = [];

        beforeEach(function () {
            xhrRequests = [];

            function FakeXHR() {
                this.headers = {};
                this.readyState = 0;
                this.status = 0;
                this.responseText = '';
                this.onreadystatechange = null;
                this.aborted = false;
                xhrRequests.push(this);
            }
            FakeXHR.prototype.open = jasmine.createSpy('open');
            FakeXHR.prototype.setRequestHeader = function (header, value) {
                this.headers[header] = value;
            };
            FakeXHR.prototype.send = jasmine.createSpy('send');
            FakeXHR.prototype.abort = function () {
                this.aborted = true;
            };

            spyOn(window, 'XMLHttpRequest').and.callFake(function () {
                return new FakeXHR();
            });
            window.site.platform = 'windows';
        });

        afterEach(function () {
            xhrRequests = [];
            window.site.platform = 'other';
        });

        it('uses a separate in-flight handle that does not share with the standard inFlightXHR', function () {
            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer:1HR4FZ672Z8Y0E4HW'
            });
            expect(ReferralAttribution.referralInFlightXHR).not.toBeNull();
            // Standard in-flight should be untouched.
            expect(Mozilla.DownloadAttribution.inFlightXHR).toBeNull();
        });

        it('caches the signed response in memory on success and does not touch standard cookies', function () {
            const container = document.createElement('div');
            container.innerHTML = `
                <a id="req-win" class="download-link"
                   href="https://download.mozilla.org/?product=firefox-latest-ssl&os=win"
                   data-download-version="win">
                </a>`;
            document.body.appendChild(container);

            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer:1HR4FZ672Z8Y0E4HW'
            });

            const req = xhrRequests[0];
            req.status = 200;
            req.responseText = JSON.stringify({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });
            req.readyState = 4;
            req.onreadystatechange();

            expect(ReferralAttribution._cachedResponseData).toEqual({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });
            // Standard cookies must not be touched.
            expect(
                Mozilla.Cookies.hasItem(
                    Mozilla.DownloadAttribution.COOKIE_CODE_ID
                )
            ).toBeFalsy();

            document.body.removeChild(container);
        });

        it('aborts a prior referral XHR when a new one is issued (rapid toggle)', function () {
            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer:FIRST'
            });
            const firstXHR = ReferralAttribution.referralInFlightXHR;

            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer:SECOND'
            });

            expect(firstXHR.aborted).toBeTruthy();
            expect(ReferralAttribution.referralInFlightXHR).not.toEqual(
                firstXHR
            );
        });
    });
});
