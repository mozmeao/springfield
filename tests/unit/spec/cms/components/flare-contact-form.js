/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupContactFormBlocks, {
    browserNav
} from '../../../../../media/js/cms/components/flare-contact-form.es6';

describe('flare-contact-form-block.es6.js', function () {
    let container;
    let originalFetch;
    // Every test form targets this hidden iframe, so a real (un-prevented) native
    // submit — the exact case the "before the delay" test needs to exercise —
    // navigates the iframe instead of away from the test runner page.
    let sink;

    function flush() {
        return new Promise((resolve) => setTimeout(resolve, 0));
    }

    function addWrapper(action, formHtml) {
        container.innerHTML = `
      <div class="fl-contact-form-wrapper">
        <form method="post" action="/page-not-found/" data-actn="${action}" class="fl-form-page contact-form" target="${sink.name}">
          ${formHtml || '<button type="submit">Submit</button>'}
        </form>
      </div>
    `;
        return container.querySelector('.fl-contact-form-wrapper');
    }

    function submitForm(wrapper) {
        const form = wrapper.querySelector('form');
        const event = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(event);
        return event;
    }

    // The submit listener is delegated on `document` and meant to be attached once for
    // the page's lifetime, so it's set up once here rather than per test.
    beforeAll(function () {
        sink = document.createElement('iframe');
        sink.name = 'contact-form-test-sink';
        sink.style.display = 'none';
        document.body.appendChild(sink);
        setupContactFormBlocks();
    });

    afterAll(function () {
        sink.remove();
    });

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
        originalFetch = window.fetch;
    });

    afterEach(function () {
        container.remove();
        window.fetch = originalFetch;
    });

    it('ignores submits fired before the anti-bot delay elapses', function () {
        // Force "now" well before the module's readyAt cutoff, rather than relying on
        // this test running within 3s of module import. Spying on Date.now (rather than
        // jasmine's fake clock) leaves the real setTimeout alone, which flush() relies on.
        spyOn(Date, 'now').and.returnValue(0);

        const wrapper = addWrapper('/contact/');
        window.fetch = jasmine.createSpy('fetch');

        const event = submitForm(wrapper);

        expect(event.defaultPrevented).toBe(false);
        expect(window.fetch).not.toHaveBeenCalled();
    });

    describe('once the anti-bot delay has elapsed', function () {
        beforeEach(function () {
            const now = Date.now();
            spyOn(Date, 'now').and.returnValue(now + 10000);
        });

        it('swaps in the response wrapper on an HTML response', async function () {
            const wrapper = addWrapper('/contact/');
            window.fetch = jasmine.createSpy('fetch').and.returnValue(
                Promise.resolve({
                    redirected: false,
                    headers: { get: () => 'text/html; charset=utf-8' },
                    text: () =>
                        Promise.resolve(
                            '<div class="fl-contact-form-wrapper"><p>Thanks!</p></div>'
                        )
                })
            );

            const event = submitForm(wrapper);
            await flush();
            await flush();

            expect(event.defaultPrevented).toBe(true);
            expect(window.fetch).toHaveBeenCalledWith(
                '/contact/',
                jasmine.objectContaining({ method: 'POST' })
            );
            expect(wrapper.innerHTML).toContain('Thanks!');
        });

        it('navigates the browser when the response was redirected', async function () {
            const wrapper = addWrapper('/contact/');
            window.fetch = jasmine.createSpy('fetch').and.returnValue(
                Promise.resolve({
                    redirected: true,
                    url: '/thank-you/'
                })
            );
            spyOn(browserNav, 'redirectTo');

            submitForm(wrapper);
            await flush();

            expect(browserNav.redirectTo).toHaveBeenCalledWith('/thank-you/');
        });

        it('falls back to a real submit when the response is unusable', async function () {
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(form, 'submit');
            window.fetch = jasmine
                .createSpy('fetch')
                .and.returnValue(Promise.reject(new Error('network down')));

            submitForm(wrapper);
            await flush();
            await flush();

            expect(form.action).toContain('/contact/');
            expect(form.submit).toHaveBeenCalled();
        });

        it('clicks the download link once it appears after a swap', async function () {
            const wrapper = addWrapper('/contact/');
            window.fetch = jasmine.createSpy('fetch').and.returnValue(
                Promise.resolve({
                    redirected: false,
                    headers: { get: () => 'text/html' },
                    text: () =>
                        Promise.resolve(
                            '<div class="fl-contact-form-wrapper"><a class="contact-form-download" href="/file.pdf" download>Download</a></div>'
                        )
                })
            );
            // Spy on the prototype, not the (not-yet-existing) swapped-in link, and avoid
            // a real navigation/download attempt in the test browser.
            spyOn(HTMLAnchorElement.prototype, 'click');

            submitForm(wrapper);
            await flush();
            await flush();

            const link = wrapper.querySelector('.contact-form-download');
            expect(link.click).toHaveBeenCalled();
            expect(link.classList.contains('hidden')).toBe(true);
        });
    });
});
