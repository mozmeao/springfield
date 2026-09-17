/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupContactForms from '../../../../../media/js/cms/components/flare-contact-form.es6';

// The request/swap itself is htmx's job (see contact-form.html) and isn't retested here.
// This covers what this module bolts on via htmx's events: the anti-bot delay, the error fallback, and the download re-click.
describe('flare-contact-form.es6.js', function () {
    let container;

    beforeAll(function () {
        setupContactForms();
    });

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
    });

    afterEach(function () {
        container.remove();
    });

    function addWrapper(action, innerHtml) {
        container.innerHTML = `
      <div class="fl-contact-form-wrapper">
        <form method="post" action="/page-not-found/" hx-post="${action}" class="fl-form contact-form">
          ${innerHtml || '<button type="submit">Submit</button>'}
        </form>
      </div>
    `;
        return container.querySelector('.fl-contact-form-wrapper');
    }

    describe('anti-bot delay', function () {
        it('sends an early submit to the decoy action instead of htmx', function () {
            spyOn(Date, 'now').and.returnValue(0);
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(form, 'submit');

            const event = new Event('htmx:confirm', {
                bubbles: true,
                cancelable: true
            });
            form.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(true);
            expect(form.submit).toHaveBeenCalled();
            expect(form.action).toContain('/page-not-found/');
        });

        it('leaves htmx:confirm and the form alone once the delay has elapsed', function () {
            spyOn(Date, 'now').and.returnValue(Date.now() + 10000);
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(form, 'submit');

            const event = new Event('htmx:confirm', {
                bubbles: true,
                cancelable: true
            });
            form.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
            expect(form.submit).not.toHaveBeenCalled();
        });
    });

    describe('error fallback', function () {
        ['htmx:sendError', 'htmx:responseError'].forEach((eventName) => {
            it(`falls back to a real submit on ${eventName}`, function () {
                const wrapper = addWrapper('/contact/');
                const form = wrapper.querySelector('form');
                spyOn(form, 'submit');

                form.dispatchEvent(new Event(eventName, { bubbles: true }));

                expect(form.action).toContain('/contact/');
                expect(form.submit).toHaveBeenCalled();
            });
        });
    });

    describe('after a swap', function () {
        it('clicks the download link the new wrapper carries', function () {
            const wrapper = addWrapper(
                '/contact/',
                '<a class="contact-form-download" href="/file.pdf" download>Download</a>'
            );
            // Spy on the prototype to avoid a real navigation/download in the test browser.
            spyOn(HTMLAnchorElement.prototype, 'click');

            wrapper.dispatchEvent(
                new Event('htmx:afterSwap', { bubbles: true })
            );

            const link = wrapper.querySelector('.contact-form-download');
            expect(link.click).toHaveBeenCalled();
            expect(link.classList.contains('hidden')).toBe(true);
        });
    });
});
