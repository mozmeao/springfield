/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupContactForms from '../../../../../media/js/cms/components/flare-contact-form.es6';

// The request/swap itself is htmx's job (see contact-form.html) and isn't retested here.
// This covers what this module bolts on via htmx's events: the anti-bot delay, the error handling,
// and the download re-click and focus after a swap.
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
          <div class="contact-form-request-error hidden" role="alert">Error sending</div>
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
            spyOn(HTMLFormElement.prototype, 'submit');

            const event = new Event('htmx:confirm', {
                bubbles: true,
                cancelable: true
            });
            form.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(true);
            expect(HTMLFormElement.prototype.submit).toHaveBeenCalled();
            expect(form.action).toContain('/page-not-found/');
        });

        it('leaves htmx:confirm and the form alone once the delay has elapsed', function () {
            // Read the clock before the spy replaces it, or the configured value is NaN.
            const afterTheDelay = Date.now() + 10000;
            spyOn(Date, 'now').and.returnValue(afterTheDelay);
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(HTMLFormElement.prototype, 'submit');

            const event = new Event('htmx:confirm', {
                bubbles: true,
                cancelable: true
            });
            form.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
            expect(HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
        });

        it('lets the block placeholder load its form straight away', function () {
            spyOn(Date, 'now').and.returnValue(0);
            container.innerHTML =
                '<div class="fl-contact-form-wrapper" hx-get="/contact/"></div>';
            const placeholder = container.querySelector(
                '.fl-contact-form-wrapper'
            );

            const event = new Event('htmx:confirm', {
                bubbles: true,
                cancelable: true
            });
            placeholder.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
        });

        it('submits natively even when a field is named "submit"', function () {
            spyOn(Date, 'now').and.returnValue(0);
            const wrapper = addWrapper(
                '/contact/',
                '<input name="submit"><button type="submit">Submit</button>'
            );
            const form = wrapper.querySelector('form');
            spyOn(HTMLFormElement.prototype, 'submit');

            form.dispatchEvent(
                new Event('htmx:confirm', { bubbles: true, cancelable: true })
            );

            expect(HTMLFormElement.prototype.submit).toHaveBeenCalled();
        });
    });

    describe('error handling', function () {
        it('falls back to a real submit when the request cannot be sent', function () {
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(HTMLFormElement.prototype, 'submit');

            form.dispatchEvent(new Event('htmx:sendError', { bubbles: true }));

            expect(form.action).toContain('/contact/');
            expect(HTMLFormElement.prototype.submit).toHaveBeenCalled();
        });

        it('shows an inline error instead of resubmitting when the server fails', function () {
            const wrapper = addWrapper('/contact/');
            const form = wrapper.querySelector('form');
            spyOn(HTMLFormElement.prototype, 'submit');

            form.dispatchEvent(
                new Event('htmx:responseError', { bubbles: true })
            );

            const error = form.querySelector('.contact-form-request-error');
            expect(error.classList.contains('hidden')).toBe(false);
            expect(document.activeElement).toBe(error);
            expect(HTMLFormElement.prototype.submit).not.toHaveBeenCalled();
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

        it('moves focus to the notification the new wrapper carries', function () {
            const wrapper = addWrapper(
                '/contact/',
                '<div role="status">Thanks!</div>'
            );

            wrapper.dispatchEvent(
                new Event('htmx:afterSwap', { bubbles: true })
            );

            expect(document.activeElement).toBe(
                wrapper.querySelector('[role="status"]')
            );
        });
    });
});
