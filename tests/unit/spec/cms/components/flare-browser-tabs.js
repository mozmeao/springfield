/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupBrowserTabs from '../../../../../media/js/cms/components/flare-browser-tabs.es6';
import setupTabs from '../../../../../media/js/cms/components/flare-tabs.es6';

const UAS = {
    firefox:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0',
    chrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    edge: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
    opera: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
    safari: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    vivaldi:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Vivaldi/6.8.3381.48',
    duckduckgo:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 DuckDuckGo/7 Safari/605.1.15'
};

const BROWSERS = ['edge', 'chrome', 'safari', 'opera', 'brave'];

describe('flare-browser-tabs.es6.js', function () {
    let container;

    function buildTablist(browsers, id) {
        id = id || 'hub';
        const tabs = browsers
            .map(function (browser, i) {
                const index = i + 1;
                const attr = browser ? ' data-browser="' + browser + '"' : '';
                return (
                    '<button type="button" role="tab" id="fl-tab-' +
                    id +
                    '-' +
                    index +
                    '" aria-controls="fl-tab-panel-' +
                    id +
                    '-' +
                    index +
                    '"' +
                    attr +
                    '>' +
                    (browser || 'plain') +
                    '</button>'
                );
            })
            .join('');
        const panels = browsers
            .map(function (browser, i) {
                return (
                    '<div id="fl-tab-panel-' +
                    id +
                    '-' +
                    (i + 1) +
                    '" role="tabpanel"></div>'
                );
            })
            .join('');
        return (
            '<div class="fl-tabs-nav" role="tablist">' +
            tabs +
            '</div>' +
            panels
        );
    }

    function render(markup) {
        container = document.createElement('div');
        container.innerHTML = markup;
        document.body.appendChild(container);
    }

    function selected() {
        const tab = container.querySelector('[role=tab][aria-selected="true"]');
        return tab ? tab.getAttribute('data-browser') || tab.id : null;
    }

    function useAgent(ua) {
        spyOnProperty(navigator, 'userAgent', 'get').and.returnValue(ua);
    }

    afterEach(function () {
        if (container) {
            container.remove();
            container = null;
        }
        delete navigator.brave;
    });

    describe('matching the visitor to a tab', function () {
        it('should select the tab for the visitor’s own browser', function () {
            useAgent(UAS.safari);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('safari');
        });

        ['edge', 'chrome', 'safari', 'opera'].forEach(function (browser) {
            it(
                'should select the ' + browser + ' tab on ' + browser,
                function () {
                    useAgent(UAS[browser]);
                    render(buildTablist(BROWSERS));

                    setupBrowserTabs(setupTabs());

                    expect(selected()).toEqual(browser);
                }
            );
        });

        it('should select the Chrome tab for Firefox visitors', function () {
            useAgent(UAS.firefox);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('chrome');
        });

        it('should select the Chrome tab for a browser no tab claims', function () {
            useAgent(UAS.vivaldi);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('chrome');
        });

        it('should select the Chrome tab on a branded iOS browser, not the Safari tab', function () {
            // DuckDuckGo and its like carry Safari's token, so without the brand
            // check they land on the Safari tab - a browser the visitor is not
            // using - rather than following the documented Chrome fallback.
            useAgent(UAS.duckduckgo);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('chrome');
        });

        it('should leave the first tab selected when there is no Chrome tab to fall back to', function () {
            useAgent(UAS.firefox);
            render(buildTablist(['edge', 'safari']));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('edge');
        });

        it('should not touch a tablist whose tabs declare no browser', function () {
            // Tabs are used for plenty of things that have nothing to do with
            // browsers; those must keep their first-tab default.
            useAgent(UAS.safari);
            render(buildTablist([null, null, null]));

            setupBrowserTabs(setupTabs());

            expect(selected()).toEqual('fl-tab-hub-1');
        });

        it('should handle several tablists on one page independently', function () {
            useAgent(UAS.opera);
            render(
                buildTablist(BROWSERS, 'one') +
                    buildTablist([null, null], 'two')
            );

            setupBrowserTabs(setupTabs());

            const chosen = container.querySelectorAll(
                '[role=tab][aria-selected="true"]'
            );
            expect(chosen.length).toEqual(2);
            expect(chosen[0].getAttribute('data-browser')).toEqual('opera');
            expect(chosen[1].id).toEqual('fl-tab-two-1');
        });

        it('should show exactly one panel', function () {
            useAgent(UAS.safari);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            const visible = Array.from(
                container.querySelectorAll('[role=tabpanel]')
            ).filter(function (panel) {
                return !panel.classList.contains('is-hidden');
            });
            expect(visible.length).toEqual(1);
            expect(visible[0].id).toEqual('fl-tab-panel-hub-3');
        });

        it('should not move focus, since the visitor has not acted', function () {
            useAgent(UAS.safari);
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());

            expect(document.activeElement).not.toEqual(
                container.querySelector('[data-browser="safari"]')
            );
        });

        it('should do nothing when given no tab instances', function () {
            useAgent(UAS.safari);
            render(buildTablist(BROWSERS));

            expect(function () {
                setupBrowserTabs([]);
                setupBrowserTabs(undefined);
            }).not.toThrow();
            expect(selected()).toBeNull();
        });
    });

    describe('Brave, which is indistinguishable from Chrome by user agent', function () {
        it('should switch to the Brave tab once the API confirms it', async function () {
            useAgent(UAS.chrome);
            navigator.brave = { isBrave: () => Promise.resolve(true) };
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());
            // Selected synchronously first, so no page is left with every panel
            // showing while the promise settles.
            expect(selected()).toEqual('chrome');

            await Promise.resolve();
            await Promise.resolve();
            expect(selected()).toEqual('brave');
        });

        it('should stay on Chrome when the API denies Brave', async function () {
            useAgent(UAS.chrome);
            navigator.brave = { isBrave: () => Promise.resolve(false) };
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());
            await Promise.resolve();
            await Promise.resolve();

            expect(selected()).toEqual('chrome');
        });

        it('should not ask when there is no Brave tab', async function () {
            useAgent(UAS.chrome);
            const isBrave = jasmine
                .createSpy('isBrave')
                .and.returnValue(Promise.resolve(true));
            navigator.brave = { isBrave: isBrave };
            render(buildTablist(['chrome', 'safari']));

            setupBrowserTabs(setupTabs());
            await Promise.resolve();

            expect(isBrave).not.toHaveBeenCalled();
            expect(selected()).toEqual('chrome');
        });

        it('should not ask when the visitor is plainly not Chrome', async function () {
            useAgent(UAS.opera);
            const isBrave = jasmine
                .createSpy('isBrave')
                .and.returnValue(Promise.resolve(true));
            navigator.brave = { isBrave: isBrave };
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());
            await Promise.resolve();

            expect(isBrave).not.toHaveBeenCalled();
            expect(selected()).toEqual('opera');
        });

        it('should not move focus when it switches to Brave', async function () {
            useAgent(UAS.chrome);
            navigator.brave = { isBrave: () => Promise.resolve(true) };
            render(buildTablist(BROWSERS));

            setupBrowserTabs(setupTabs());
            await Promise.resolve();
            await Promise.resolve();

            expect(document.activeElement).not.toEqual(
                container.querySelector('[data-browser="brave"]')
            );
        });
    });

    describe('a Brave result that arrives late', function () {
        // The API is answered by hand here so the visitor can act in the window
        // while it is still pending - the situation the guard exists for.
        let resolveBrave;

        function setupWithPendingBrave() {
            useAgent(UAS.chrome);
            navigator.brave = {
                isBrave: () =>
                    new Promise(function (resolve) {
                        resolveBrave = resolve;
                    })
            };
            render(buildTablist(BROWSERS));
            setupBrowserTabs(setupTabs());
        }

        async function settle(result) {
            resolveBrave(result);
            await new Promise(function (resolve) {
                setTimeout(resolve, 0);
            });
        }

        function tab(browser) {
            return container.querySelector('[data-browser="' + browser + '"]');
        }

        afterEach(function () {
            resolveBrave = null;
        });

        it('should still apply when the visitor has done nothing', async function () {
            setupWithPendingBrave();
            expect(selected()).toEqual('chrome');

            await settle(true);

            expect(selected()).toEqual('brave');
        });

        it('should not overwrite a tab the visitor clicked while it was pending', async function () {
            setupWithPendingBrave();

            tab('safari').click();
            expect(selected()).toEqual('safari');

            await settle(true);

            expect(selected()).toEqual('safari');
        });

        it('should not overwrite a tab the visitor reached by arrow key', async function () {
            setupWithPendingBrave();
            tab('chrome').dispatchEvent(
                new KeyboardEvent('keydown', {
                    key: 'ArrowRight',
                    bubbles: true
                })
            );
            expect(selected()).toEqual('safari');

            await settle(true);

            expect(selected()).toEqual('safari');
        });

        it('should not overwrite a tab the visitor reached by Home or End', async function () {
            setupWithPendingBrave();

            tab('chrome').dispatchEvent(
                new KeyboardEvent('keydown', { key: 'End', bubbles: true })
            );
            expect(selected()).toEqual('brave');
            await settle(true);

            expect(selected()).toEqual('brave');
        });

        it('should stand down once the visitor tabs into the tablist', async function () {
            setupWithPendingBrave();
            tab('safari').focus();
            expect(selected()).toEqual('chrome');

            await settle(true);

            expect(selected()).toEqual('chrome');
        });

        it('should leave the visitor’s choice alone even when the API denies Brave', async function () {
            setupWithPendingBrave();

            tab('opera').click();
            await settle(false);

            expect(selected()).toEqual('opera');
        });

        it('should stop listening for interaction once it has settled', async function () {
            setupWithPendingBrave();
            await settle(true);
            expect(selected()).toEqual('brave');
            tab('edge').click();

            expect(selected()).toEqual('edge');
        });
    });
});
