/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

const ANDROID_UA =
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36';
const IOS_UA =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
const DESKTOP_UA =
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36';

const ANDROID_STORE_PREFIX =
    'https://play.google.com/store/apps/details?id=org.mozilla.firefox';
const IOS_STORE_PREFIX = 'https://apps.apple.com/app/apple-store/id989804926';

describe('mobile-attribution.js', function () {
    let html;
    let container;

    beforeEach(function () {
        html = document.documentElement;
        container = document.createElement('div');
        // Suppress default <a> navigation for any test that dispatches a
        // click event. Synthetic clicks on real-looking URLs (e.g.
        // https://apps.apple.com/...) in headless CI browsers will navigate
        // the runner away, killing the rest of the suite — so we
        // preventDefault at the container level for any click that bubbles
        // out unhandled by a test's own listeners.
        container.addEventListener('click', function (event) {
            event.preventDefault();
        });
        document.body.appendChild(container);
    });

    afterEach(function () {
        // Clean up any campaign attrs the test set.
        html.removeAttribute('data-stub-attribution-campaign');
        html.removeAttribute('data-stub-attribution-campaign-override');
        html.removeAttribute('data-stub-attribution-campaign-force');
        document.body.removeChild(container);
    });

    describe('getCampaign', function () {
        const getCampaign = function (search) {
            return Mozilla.MobileAttribution.getCampaign(html, search);
        };

        it('returns null when nothing is set', function () {
            expect(getCampaign('')).toBeNull();
        });

        it('returns the default data attr when set', function () {
            html.setAttribute('data-stub-attribution-campaign', 'default-x');
            expect(getCampaign('')).toBe('default-x');
        });

        it('returns the URL utm_campaign when present', function () {
            expect(getCampaign('?utm_campaign=url-x')).toBe('url-x');
        });

        it('URL utm_campaign wins over default data attr', function () {
            html.setAttribute('data-stub-attribution-campaign', 'default-x');
            expect(getCampaign('?utm_campaign=url-x')).toBe('url-x');
        });

        it('override data attr wins over URL utm_campaign', function () {
            html.setAttribute(
                'data-stub-attribution-campaign-override',
                'override-x'
            );
            expect(getCampaign('?utm_campaign=url-x')).toBe('override-x');
        });

        it('force data attr wins over everything', function () {
            html.setAttribute(
                'data-stub-attribution-campaign-force',
                'force-x'
            );
            html.setAttribute(
                'data-stub-attribution-campaign-override',
                'override-x'
            );
            html.setAttribute('data-stub-attribution-campaign', 'default-x');
            expect(getCampaign('?utm_campaign=url-x')).toBe('force-x');
        });

        it('decodes URL-encoded utm_campaign values', function () {
            expect(getCampaign('?utm_campaign=hello%20world')).toBe(
                'hello world'
            );
        });

        it('handles utm_campaign as not the first query param', function () {
            expect(getCampaign('?foo=bar&utm_campaign=second')).toBe('second');
        });
    });

    describe('getStoreUrl', function () {
        it('builds an Android Play Store URL with the install_referrer', function () {
            const url = Mozilla.MobileAttribution.getStoreUrl('test-19', true);
            expect(url.indexOf(ANDROID_STORE_PREFIX)).toBe(0);
            expect(url).toContain('utm_campaign%3Dtest-19');
            expect(url).toContain('utm_source%3Dwww.firefox.com');
            expect(url).toContain('utm_medium%3Dreferral');
        });

        it('builds an iOS App Store URL with pt/ct', function () {
            const url = Mozilla.MobileAttribution.getStoreUrl('test-19', false);
            expect(url.indexOf(IOS_STORE_PREFIX)).toBe(0);
            expect(url).toContain('pt=373246');
            expect(url).toContain('ct=test-19');
            expect(url).toContain('mz_pr=firefox_mobile');
        });

        it('URL-encodes campaign values containing special characters', function () {
            const url = Mozilla.MobileAttribution.getStoreUrl(
                'hello world',
                true
            );
            expect(url).toContain('utm_campaign%3Dhello%20world');
        });
    });

    describe('rewriteLinks', function () {
        afterEach(function () {
            // Restore the TrackProductDownload namespace so other test suites
            // see it intact. Some tests delete or stub it.
            if (
                window.Mozilla &&
                !window.Mozilla.TrackProductDownload &&
                window._OriginalTrackProductDownload
            ) {
                window.Mozilla.TrackProductDownload =
                    window._OriginalTrackProductDownload;
                delete window._OriginalTrackProductDownload;
            }
        });

        it('rewrites HREFs of /thanks/-bound .c-button-download-thanks-link elements', function () {
            container.innerHTML =
                '<a class="c-button-download-thanks-link" href="/thanks/">Download</a>' +
                '<a class="c-button-download-thanks-link" href="/en-US/thanks/">Download</a>';

            Mozilla.MobileAttribution.rewriteLinks(container, 'TARGET');

            const links = container.querySelectorAll('a');
            expect(links[0].getAttribute('href')).toBe('TARGET');
            expect(links[1].getAttribute('href')).toBe('TARGET');
        });

        it('rewrites .download-link inside .c-button-download-thanks (nav and pre-footer pattern)', function () {
            // Nav and pre-footer pass exclude_unsupported_content=True, which
            // omits the `-link` suffix on the class. The .download-link inside
            // the wrapper still needs to be rewritten.
            container.innerHTML =
                '<div class="c-button-download-thanks">' +
                '<a class="download-link" href="/thanks/">Download</a>' +
                '</div>';

            Mozilla.MobileAttribution.rewriteLinks(container, 'TARGET');

            expect(container.querySelector('a').getAttribute('href')).toBe(
                'TARGET'
            );
        });

        it('leaves non-/thanks/ HREFs alone (Path A store buttons are unaffected)', function () {
            container.innerHTML =
                '<a class="c-button-download-thanks-link" href="/thanks/">Should rewrite</a>' +
                '<a class="fl-store-button fl-store-button-android" href="https://play.google.com/...">Should not rewrite</a>' +
                '<a class="fl-store-button fl-store-button-ios" href="https://apps.apple.com/...">Should not rewrite</a>';

            Mozilla.MobileAttribution.rewriteLinks(container, 'TARGET');

            expect(
                container
                    .querySelector('.c-button-download-thanks-link')
                    .getAttribute('href')
            ).toBe('TARGET');
            expect(
                container
                    .querySelector('.fl-store-button-android')
                    .getAttribute('href')
            ).toBe('https://play.google.com/...');
            expect(
                container
                    .querySelector('.fl-store-button-ios')
                    .getAttribute('href')
            ).toBe('https://apps.apple.com/...');
        });

        it('skips elements whose href is not /thanks/', function () {
            // Defense in depth: even if the class lands on a non-/thanks/ link,
            // we should not rewrite it.
            container.innerHTML =
                '<a class="c-button-download-thanks-link" href="https://example.com/other">Should not rewrite</a>' +
                '<div class="c-button-download-thanks">' +
                '<a class="download-link" href="https://example.com/other2">Should not rewrite</a>' +
                '</div>';

            Mozilla.MobileAttribution.rewriteLinks(container, 'TARGET');

            const links = container.querySelectorAll('a');
            expect(links[0].getAttribute('href')).toBe(
                'https://example.com/other'
            );
            expect(links[1].getAttribute('href')).toBe(
                'https://example.com/other2'
            );
        });

        it('clicking a rewritten button fires sendEventFromURL and navigates to the original https store URL', function () {
            // Simulate the post-rewrite + post-mozilla-utils.js state: the
            // button HREF has been mutated to a market:// URL after our
            // rewrite ran (as would happen on real Android UAs). The click
            // handler must still pass the original https:// URL — not the
            // market:// URL — so TrackProductDownload's regex recognizes it,
            // and the navigation should target the original URL so desktop
            // browsers (with mobile UA spoofing) reach a real destination
            // instead of an unregistered market:// scheme.
            const ORIGINAL_STORE_URL =
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_campaign%3Dtest-19';
            const MUTATED_HREF =
                'market://details?id=org.mozilla.firefox&referrer=utm_campaign%3Dtest-19';

            container.innerHTML =
                '<a class="c-button-download-thanks-link" href="/thanks/">Download</a>';

            const sendEventSpy = spyOn(
                Mozilla.TrackProductDownload,
                'sendEventFromURL'
            );
            // Spy on the navigation seam so the test doesn't actually
            // navigate the jasmine runner away.
            const navigateSpy = spyOn(Mozilla.MobileAttribution, '_navigate');

            Mozilla.MobileAttribution.rewriteLinks(
                container,
                ORIGINAL_STORE_URL
            );

            // Simulate mozilla-utils.js mutating the href to market:// after
            // our rewrite (this is what happens in practice on Android UAs).
            const link = container.querySelector('a');
            link.setAttribute('href', MUTATED_HREF);

            const clickEvent = new MouseEvent('click', {
                bubbles: true,
                cancelable: true
            });
            const preventSpy = spyOn(
                clickEvent,
                'preventDefault'
            ).and.callThrough();
            link.dispatchEvent(clickEvent);

            expect(sendEventSpy).toHaveBeenCalledWith(ORIGINAL_STORE_URL);
            expect(navigateSpy).toHaveBeenCalledWith(ORIGINAL_STORE_URL);
            expect(preventSpy).toHaveBeenCalled();
        });

        it('does not throw if TrackProductDownload is undefined at init time', function () {
            window._OriginalTrackProductDownload =
                window.Mozilla.TrackProductDownload;
            delete window.Mozilla.TrackProductDownload;

            container.innerHTML =
                '<a class="c-button-download-thanks-link" href="/thanks/">Download</a>';

            expect(function () {
                Mozilla.MobileAttribution.rewriteLinks(container, 'TARGET');
            }).not.toThrow();

            // The HREF still gets rewritten even without the tracker — the
            // navigation works, only the click event is missed.
            expect(container.querySelector('a').getAttribute('href')).toBe(
                'TARGET'
            );
        });
    });

    describe('attachAndroidStoreButtonTracking', function () {
        afterEach(function () {
            // Restore the TrackProductDownload namespace if a test deleted it.
            if (
                window.Mozilla &&
                !window.Mozilla.TrackProductDownload &&
                window._OriginalTrackProductDownload
            ) {
                window.Mozilla.TrackProductDownload =
                    window._OriginalTrackProductDownload;
                delete window._OriginalTrackProductDownload;
            }
        });

        it('attaches a sendEventFromURL click handler to .fl-store-button-android elements', function () {
            const ORIGINAL_ANDROID_URL =
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_campaign%3Dpage-slug';

            container.innerHTML =
                '<a class="ga-product-download fl-store-button fl-store-button-android" href="' +
                ORIGINAL_ANDROID_URL +
                '">Play Store</a>';

            const sendEventSpy = spyOn(
                Mozilla.TrackProductDownload,
                'sendEventFromURL'
            );
            const navigateSpy = spyOn(Mozilla.MobileAttribution, '_navigate');

            Mozilla.MobileAttribution.attachAndroidStoreButtonTracking(
                container
            );

            const link = container.querySelector('a');
            link.dispatchEvent(
                new MouseEvent('click', { bubbles: true, cancelable: true })
            );

            expect(sendEventSpy).toHaveBeenCalledWith(ORIGINAL_ANDROID_URL);
            expect(navigateSpy).toHaveBeenCalledWith(ORIGINAL_ANDROID_URL);
        });

        it('captures the original https URL even if href is later mutated to market://', function () {
            // Simulate the real-world race: our handler is attached at
            // script load (sync). mozilla-utils.js mutates the href on
            // DOMContentLoaded. By click time, the href is market://...
            // but our captured URL is still the original https://.
            const ORIGINAL_ANDROID_URL =
                'https://play.google.com/store/apps/details?id=org.mozilla.firefox&referrer=utm_campaign%3Dpage-slug';
            const MUTATED_HREF =
                'market://details?id=org.mozilla.firefox&referrer=utm_campaign%3Dpage-slug';

            container.innerHTML =
                '<a class="ga-product-download fl-store-button fl-store-button-android" href="' +
                ORIGINAL_ANDROID_URL +
                '">Play Store</a>';

            const sendEventSpy = spyOn(
                Mozilla.TrackProductDownload,
                'sendEventFromURL'
            );
            spyOn(Mozilla.MobileAttribution, '_navigate');

            Mozilla.MobileAttribution.attachAndroidStoreButtonTracking(
                container
            );

            // Simulate mozilla-utils.js mutation after our attach.
            container.querySelector('a').setAttribute('href', MUTATED_HREF);

            container
                .querySelector('a')
                .dispatchEvent(
                    new MouseEvent('click', { bubbles: true, cancelable: true })
                );

            // Captured URL wins — not the mutated market:// URL.
            expect(sendEventSpy).toHaveBeenCalledWith(ORIGINAL_ANDROID_URL);
        });

        it('does NOT attach to .fl-store-button-ios elements (iOS already fires via existing handler)', function () {
            container.innerHTML =
                '<a class="ga-product-download fl-store-button fl-store-button-ios" href="https://apps.apple.com/...?ct=page-slug">App Store</a>';

            const sendEventSpy = spyOn(
                Mozilla.TrackProductDownload,
                'sendEventFromURL'
            );

            Mozilla.MobileAttribution.attachAndroidStoreButtonTracking(
                container
            );

            container
                .querySelector('a')
                .dispatchEvent(
                    new MouseEvent('click', { bubbles: true, cancelable: true })
                );

            expect(sendEventSpy).not.toHaveBeenCalled();
        });

        it('does not throw if TrackProductDownload is undefined', function () {
            window._OriginalTrackProductDownload =
                window.Mozilla.TrackProductDownload;
            delete window.Mozilla.TrackProductDownload;

            container.innerHTML =
                '<a class="fl-store-button-android" href="https://play.google.com/...">Play Store</a>';

            expect(function () {
                Mozilla.MobileAttribution.attachAndroidStoreButtonTracking(
                    container
                );
            }).not.toThrow();
        });
    });

    describe('init', function () {
        beforeEach(function () {
            spyOn(Mozilla.MobileAttribution, 'rewriteLinks');
            spyOn(
                Mozilla.MobileAttribution,
                'attachAndroidStoreButtonTracking'
            );
        });

        it('is a no-op when no campaign resolves and no Android UA', function () {
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                IOS_UA
            );

            Mozilla.MobileAttribution.init();

            expect(
                Mozilla.MobileAttribution.rewriteLinks
            ).not.toHaveBeenCalled();
            expect(
                Mozilla.MobileAttribution.attachAndroidStoreButtonTracking
            ).not.toHaveBeenCalled();
        });

        it('is a no-op on desktop UA even when a campaign is set', function () {
            html.setAttribute('data-stub-attribution-campaign', 'test-19');
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                DESKTOP_UA
            );

            Mozilla.MobileAttribution.init();

            expect(
                Mozilla.MobileAttribution.rewriteLinks
            ).not.toHaveBeenCalled();
            expect(
                Mozilla.MobileAttribution.attachAndroidStoreButtonTracking
            ).not.toHaveBeenCalled();
        });

        it('calls attachAndroidStoreButtonTracking on Android UA regardless of campaign', function () {
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                ANDROID_UA
            );

            Mozilla.MobileAttribution.init();

            expect(
                Mozilla.MobileAttribution.attachAndroidStoreButtonTracking
            ).toHaveBeenCalled();
        });

        it('does NOT call attachAndroidStoreButtonTracking on iOS UA', function () {
            html.setAttribute('data-stub-attribution-campaign', 'test-19');
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                IOS_UA
            );

            Mozilla.MobileAttribution.init();

            expect(
                Mozilla.MobileAttribution.attachAndroidStoreButtonTracking
            ).not.toHaveBeenCalled();
        });

        it('rewrites with the Android URL on Android UA', function () {
            html.setAttribute('data-stub-attribution-campaign', 'test-19');
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                ANDROID_UA
            );

            Mozilla.MobileAttribution.init();

            expect(Mozilla.MobileAttribution.rewriteLinks).toHaveBeenCalled();
            const callArgs =
                Mozilla.MobileAttribution.rewriteLinks.calls.mostRecent().args;
            expect(callArgs[0]).toBe(document);
            expect(callArgs[1].indexOf(ANDROID_STORE_PREFIX)).toBe(0);
            expect(callArgs[1]).toContain('utm_campaign%3Dtest-19');
        });

        it('rewrites with the iOS URL on iOS UA', function () {
            html.setAttribute('data-stub-attribution-campaign', 'test-19');
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                IOS_UA
            );

            Mozilla.MobileAttribution.init();

            expect(Mozilla.MobileAttribution.rewriteLinks).toHaveBeenCalled();
            const callArgs =
                Mozilla.MobileAttribution.rewriteLinks.calls.mostRecent().args;
            expect(callArgs[1].indexOf(IOS_STORE_PREFIX)).toBe(0);
            expect(callArgs[1]).toContain('ct=test-19');
        });
    });
});
