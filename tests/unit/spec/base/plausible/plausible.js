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

        it('should not load the script if DNT is enabled', function () {
            window.Mozilla.dntEnabled = sinon.stub().returns(true);

            Plausible.init();
            expect(Plausible.defineQueueStub).not.toHaveBeenCalled();
            expect(Plausible.loadScript).not.toHaveBeenCalled();
        });

        it('should not load the script if GPC is enabled', function () {
            window.Mozilla.gpcEnabled = sinon.stub().returns(true);

            Plausible.init();
            expect(Plausible.defineQueueStub).not.toHaveBeenCalled();
            expect(Plausible.loadScript).not.toHaveBeenCalled();
        });

        it('should define the queue stub and load the script when consent signals allow', function () {
            Plausible.init();
            expect(Plausible.defineQueueStub).toHaveBeenCalled();
            expect(Plausible.loadScript).toHaveBeenCalled();
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
