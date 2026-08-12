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
        ReferralAttribution._cachedResponseData = null;
        ReferralAttribution._signingComplete = false;
        ReferralAttribution._pendingClick = null;
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

        it('calls applyReferral with the invitation code when checked', function () {
            spyOn(ReferralAttribution, 'applyReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.applyReferral).toHaveBeenCalledWith(
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
            spyOn(ReferralAttribution, 'applyReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.applyReferral).not.toHaveBeenCalled();
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
                'utm_content%3Dfxrefer' + INVITATION_CODE
            );
        });

        it('rewrites the Android badge href to get-firefox campaign without utm_content when unchecked', function () {
            // First apply referral...
            ReferralAttribution.processAttributionRequest(true);
            // ...then remove it.
            ReferralAttribution.processAttributionRequest(false);

            const badge = fixture.querySelector('.fl-store-button-android');
            const href = badge.getAttribute('href');
            expect(href).toContain('utm_campaign%3Dget-firefox');
            expect(href).not.toContain('utm_content');
        });

        it('does not call ReferralAttribution.applyReferral on Android', function () {
            spyOn(ReferralAttribution, 'applyReferral');

            ReferralAttribution.processAttributionRequest(true);

            expect(ReferralAttribution.applyReferral).not.toHaveBeenCalled();
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
            spyOn(ReferralAttribution, 'applyReferral');

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
            expect(ReferralAttribution.applyReferral).toHaveBeenCalledWith(
                INVITATION_CODE
            );
        });

        it('shows the checkbox (opt-out = default checked) and rewrites Android links on Android', function () {
            window.site.platform = 'android';

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
            const badge = fixture.querySelector('.fl-store-button-android');
            expect(badge.getAttribute('href')).toContain('utm_content');
        });

        it('returns false and leaves the checkbox hidden when requirements are not met', function () {
            window.site.platform = 'ios';

            const result = ReferralAttribution.init();

            expect(result).toBeFalse();
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

    describe('_holdDesktopLinks / _interceptClick / _releaseDesktopLinks', function () {
        let link;
        let navigateSpy;

        beforeEach(function () {
            link = fixture.querySelector('#dl-win');
            navigateSpy = spyOn(ReferralAttribution, '_navigate');
            ReferralAttribution._signingComplete = false;
            ReferralAttribution._pendingClick = null;
        });

        it('_holdDesktopLinks prevents a click on a .download-link from navigating', function () {
            ReferralAttribution._holdDesktopLinks();

            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            expect(ReferralAttribution._pendingClick).toBe(link);
        });

        it('_releaseDesktopLinks navigates to the current href of the queued link on success', function () {
            ReferralAttribution._holdDesktopLinks();

            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );
            expect(ReferralAttribution._pendingClick).toBe(link);

            // Simulate signing success: link href is now decorated.
            const decorated =
                'https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US&attribution_code=CODE&attribution_sig=SIG';
            link.href = decorated;

            ReferralAttribution._releaseDesktopLinks();

            expect(navigateSpy).toHaveBeenCalledWith(decorated);
            expect(ReferralAttribution._pendingClick).toBeNull();
        });

        it('_releaseDesktopLinks navigates with the undecorated href on timeout (download still proceeds)', function () {
            const bare =
                'https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US';
            link.href = bare;

            ReferralAttribution._holdDesktopLinks();

            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            // Signing timed out — href was never decorated.
            ReferralAttribution._releaseDesktopLinks();

            expect(navigateSpy).toHaveBeenCalledWith(bare);
        });

        it('_releaseDesktopLinks is idempotent — a second call does not navigate again', function () {
            ReferralAttribution._holdDesktopLinks();
            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            ReferralAttribution._releaseDesktopLinks();
            ReferralAttribution._releaseDesktopLinks();

            expect(navigateSpy).toHaveBeenCalledTimes(1);
        });

        it('_releaseDesktopLinks does not navigate when no click was queued', function () {
            ReferralAttribution._holdDesktopLinks();
            ReferralAttribution._releaseDesktopLinks();

            expect(navigateSpy).not.toHaveBeenCalled();
        });

        it('clicks pass through without interception after _releaseDesktopLinks', function () {
            ReferralAttribution._holdDesktopLinks();
            ReferralAttribution._releaseDesktopLinks();

            // A click after release should not be stored.
            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            expect(ReferralAttribution._pendingClick).toBeNull();
        });
    });

    describe('applyReferral', function () {
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

            ReferralAttribution.applyReferral(INVITATION_CODE, success);

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

            ReferralAttribution.applyReferral(INVITATION_CODE);

            expect(
                Mozilla.DownloadAttribution.waitForGoogleAnalyticsThen
            ).toHaveBeenCalled();
        });

        it('holds .download-link clicks during the signing round-trip', function () {
            spyOn(Mozilla.DownloadAttribution, 'waitForGoogleAnalyticsThen');

            ReferralAttribution.applyReferral(INVITATION_CODE);

            const link = fixture.querySelector('#dl-win');
            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            expect(ReferralAttribution._pendingClick).toBe(link);
        });

        it('releases the held click after XHR success, navigating to the decorated href', function () {
            const navigateSpy = spyOn(ReferralAttribution, '_navigate');
            // Resolve the GA wait synchronously.
            spyOn(
                Mozilla.DownloadAttribution,
                'waitForGoogleAnalyticsThen'
            ).and.callFake((cb) => cb());
            spyOn(
                ReferralAttribution,
                'requestReferralAuthentication'
            ).and.callFake((_data, successCb) => {
                // Simulate XHR success: decorate links first, then fire callback.
                const link = fixture.querySelector('#dl-win');
                link.href +=
                    '&attribution_code=REFERRALCODE&attribution_sig=REFERRALSIG';
                successCb();
            });

            ReferralAttribution.applyReferral(INVITATION_CODE);

            const link = fixture.querySelector('#dl-win');
            // Queue the click before the XHR resolves (simulated synchronously above,
            // but the hold was installed before waitForGoogleAnalyticsThen was called).
            // Re-verify the release path by manually queuing a pending click.
            ReferralAttribution._pendingClick = link;
            ReferralAttribution._signingComplete = false;
            ReferralAttribution._releaseDesktopLinks();

            expect(navigateSpy).toHaveBeenCalledWith(link.href);
        });

        it('releases the held click on XHR timeout so the download still proceeds unattributed', function () {
            const navigateSpy = spyOn(ReferralAttribution, '_navigate');
            spyOn(
                Mozilla.DownloadAttribution,
                'waitForGoogleAnalyticsThen'
            ).and.callFake((cb) => cb());
            spyOn(
                ReferralAttribution,
                'requestReferralAuthentication'
            ).and.callFake((_data, _successCb, timeoutCb) => {
                timeoutCb();
            });

            const link = fixture.querySelector('#dl-win');
            ReferralAttribution._pendingClick = link;

            ReferralAttribution.applyReferral(INVITATION_CODE);

            expect(navigateSpy).toHaveBeenCalledWith(link.href);
        });

        it('sets referralActive to block the standard pipeline from overwriting links', function () {
            spyOn(Mozilla.DownloadAttribution, 'waitForGoogleAnalyticsThen');
            expect(Mozilla.DownloadAttribution.referralActive).toBeFalse();

            ReferralAttribution.applyReferral(INVITATION_CODE);

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
            expect(data.utm_content).toEqual('fxrefer1HR4FZ672Z8Y0E4HW');
        });

        it('always includes utm_content with the code', function () {
            expect(
                ReferralAttribution.getReferralData('TESTCODE').utm_content
            ).toEqual('fxreferTESTCODE');
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

        it('releases any held click immediately so an uncheck during signing does not block the download', function () {
            const navigateSpy = spyOn(ReferralAttribution, '_navigate');
            const link = container.querySelector('#referral-win');

            // Simulate a signing round in progress with a queued click.
            ReferralAttribution._signingComplete = false;
            ReferralAttribution._pendingClick = link;

            ReferralAttribution.removeReferral();

            // The download should proceed right away with the un-attributed href.
            expect(navigateSpy).toHaveBeenCalledWith(link.href);
            expect(ReferralAttribution._pendingClick).toBeNull();
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
                xhrRequests.push(this);
            }
            FakeXHR.prototype.open = jasmine.createSpy('open');
            FakeXHR.prototype.setRequestHeader = function (header, value) {
                this.headers[header] = value;
            };
            FakeXHR.prototype.send = jasmine.createSpy('send');

            spyOn(window, 'XMLHttpRequest').and.callFake(function () {
                return new FakeXHR();
            });
            window.site.platform = 'windows';
        });

        afterEach(function () {
            xhrRequests = [];
            window.site.platform = 'other';
        });

        it('does not share state with the standard DownloadAttribution inFlightXHR', function () {
            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer1HR4FZ672Z8Y0E4HW'
            });
            expect(xhrRequests.length).toBe(1);
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
                utm_content: 'fxrefer1HR4FZ672Z8Y0E4HW'
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

        it('does not update links when referralActive is false at XHR completion', function () {
            const container = document.createElement('div');
            container.innerHTML = `
                <a id="req-win2" class="download-link"
                   href="https://download.mozilla.org/?product=firefox-latest-ssl&os=win"
                   data-download-version="win">
                </a>`;
            document.body.appendChild(container);

            Mozilla.DownloadAttribution.referralActive = false;
            spyOn(Mozilla.DownloadAttribution, 'cleanBouncerLinks');
            spyOn(Mozilla.DownloadAttribution, 'updateBouncerLinks');

            ReferralAttribution.requestReferralAuthentication({
                utm_content: 'fxrefer1HR4FZ672Z8Y0E4HW'
            });

            const req = xhrRequests[0];
            req.status = 200;
            req.responseText = JSON.stringify({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });
            req.readyState = 4;
            req.onreadystatechange();

            // Response is cached even though links are not updated.
            expect(ReferralAttribution._cachedResponseData).toEqual({
                attribution_code: 'REFERRALCODE',
                attribution_sig: 'REFERRALSIG'
            });
            expect(
                Mozilla.DownloadAttribution.cleanBouncerLinks
            ).not.toHaveBeenCalled();
            expect(
                Mozilla.DownloadAttribution.updateBouncerLinks
            ).not.toHaveBeenCalled();

            document.body.removeChild(container);
        });
    });
});
