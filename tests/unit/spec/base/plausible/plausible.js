/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

import Plausible from '../../../../../media/js/base/plausible/plausible.es6';

describe('plausible.es6.js', function () {
    const html = document.getElementsByTagName('html')[0];

    beforeEach(function () {
        window.Mozilla.gpcEnabled = sinon.stub().returns(false);
        window.Mozilla.dntEnabled = sinon.stub().returns(false);
    });

    afterEach(function () {
        html.removeAttribute('data-plausible-domain');
        html.removeAttribute('data-plausible-src');
        delete window.Mozilla.gpcEnabled;
        delete window.Mozilla.dntEnabled;
        delete window.plausible;
    });

    describe('init', function () {
        beforeEach(function () {
            spyOn(Plausible, 'loadScript');
            spyOn(Plausible, 'defineQueueStub');
        });

        it('should define the queue stub but not load the script if DNT is enabled', function () {
            window.Mozilla.dntEnabled = sinon.stub().returns(true);

            Plausible.init();
            expect(Plausible.defineQueueStub).toHaveBeenCalled();
            expect(Plausible.loadScript).not.toHaveBeenCalled();
        });

        it('should define the queue stub but not load the script if GPC is enabled', function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);

            Plausible.init();
            expect(Plausible.defineQueueStub).toHaveBeenCalled();
            expect(Plausible.loadScript).not.toHaveBeenCalled();
        });

        it('should define the queue stub and load the script when consent signals allow', function () {
            Plausible.init();
            expect(Plausible.defineQueueStub).toHaveBeenCalled();
            expect(Plausible.loadScript).toHaveBeenCalled();
        });

        it('should define the queue stub but not load the script if analytics consent was explicitly declined', function () {
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({ analytics: false })
            );

            Plausible.init();
            expect(Plausible.defineQueueStub).toHaveBeenCalled();
            expect(Plausible.loadScript).not.toHaveBeenCalled();
        });

        it('should load the script when analytics consent was granted', function () {
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({ analytics: true })
            );

            Plausible.init();
            expect(Plausible.loadScript).toHaveBeenCalled();
        });
    });

    describe('analyticsDenied', function () {
        it('should return true when GPC is enabled', function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);
            expect(Plausible.analyticsDenied()).toBe(true);
        });

        it('should return true when DNT is enabled', function () {
            window.Mozilla.dntEnabled = sinon.stub().returns(true);
            expect(Plausible.analyticsDenied()).toBe(true);
        });

        it('should return true when the consent cookie explicitly declines analytics', function () {
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({ analytics: false })
            );
            expect(Plausible.analyticsDenied()).toBe(true);
        });

        it('should return false when the consent cookie grants analytics', function () {
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({ analytics: true })
            );
            expect(Plausible.analyticsDenied()).toBe(false);
        });

        it('should return false when no consent cookie is set (cookieless default)', function () {
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(null);
            expect(Plausible.analyticsDenied()).toBe(false);
        });
    });

    describe('loadScript', function () {
        let appendChildSpy;

        beforeEach(function () {
            appendChildSpy = spyOn(document.head, 'appendChild');
        });

        it('should not inject a script when data attributes are missing', function () {
            Plausible.loadScript();
            expect(appendChildSpy).not.toHaveBeenCalled();
        });

        it('should inject a deferred script with the configured domain and src', function () {
            html.setAttribute('data-plausible-domain', 'firefox.com');
            html.setAttribute(
                'data-plausible-src',
                'https://plausible.example/js/script.js'
            );

            Plausible.loadScript();

            expect(appendChildSpy).toHaveBeenCalled();
            const script = appendChildSpy.calls.mostRecent().args[0];
            expect(script.tagName).toBe('SCRIPT');
            expect(script.defer).toBe(true);
            expect(script.getAttribute('data-domain')).toBe('firefox.com');
            expect(script.src).toBe('https://plausible.example/js/script.js');
        });
    });

    describe('trackEvent', function () {
        it('should not call window.plausible when the queue is undefined', function () {
            delete window.plausible;
            // Should not throw.
            Plausible.trackEvent('product_download');
            expect(window.plausible).toBeUndefined();
        });

        it('should not send an event when GPC is enabled', function () {
            window.plausible = sinon.stub();
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);

            Plausible.trackEvent('product_download');
            expect(window.plausible.called).toBe(false);
        });

        it('should not send an event when DNT is enabled', function () {
            window.plausible = sinon.stub();
            window.Mozilla.dntEnabled = sinon.stub().returns(true);

            Plausible.trackEvent('product_download');
            expect(window.plausible.called).toBe(false);
        });

        it('should not send an event when analytics consent was explicitly declined', function () {
            window.plausible = sinon.stub();
            spyOn(window.Mozilla.Cookies, 'getItem').and.returnValue(
                JSON.stringify({ analytics: false })
            );

            Plausible.trackEvent('product_download');
            expect(window.plausible.called).toBe(false);
        });

        it('should send the event name with no props', function () {
            window.plausible = sinon.stub();

            Plausible.trackEvent('product_download');
            expect(window.plausible.calledOnce).toBe(true);
            expect(window.plausible.calledWith('product_download')).toBe(true);
        });

        it('should send the event name with props when provided', function () {
            window.plausible = sinon.stub();
            const props = { product: 'firefox', platform: 'win' };

            Plausible.trackEvent('product_download', props);
            expect(window.plausible.calledOnce).toBe(true);
            expect(
                window.plausible.calledWith('product_download', {
                    props: props
                })
            ).toBe(true);
        });
    });

    describe('defineQueueStub', function () {
        it('should create a window.plausible queue function', function () {
            Plausible.defineQueueStub();
            expect(typeof window.plausible).toBe('function');

            window.plausible('pageview');
            expect(window.plausible.q.length).toBe(1);
        });

        it('should not overwrite an existing window.plausible', function () {
            const existing = sinon.stub();
            window.plausible = existing;

            Plausible.defineQueueStub();
            expect(window.plausible).toBe(existing);
        });
    });
});
