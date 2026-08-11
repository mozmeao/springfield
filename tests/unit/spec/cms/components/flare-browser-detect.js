/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    detectBrowser,
    isBrave
} from '../../../../../media/js/cms/components/flare-browser-detect.es6';

describe('flare-browser-detect.es6.js', function () {
    describe('detectBrowser', function () {
        const UAS = {
            firefox:
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0',
            'firefox-windows':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
            'firefox-android':
                'Mozilla/5.0 (Android 14; Mobile; rv:140.0) Gecko/140.0 Firefox/140.0',
            'firefox-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/127.0 Mobile/15E148 Safari/605.1.15',
            chrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'chrome-macos':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'chrome-android':
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
            'chrome-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/126.0.0.0 Mobile/15E148 Safari/604.1',
            edge: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
            'edge-android':
                'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36 EdgA/126.0.0.0',
            'edge-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/126.0.0.0 Mobile/15E148 Safari/605.1.15',
            'edge-legacy':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/18.17763',
            opera: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
            'opera-android':
                'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36 OPR/82.0.0.0',
            'opera-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) OPT/5.0.0 Mobile/15E148 Safari/605.1.15',
            safari: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
            'safari-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
            vivaldi:
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Vivaldi/6.8.3381.48',
            samsung:
                'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/121.0.0.0 Mobile Safari/537.36',
            yandex: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 YaBrowser/24.6.0.0 Safari/537.36',
            // Branded WebKit wrappers. Every one of these keeps Safari's token
            // and appends its own, so they reach the Safari check unless caught.
            'duckduckgo-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 DuckDuckGo/7 Safari/605.1.15',
            'duckduckgo-android':
                'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.0.0 DuckDuckGo/5 Mobile Safari/537.36',
            'firefox-focus-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Focus/126.0 Mobile/15E148 Safari/605.1.15',
            'firefox-klar-ios':
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Klar/126.0 Mobile/15E148 Safari/605.1.15',
            puffin: 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36 Puffin/9.10.0',
            seamonkey:
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0 SeaMonkey/2.53.18',
            curl: 'curl/8.4.0'
        };

        const EXPECTED = {
            firefox: 'firefox',
            'firefox-windows': 'firefox',
            'firefox-android': 'firefox',
            'firefox-ios': 'firefox',
            chrome: 'chrome',
            'chrome-macos': 'chrome',
            'chrome-android': 'chrome',
            'chrome-ios': 'chrome',
            edge: 'edge',
            'edge-android': 'edge',
            'edge-ios': 'edge',
            'edge-legacy': 'edge',
            opera: 'opera',
            'opera-android': 'opera',
            'opera-ios': 'opera',
            safari: 'safari',
            'safari-ios': 'safari',
            // Chromium forks with no comparison tab of their own must fall back
            // rather than be mistaken for Chrome.
            vivaldi: 'other',
            samsung: 'other',
            yandex: 'other',
            // Branded wrappers around WebKit or Chromium. Reporting these as
            // safari/chrome would send the visitor to a tab for a browser they
            // are not using, instead of the documented Chrome fallback.
            'duckduckgo-ios': 'other',
            'duckduckgo-android': 'other',
            'firefox-focus-ios': 'other',
            'firefox-klar-ios': 'other',
            puffin: 'other',
            // non-Chromium others
            seamonkey: 'other',
            curl: 'other'
        };

        Object.keys(EXPECTED).forEach(function (key) {
            it('should detect ' + key + ' as ' + EXPECTED[key], function () {
                expect(detectBrowser(UAS[key])).toEqual(EXPECTED[key]);
            });
        });

        it('should fall back to navigator.userAgent when given no argument', function () {
            spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(
                UAS.safari
            );
            expect(detectBrowser()).toEqual('safari');
        });

        it('should report an unrecognised WebKit wrapper as safari, a known limitation', function () {
            const unknownWrapper =
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 NewPrivacyBrowser/2 Safari/605.1.15';
            expect(detectBrowser(unknownWrapper)).toEqual('safari');
        });

        it('should report Brave as chrome, since it copies Chrome exactly', function () {
            expect(detectBrowser(UAS.chrome)).toEqual('chrome');
        });
    });

    describe('isBrave', function () {
        afterEach(function () {
            delete navigator.brave;
        });

        it('should resolve false when the API is absent', async function () {
            await expectAsync(isBrave()).toBeResolvedTo(false);
        });

        it('should resolve false when brave exists but isBrave is not callable', async function () {
            navigator.brave = {};
            await expectAsync(isBrave()).toBeResolvedTo(false);
        });

        it('should resolve true when the API confirms Brave', async function () {
            navigator.brave = {
                isBrave: () => Promise.resolve(true)
            };
            await expectAsync(isBrave()).toBeResolvedTo(true);
        });

        it('should resolve false when the API denies Brave', async function () {
            navigator.brave = {
                isBrave: () => Promise.resolve(false)
            };
            await expectAsync(isBrave()).toBeResolvedTo(false);
        });

        it('should resolve false when the API rejects', async function () {
            navigator.brave = {
                isBrave: () => Promise.reject(new Error('nope'))
            };
            await expectAsync(isBrave()).toBeResolvedTo(false);
        });

        it('should resolve false when the API throws synchronously', async function () {
            navigator.brave = {
                isBrave: () => {
                    throw new Error('nope');
                }
            };
            await expectAsync(isBrave()).toBeResolvedTo(false);
        });
    });
});
