/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import PartnerDownload from '../../../../../media/js/firefox/download/partner-download.es6';
import Plausible from '../../../../../media/js/base/plausible/plausible.es6';

const WIN64_URL =
    'https://download.mozilla.org/?product=partner-firefox-release-acme-acme-001-latest&os=win64&lang=en-US';
const WIN_URL =
    'https://download.mozilla.org/?product=partner-firefox-release-acme-acme-001-latest&os=win&lang=en-US';
const OSX_URL =
    'https://download.mozilla.org/?product=partner-firefox-release-acme-acme-001-latest&os=osx&lang=en-US';
const SIGNED = { attribution_code: 'code123', attribution_sig: 'sig456' };

function options(windows, mac, linux, links = {}) {
    return {
        windows: { state: windows },
        mac: { state: mac },
        linux: { state: linux },
        links: links
    };
}

function signals(platform, overrides = {}) {
    return Object.assign(
        { platform: platform, isFirefox: false, fxSupported: true, x64: true },
        overrides
    );
}

// Let pending promise callbacks run between clock ticks.
async function flushPromises() {
    for (let i = 0; i < 10; i++) {
        await Promise.resolve();
    }
}

describe('partner-download.es6.js', function () {
    describe('getState', function () {
        const allAvailable = options('available', 'available', 'available', {
            win64: 'win64-link',
            win: 'win-link',
            osx: 'osx-link'
        });

        it('should treat Android and iOS, Firefox included, as an unbuilt device', function () {
            expect(
                PartnerDownload.getState(
                    signals('android', { isFirefox: true }),
                    allAvailable
                )
            ).toEqual({ state: 1, reason: 'device' });
            expect(
                PartnerDownload.getState(signals('ios'), allAvailable)
            ).toEqual({ state: 1, reason: 'device' });
        });

        it('should tell desktop Firefox users they already have Firefox', function () {
            expect(
                PartnerDownload.getState(
                    signals('windows', { isFirefox: true }),
                    allAvailable
                )
            ).toEqual({ state: 2, reason: 'firefox' });
        });

        it('should prefer the Firefox message over an unsupported system', function () {
            expect(
                PartnerDownload.getState(
                    signals('windows', { isFirefox: true, fxSupported: false }),
                    allAvailable
                )
            ).toEqual({ state: 2, reason: 'firefox' });
        });

        it('should send unsupported Windows and macOS to the unsupported message', function () {
            for (const platform of ['windows', 'osx']) {
                expect(
                    PartnerDownload.getState(
                        signals(platform, { fxSupported: false }),
                        allAvailable
                    )
                ).toEqual({ state: 3, reason: 'unsupported_os' });
            }
        });

        it('should offer the Mac repack when Mac is available', function () {
            expect(
                PartnerDownload.getState(signals('osx'), allAvailable)
            ).toEqual({ state: 4, link: 'osx-link' });
        });

        it('should offer regular Firefox when the language is not built', function () {
            expect(
                PartnerDownload.getState(
                    signals('windows'),
                    options('language', 'available', 'available')
                )
            ).toEqual({ state: 5, reason: 'language' });
        });

        it('should show the device message when the system has no build', function () {
            expect(
                PartnerDownload.getState(
                    signals('osx'),
                    options('available', 'device', 'available')
                )
            ).toEqual({ state: 6, reason: 'device' });
        });

        it('should show the partner Linux button when Linux is available', function () {
            expect(
                PartnerDownload.getState(signals('linux'), allAvailable)
            ).toEqual({ state: 7 });
        });

        it('should show the usual Linux options when Linux has no build', function () {
            expect(
                PartnerDownload.getState(
                    signals('linux'),
                    options('available', 'available', 'language')
                )
            ).toEqual({ state: 8, reason: 'language' });
            expect(
                PartnerDownload.getState(
                    signals('linux'),
                    options('available', 'available', 'device')
                )
            ).toEqual({ state: 9, reason: 'device' });
        });

        it('should treat other platforms as an unbuilt device', function () {
            expect(
                PartnerDownload.getState(signals('other'), allAvailable)
            ).toEqual({ state: 10, reason: 'device' });
        });

        it('should show the device message for a 64-bit-only build on a machine not detected as 64-bit', function () {
            expect(
                PartnerDownload.getState(
                    signals('windows', { x64: false }),
                    options('available', 'device', 'device', {
                        win64: 'win64-link'
                    })
                )
            ).toEqual({ state: 6, reason: 'device' });
        });
    });

    describe('chooseWindowsLink', function () {
        it('should pick 64-bit on a 64-bit machine when both builds exist', function () {
            expect(
                PartnerDownload.chooseWindowsLink(true, {
                    win64: 'win64-link',
                    win: 'win-link'
                })
            ).toBe('win64-link');
        });

        it('should pick 32-bit on a machine not detected as 64-bit', function () {
            expect(
                PartnerDownload.chooseWindowsLink(false, {
                    win64: 'win64-link',
                    win: 'win-link'
                })
            ).toBe('win-link');
        });

        it('should pick nothing for a 64-bit-only build on a machine not detected as 64-bit', function () {
            expect(
                PartnerDownload.chooseWindowsLink(false, {
                    win64: 'win64-link'
                })
            ).toBeNull();
        });

        it('should pick a 32-bit-only build on a 64-bit machine', function () {
            expect(
                PartnerDownload.chooseWindowsLink(true, { win: 'win-link' })
            ).toBe('win-link');
        });
    });

    describe('waitForBitness', function () {
        const originalUserAgentData = Object.getOwnPropertyDescriptor(
            Navigator.prototype,
            'userAgentData'
        );
        let originalArchSize;

        function stubUserAgentData(getHighEntropyValues) {
            Object.defineProperty(navigator, 'userAgentData', {
                configurable: true,
                value: { getHighEntropyValues: getHighEntropyValues }
            });
        }

        beforeEach(function () {
            jasmine.clock().install();
            originalArchSize = window.site.archSize;
            window.site.archSize = 32;
        });

        afterEach(function () {
            jasmine.clock().uninstall();
            window.site.archSize = originalArchSize;
            delete navigator.userAgentData;
            if (originalUserAgentData) {
                Object.defineProperty(
                    Navigator.prototype,
                    'userAgentData',
                    originalUserAgentData
                );
            }
        });

        it('should wait for client hints that report 64-bit', async function () {
            stubUserAgentData(
                () =>
                    new Promise((resolve) =>
                        setTimeout(() => resolve({ bitness: '64' }), 300)
                    )
            );
            let x64;
            PartnerDownload.waitForBitness().then((value) => (x64 = value));

            jasmine.clock().tick(299);
            await flushPromises();
            expect(x64).toBeUndefined();

            jasmine.clock().tick(1);
            await flushPromises();
            expect(x64).toBeTrue();
        });

        it('should count the machine as not 64-bit when client hints never arrive', async function () {
            // A promise that never settles.
            stubUserAgentData(() => new Promise(() => undefined));
            let x64;
            PartnerDownload.waitForBitness().then((value) => (x64 = value));

            jasmine.clock().tick(500);
            await flushPromises();
            expect(x64).toBeFalse();
        });
    });

    describe('begin', function () {
        let originalSite;
        let signedCookie;

        function renderPage(windows, mac, linux, links) {
            const linkMarkup = links
                .map(
                    ([linkOs, url]) =>
                        `<a class="download-link" data-download-version="${linkOs}" href="${url}"></a>`
                )
                .join('');
            document.body.insertAdjacentHTML(
                'beforeend',
                `<main class="c-partner-download" data-partner="acme" data-lang="en-US"
                    data-windows="${windows}" data-mac="${mac}" data-linux="${linux}">
                    <a id="partner-download-try-again" href="/en-US/download/all/">Try downloading again.</a>
                    <div class="c-partner-download-links" hidden>${linkMarkup}</div>
                </main>`
            );
        }

        function visitOn(platform, overrides = {}) {
            window.site = Object.assign(
                {},
                originalSite,
                {
                    platform: platform,
                    archSize: 64,
                    fxSupported: true,
                    isFirefox: () => false
                },
                overrides
            );
        }

        function attributionEvents() {
            return window.dataLayer.filter(
                (event) => event.type === 'direct-attribution'
            );
        }

        beforeEach(function () {
            jasmine.clock().install();
            jasmine.clock().mockDate();
            originalSite = window.site;
            window.dataLayer = [];
            signedCookie = null;
            spyOn(PartnerDownload, 'navigate');
            spyOn(window.Mozilla.TrackProductDownload, 'sendEventFromURL');
            spyOn(
                window.Mozilla.DownloadAttribution,
                'meetsFunctionalRequirements'
            ).and.returnValue(true);
            spyOn(
                window.Mozilla.DownloadAttribution,
                'hasSignedCookie'
            ).and.callFake(() => signedCookie !== null);
            spyOn(
                window.Mozilla.DownloadAttribution,
                'getSignedCookie'
            ).and.callFake(() => signedCookie);
            spyOn(window.Mozilla.DownloadAttribution, 'initAnalytics');
            spyOn(window.Mozilla.DownloadAttribution, 'initEssential');
        });

        afterEach(function () {
            jasmine.clock().uninstall();
            window.site = originalSite;
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = false;
            window.Mozilla.DownloadAttribution.inFlightXHR = null;
            window.Mozilla.DownloadAttribution.requestComplete = false;
            window.Mozilla.DownloadAttribution.successCallback = undefined;
            window.Mozilla.DownloadAttribution.timeoutCallback = undefined;
            const container = document.querySelector('.c-partner-download');
            if (container) {
                container.remove();
            }
        });

        it('should download the repack at 1 second when signing finishes earlier', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = true;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(400);
            signedCookie = SIGNED;
            window.Mozilla.DownloadAttribution.successCallback();
            await flushPromises();
            jasmine.clock().tick(599);
            await flushPromises();
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();

            jasmine.clock().tick(1);
            await flushPromises();
            const firedURL =
                PartnerDownload.navigate.calls.mostRecent().args[0];
            expect(firedURL).toBe(
                `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
            );
            expect(attributionEvents()).toEqual([
                jasmine.objectContaining({ action: 'success' })
            ]);
        });

        it('should wait past 1 second for signing that finishes at 1.6 seconds', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = true;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1599);
            await flushPromises();
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();

            signedCookie = SIGNED;
            window.Mozilla.DownloadAttribution.successCallback();
            await flushPromises();
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
            );
        });

        it('should download without attribution at 2 seconds when signing never returns', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = true;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1999);
            await flushPromises();
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();

            jasmine.clock().tick(1);
            await flushPromises();
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(OSX_URL);
            expect(attributionEvents()).toEqual([
                jasmine.objectContaining({ action: 'timeout' })
            ]);
        });

        it('should stop waiting when an in-flight signing request times out', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.inFlightXHR = {};
            window.Mozilla.DownloadAttribution.requestComplete = false;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1200);
            window.Mozilla.DownloadAttribution.timeoutCallback();
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(OSX_URL);
            expect(attributionEvents()).toEqual([
                jasmine.objectContaining({ action: 'timeout' })
            ]);
        });

        it('should not wait when nothing is signing', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(OSX_URL);
            expect(attributionEvents()).toEqual([]);
        });

        it('should apply an existing signed cookie straight away', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
            );
        });

        it('should replace attribution already on the link instead of repeating it', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [
                [
                    'osx',
                    `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
                ]
            ]);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
            );
        });

        it('should point "try again" at the downloaded URL and track it', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            const firedURL =
                PartnerDownload.navigate.calls.mostRecent().args[0];
            expect(
                document.getElementById('partner-download-try-again').href
            ).toBe(firedURL);
            expect(
                window.Mozilla.TrackProductDownload.sendEventFromURL
            ).toHaveBeenCalledWith(firedURL);
        });

        it('should pick the 64-bit Windows build on a 64-bit machine', async function () {
            visitOn('windows');
            spyOn(PartnerDownload, 'waitForBitness').and.returnValue(
                Promise.resolve(true)
            );
            renderPage('available', 'device', 'device', [
                ['win64', WIN64_URL],
                ['win', WIN_URL]
            ]);

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(WIN64_URL);
        });

        it('should never download on Linux, even with a partner build', async function () {
            visitOn('linux');
            renderPage('device', 'device', 'available', []);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(3000);
            await flushPromises();

            expect(
                document
                    .querySelector('.c-partner-download')
                    .getAttribute('data-state')
            ).toBe('7');
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();
        });

        it('should show the state without downloading for desktop Firefox', async function () {
            visitOn('osx', { isFirefox: () => true });
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(3000);
            await flushPromises();

            expect(
                document
                    .querySelector('.c-partner-download')
                    .getAttribute('data-state')
            ).toBe('2');
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();
        });

        it('should leave starting attribution to the site', async function () {
            visitOn('osx');
            renderPage('device', 'available', 'device', [['osx', OSX_URL]]);

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(3000);
            await flushPromises();

            expect(
                window.Mozilla.DownloadAttribution.initAnalytics
            ).not.toHaveBeenCalled();
            expect(
                window.Mozilla.DownloadAttribution.initEssential
            ).not.toHaveBeenCalled();
        });

        describe('analytics', function () {
            const REGULAR_URL =
                'https://download.mozilla.org/?product=firefox-latest-ssl&os=osx&lang=en-US';
            const PLAY_STORE_URL =
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox';

            function eventsNamed(name) {
                return window.dataLayer.filter((event) => event.event === name);
            }

            function clickDownloadLink(url) {
                const link = document.createElement('a');
                link.href = url;
                window.Mozilla.TrackProductDownload.handleLink({
                    target: link
                });
            }

            beforeEach(function () {
                document.documentElement.setAttribute(
                    'data-download-partner',
                    'acme'
                );
                spyOn(Plausible, 'trackEvent');
                // Bitness is covered above; Chrome's client hints would otherwise wait on the mocked clock.
                spyOn(PartnerDownload, 'waitForBitness').and.returnValue(
                    Promise.resolve(true)
                );
                window.Mozilla.TrackProductDownload.sendEventFromURL.and.callThrough();
            });

            afterEach(function () {
                document.documentElement.removeAttribute(
                    'data-download-partner'
                );
                delete window.plausible;
            });

            it('should mark the automatic partner download as a repack', async function () {
                window.plausible = jasmine.createSpy('plausible');
                visitOn('osx');
                renderPage('device', 'available', 'device', [['osx', OSX_URL]]);

                PartnerDownload.begin();
                await flushPromises();
                jasmine.clock().tick(1000);
                await flushPromises();

                expect(eventsNamed('firefox_download')).toEqual([
                    jasmine.objectContaining({
                        product: 'firefox',
                        partner: 'acme',
                        partner_download: 'repack'
                    })
                ]);
                // The download event's Plausible copy lives in another bundle, so check the shared global.
                expect(window.plausible).toHaveBeenCalledWith(
                    'product_download',
                    {
                        props: jasmine.objectContaining({
                            partner: 'acme',
                            partner_download: 'repack'
                        })
                    }
                );
            });

            it('should mark regular Firefox and store clicks as a fallback', function () {
                clickDownloadLink(REGULAR_URL);
                clickDownloadLink(PLAY_STORE_URL);

                const downloads = window.dataLayer.filter(
                    (event) =>
                        event.event === 'firefox_download' ||
                        event.event === 'firefox_mobile_download'
                );
                expect(
                    downloads.map((event) => event.partner_download)
                ).toEqual(['fallback', 'fallback']);
            });

            const unavailableCases = [
                [
                    'android',
                    {},
                    ['available', 'available', 'available'],
                    1,
                    'device'
                ],
                [
                    'osx',
                    { isFirefox: () => true },
                    ['available', 'available', 'available'],
                    2,
                    'firefox'
                ],
                [
                    'windows',
                    { fxSupported: false },
                    ['available', 'available', 'available'],
                    3,
                    'unsupported_os'
                ],
                [
                    'osx',
                    {},
                    ['available', 'language', 'available'],
                    5,
                    'language'
                ],
                ['osx', {}, ['available', 'device', 'available'], 6, 'device'],
                [
                    'linux',
                    {},
                    ['available', 'available', 'language'],
                    8,
                    'language'
                ],
                [
                    'linux',
                    {},
                    ['available', 'available', 'device'],
                    9,
                    'device'
                ],
                [
                    'other',
                    {},
                    ['available', 'available', 'available'],
                    10,
                    'device'
                ]
            ];

            for (const [
                platform,
                overrides,
                states,
                state,
                reason
            ] of unavailableCases) {
                it(`should send one unavailable event for state ${state}`, async function () {
                    visitOn(platform, overrides);
                    renderPage(...states, []);

                    PartnerDownload.begin();
                    await flushPromises();

                    expect(eventsNamed('partner_download_unavailable')).toEqual(
                        [
                            {
                                event: 'partner_download_unavailable',
                                partner: 'acme',
                                platform:
                                    platform === 'osx' ? 'macos' : platform,
                                download_language: 'en-US',
                                reason: reason,
                                non_interaction: true
                            }
                        ]
                    );
                    expect(Plausible.trackEvent).toHaveBeenCalledWith(
                        'partner_download_unavailable',
                        {
                            partner: 'acme',
                            platform: platform === 'osx' ? 'macos' : platform,
                            download_language: 'en-US',
                            reason: reason
                        }
                    );
                });
            }

            it('should send no unavailable event when the partner build is offered', async function () {
                visitOn('osx');
                renderPage('device', 'available', 'device', [['osx', OSX_URL]]);
                PartnerDownload.begin();
                await flushPromises();
                jasmine.clock().tick(1000);
                await flushPromises();
                document.querySelector('.c-partner-download').remove();

                visitOn('linux');
                renderPage('device', 'device', 'available', []);
                PartnerDownload.begin();
                await flushPromises();

                expect(eventsNamed('partner_download_unavailable')).toEqual([]);
            });
        });
    });
});
