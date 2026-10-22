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

const PRODUCT_URL =
    'https://download.mozilla.org/?product=partner-firefox-release-acme-acme-001-latest';
const WIN64_URL = `${PRODUCT_URL}&os=win64&lang=en-US`;
const WIN_URL = `${PRODUCT_URL}&os=win&lang=en-US`;
const OSX_URL = `${PRODUCT_URL}&os=osx&lang=en-US`;
const SIGNED = { attribution_code: 'code123', attribution_sig: 'sig456' };
const SIGNED_OSX_URL = `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`;
const STATES = [
    'download',
    'linux',
    'firefox',
    'language',
    'device',
    'linux_language',
    'linux_device',
    'unsupported_os'
];

function renderPage(builds, links = []) {
    const linkMarkup = links
        .map(
            ([linkOs, url]) =>
                `<a class="download-link" data-download-version="${linkOs}" href="${url}"></a>`
        )
        .join('');
    const sections = STATES.map(
        (state) => `<section data-state="${state}" hidden></section>`
    ).join('');
    document.body.insertAdjacentHTML(
        'beforeend',
        `<main class="c-partner-download" data-partner="acme" data-lang="en-US"
            data-windows="${builds.windows}" data-osx="${builds.osx}" data-linux="${builds.linux}">
            <a id="partner-download-try-again" href="/en-US/download/all/">Try downloading again.</a>
            <div class="c-partner-download-links" hidden>${linkMarkup}</div>
            ${sections}
        </main>`
    );
    return document.querySelector('.c-partner-download');
}

// Let pending promise callbacks run between clock ticks.
async function flushPromises() {
    for (let i = 0; i < 10; i++) {
        await Promise.resolve();
    }
}

describe('partner-download.es6.js', function () {
    let container;

    afterEach(function () {
        if (container) {
            container.remove();
            container = null;
        }
    });

    describe('getState', function () {
        const allAvailable = {
            windows: 'available',
            osx: 'available',
            linux: 'available'
        };
        const link = document.createElement('a');

        function site(platform, overrides = {}) {
            return Object.assign(
                {
                    platform: platform,
                    isFirefox: () => false,
                    fxSupported: true
                },
                overrides
            );
        }

        it('should treat Android and iOS, Firefox included, as an unbuilt device', function () {
            expect(
                PartnerDownload.getState(
                    site('android', { isFirefox: () => true }),
                    allAvailable,
                    null
                )
            ).toBe('device');
            expect(
                PartnerDownload.getState(site('ios'), allAvailable, null)
            ).toBe('device');
        });

        it('should tell desktop Firefox users they already have Firefox, supported or not', function () {
            expect(
                PartnerDownload.getState(
                    site('windows', {
                        isFirefox: () => true,
                        fxSupported: false
                    }),
                    allAvailable,
                    link
                )
            ).toBe('firefox');
        });

        it('should send unsupported Windows and macOS to the unsupported message', function () {
            for (const platform of ['windows', 'osx']) {
                expect(
                    PartnerDownload.getState(
                        site(platform, { fxSupported: false }),
                        allAvailable,
                        link
                    )
                ).toBe('unsupported_os');
            }
        });

        it('should download when there is a partner build for the machine', function () {
            expect(
                PartnerDownload.getState(site('osx'), allAvailable, link)
            ).toBe('download');
        });

        it('should say why Windows and macOS have no partner build', function () {
            const builds = {
                windows: 'available',
                osx: 'language',
                linux: 'device'
            };
            expect(PartnerDownload.getState(site('osx'), builds, null)).toBe(
                'language'
            );
            expect(
                PartnerDownload.getState(
                    site('osx'),
                    Object.assign({}, builds, { osx: 'device' }),
                    null
                )
            ).toBe('device');
            // A 64-bit-only build on a machine not detected as 64-bit.
            expect(
                PartnerDownload.getState(site('windows'), builds, null)
            ).toBe('device');
        });

        it('should show the partner Linux button, or why Linux has no build', function () {
            spyOn(PartnerDownload, 'isArm').and.returnValue(false);
            for (const linux of ['available', 'language', 'device']) {
                expect(
                    PartnerDownload.getState(
                        site('linux'),
                        { windows: 'available', osx: 'available', linux },
                        null
                    )
                ).toBe(linux === 'available' ? 'linux' : `linux_${linux}`);
            }
        });

        it('should send ARM Linux to the regular Linux options', function () {
            spyOn(PartnerDownload, 'isArm').and.returnValue(true);

            expect(
                PartnerDownload.getState(site('linux'), allAvailable, null)
            ).toBe('linux_device');
        });

        it('should treat other platforms as an unbuilt device', function () {
            expect(
                PartnerDownload.getState(site('other'), allAvailable, null)
            ).toBe('device');
        });
    });

    describe('findLink', function () {
        function linkFor(platform, x64, links) {
            container = renderPage(
                { windows: 'available', osx: 'available', linux: 'device' },
                links
            );
            const link = PartnerDownload.findLink(container, platform, x64);
            container.remove();
            return link && link.href;
        }

        const bothWindows = [
            ['win64', WIN64_URL],
            ['win', WIN_URL]
        ];

        it('should pick the 64-bit Windows build only for a 64-bit machine', function () {
            expect(linkFor('windows', true, bothWindows)).toBe(WIN64_URL);
            expect(linkFor('windows', false, bothWindows)).toBe(WIN_URL);
            expect(
                linkFor('windows', false, [['win64', WIN64_URL]])
            ).toBeNull();
            expect(linkFor('windows', true, [['win', WIN_URL]])).toBe(WIN_URL);
        });

        it('should pick the Mac build on macOS and nothing elsewhere', function () {
            const links = [['osx', OSX_URL], ...bothWindows];
            expect(linkFor('osx', true, links)).toBe(OSX_URL);
            expect(linkFor('linux', true, links)).toBeNull();
        });
    });

    describe('isX64', function () {
        const originalUserAgentData = Object.getOwnPropertyDescriptor(
            Navigator.prototype,
            'userAgentData'
        );
        let originalSite;

        function stubUserAgentData(getHighEntropyValues) {
            Object.defineProperty(navigator, 'userAgentData', {
                configurable: true,
                value: { getHighEntropyValues: getHighEntropyValues }
            });
        }

        beforeEach(function () {
            jasmine.clock().install();
            originalSite = window.site;
            window.site = Object.assign({}, originalSite, {
                platform: 'windows',
                archSize: 32,
                getArchSize: () => 32
            });
        });

        afterEach(function () {
            jasmine.clock().uninstall();
            window.site = originalSite;
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
            stubUserAgentData(() => wait(300, { bitness: '64' }));
            let x64;
            PartnerDownload.isX64().then((value) => (x64 = value));

            jasmine.clock().tick(299);
            await flushPromises();
            expect(x64).toBeUndefined();

            jasmine.clock().tick(1);
            await flushPromises();
            expect(x64).toBeTrue();
        });

        it('should fall back to the user agent when client hints never arrive', async function () {
            stubUserAgentData(() => new Promise(() => undefined));
            let x64;
            PartnerDownload.isX64().then((value) => (x64 = value));

            jasmine.clock().tick(500);
            await flushPromises();
            expect(x64).toBeFalse();
        });

        it('should fall back to the user agent, not the unconfirmed default, when client hints are slow', async function () {
            stubUserAgentData(() => new Promise(() => undefined));
            window.site.getArchSize = () => 64;
            let x64;
            PartnerDownload.isX64().then((value) => (x64 = value));

            jasmine.clock().tick(500);
            await flushPromises();
            expect(x64).toBeTrue();
        });

        it('should not ask for client hints off Windows', async function () {
            const getHighEntropyValues = jasmine.createSpy();
            stubUserAgentData(getHighEntropyValues);
            window.site.platform = 'osx';
            window.site.getArchSize = () => 64;

            expect(await PartnerDownload.isX64()).toBeTrue();
            expect(getHighEntropyValues).not.toHaveBeenCalled();
        });

        function wait(ms, value) {
            return new Promise((resolve) =>
                setTimeout(() => resolve(value), ms)
            );
        }
    });

    describe('begin', function () {
        const macBuild = {
            windows: 'device',
            osx: 'available',
            linux: 'device'
        };
        let originalSite;
        let signedCookie;

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

        function eventsNamed(name) {
            return window.dataLayer.filter((event) => event.event === name);
        }

        function attributionEvents() {
            return window.dataLayer.filter(
                (event) => event.type === 'direct-attribution'
            );
        }

        function shownStates() {
            return Array.from(
                container.querySelectorAll('section:not([hidden])')
            ).map((section) => section.getAttribute('data-state'));
        }

        beforeEach(function () {
            jasmine.clock().install();
            originalSite = window.site;
            window.dataLayer = [];
            signedCookie = null;
            spyOn(PartnerDownload, 'navigate');
            spyOn(PartnerDownload, 'isX64').and.returnValue(
                Promise.resolve(true)
            );
            spyOn(Plausible, 'trackEvent');
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
        });

        afterEach(function () {
            jasmine.clock().uninstall();
            window.site = originalSite;
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = false;
            window.Mozilla.DownloadAttribution.inFlightXHR = null;
            window.Mozilla.DownloadAttribution.requestComplete = false;
            window.Mozilla.DownloadAttribution.successCallback = undefined;
            window.Mozilla.DownloadAttribution.timeoutCallback = undefined;
        });

        it('should show only the chosen state', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);

            PartnerDownload.begin();
            await flushPromises();

            expect(shownStates()).toEqual(['download']);
        });

        it('should download at 1 second when nothing is signing, and point "try again" at it', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(999);
            await flushPromises();
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();

            jasmine.clock().tick(1);
            await flushPromises();
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(OSX_URL);
            expect(
                document.getElementById('partner-download-try-again').href
            ).toBe(OSX_URL);
            expect(
                window.Mozilla.TrackProductDownload.sendEventFromURL
            ).toHaveBeenCalledWith(OSX_URL);
            expect(attributionEvents()).toEqual([]);
        });

        it('should fall back to the regular download if the page script fails', async function () {
            window.site = undefined;
            container = renderPage(macBuild, [['osx', OSX_URL]]);

            expect(await PartnerDownload.begin()).toBe('device');
            expect(shownStates()).toEqual(['device']);
        });

        it('should keep a callback another script already registered', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
            const otherScriptCallback = jasmine.createSpy(
                'otherScriptCallback'
            );
            window.Mozilla.DownloadAttribution.successCallback =
                otherScriptCallback;
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = true;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1200);
            window.Mozilla.DownloadAttribution.successCallback();
            await flushPromises();

            expect(otherScriptCallback).toHaveBeenCalled();
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(OSX_URL);
        });

        it('should still send the unavailable event to Plausible when the data layer throws', async function () {
            visitOn('osx');
            container = renderPage({
                windows: 'device',
                osx: 'language',
                linux: 'device'
            });
            window.dataLayer = {
                push: () => {
                    throw new Error('GTM listener failed');
                }
            };

            expect(await PartnerDownload.begin()).toBe('language');
            expect(Plausible.trackEvent).toHaveBeenCalledWith(
                'partner_download_unavailable',
                jasmine.objectContaining({ reason: 'language' })
            );
        });

        it('should drop attribution from "try again" when consent is withdrawn after the download', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                `${OSX_URL}&attribution_code=code123&attribution_sig=sig456`
            );

            signedCookie = null;
            const tryAgain = document.getElementById(
                'partner-download-try-again'
            );
            // Keep the test page from following the link.
            tryAgain.addEventListener('click', (event) =>
                event.preventDefault()
            );
            tryAgain.click();

            expect(tryAgain.href).toBe(OSX_URL);
            expect(
                window.Mozilla.TrackProductDownload.sendEventFromURL
            ).toHaveBeenCalledWith(OSX_URL);
        });

        it('should still wait the full second when signing finishes sooner', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
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
            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                SIGNED_OSX_URL
            );
            expect(attributionEvents()).toEqual([
                jasmine.objectContaining({ action: 'success' })
            ]);
        });

        it('should wait past 1 second for signing that finishes at 1.6 seconds', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
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
                SIGNED_OSX_URL
            );
        });

        it('should download without attribution at 2 seconds when signing never returns', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
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

        it('should still download when the data layer throws', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.gettingAnalyticsData = true;
            spyOn(window.dataLayer, 'push').and.throwError('GTM failed');

            PartnerDownload.begin();
            await flushPromises();
            signedCookie = SIGNED;
            window.Mozilla.DownloadAttribution.successCallback();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                SIGNED_OSX_URL
            );
        });

        it('should stop waiting when an in-flight signing request times out', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [['osx', OSX_URL]]);
            window.Mozilla.DownloadAttribution.inFlightXHR = {};

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

        it('should replace attribution already on the link with the signed cookie', async function () {
            visitOn('osx');
            container = renderPage(macBuild, [
                ['osx', `${OSX_URL}&attribution_code=old&attribution_sig=old`]
            ]);
            signedCookie = SIGNED;

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(
                SIGNED_OSX_URL
            );
        });

        it('should pick the 64-bit Windows build on a 64-bit machine', async function () {
            visitOn('windows');
            container = renderPage(
                { windows: 'available', osx: 'device', linux: 'device' },
                [
                    ['win64', WIN64_URL],
                    ['win', WIN_URL]
                ]
            );

            PartnerDownload.begin();
            await flushPromises();
            jasmine.clock().tick(1000);
            await flushPromises();

            expect(PartnerDownload.navigate).toHaveBeenCalledWith(WIN64_URL);
        });

        it('should never download on Linux or in desktop Firefox', async function () {
            const cases = [
                ['linux', {}, 'linux'],
                ['osx', { isFirefox: () => true }, 'firefox']
            ];
            for (const [platform, overrides, expectedState] of cases) {
                visitOn(platform, overrides);
                container = renderPage(
                    { windows: 'device', osx: 'available', linux: 'available' },
                    [['osx', OSX_URL]]
                );

                PartnerDownload.begin();
                await flushPromises();
                jasmine.clock().tick(3000);
                await flushPromises();

                expect(shownStates()).toEqual([expectedState]);
                container.remove();
            }
            expect(PartnerDownload.navigate).not.toHaveBeenCalled();
        });

        const unavailableCases = [
            ['android', {}, macBuild, 'device'],
            ['osx', { isFirefox: () => true }, macBuild, 'firefox'],
            ['windows', { fxSupported: false }, macBuild, 'unsupported_os'],
            [
                'osx',
                {},
                { windows: 'device', osx: 'language', linux: 'device' },
                'language'
            ],
            [
                'osx',
                {},
                { windows: 'device', osx: 'device', linux: 'device' },
                'device'
            ],
            [
                'linux',
                {},
                { windows: 'device', osx: 'device', linux: 'language' },
                'language'
            ],
            ['linux', {}, macBuild, 'device'],
            ['other', {}, macBuild, 'device']
        ];

        for (const [platform, overrides, builds, reason] of unavailableCases) {
            it(`should send one unavailable event on ${platform} with reason ${reason}`, async function () {
                visitOn(platform, overrides);
                container = renderPage(builds);

                PartnerDownload.begin();
                await flushPromises();

                const props = {
                    partner: 'acme',
                    platform: platform === 'osx' ? 'macos' : platform,
                    download_language: 'en-US',
                    reason: reason
                };
                expect(eventsNamed('partner_download_unavailable')).toEqual([
                    Object.assign(
                        { event: 'partner_download_unavailable' },
                        props,
                        { non_interaction: true }
                    )
                ]);
                expect(Plausible.trackEvent).toHaveBeenCalledWith(
                    'partner_download_unavailable',
                    props
                );
            });
        }

        it('should send no unavailable event when the partner build is offered', async function () {
            for (const [platform, builds] of [
                ['osx', macBuild],
                [
                    'linux',
                    { windows: 'device', osx: 'device', linux: 'available' }
                ]
            ]) {
                visitOn(platform);
                container = renderPage(builds, [['osx', OSX_URL]]);
                PartnerDownload.begin();
                await flushPromises();
                jasmine.clock().tick(1000);
                await flushPromises();
                container.remove();
            }

            expect(eventsNamed('partner_download_unavailable')).toEqual([]);
        });
    });
});
