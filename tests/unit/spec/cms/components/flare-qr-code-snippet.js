/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupQRCodeSnippet from '../../../../../media/js/cms/components/flare-qr-code-snippet.es6';

describe('flare-qr-code-snippet.es6.js — reduced motion', function () {
    let container;

    function stubReducedMotion(matches) {
        spyOn(window, 'matchMedia').and.callFake((query) => ({
            matches: query === '(prefers-reduced-motion)' ? matches : false,
            media: query
        }));
    }

    function addFloatingSnippet() {
        const el = document.createElement('aside');
        el.className =
            'js-qr-code-floating-snippet fl-qr-code-snippet-closable is-open';
        el.innerHTML = `
            <div class="fl-qr-code-floating-header">
                <button class="fl-qr-code-snippet-close" aria-expanded="true">
                    <span class="fl-icon fl-icon-subtract" aria-hidden="true"></span>
                </button>
            </div>
        `;
        container.appendChild(el);
        return el;
    }

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
        spyOn(window.Mozilla.Cookies, 'enabled').and.returnValue(false);
    });

    afterEach(function () {
        container.remove();
    });

    it('reveals the snippet on init even when reduced motion is active', function () {
        stubReducedMotion(true);
        const el = addFloatingSnippet();

        setupQRCodeSnippet();

        expect(el.style.visibility).toBe('visible');
    });

    it('hides the snippet via visibility once dismissed while reduced motion is active', function () {
        stubReducedMotion(true);
        const el = addFloatingSnippet();

        setupQRCodeSnippet();
        expect(el.classList.contains('is-open')).toBe(true);

        el.querySelector('.fl-qr-code-snippet-close').click(); // dismiss
        expect(el.classList.contains('is-open')).toBe(false);
        expect(el.style.visibility).toBe('hidden');
    });

    it('leaves the snippet visible (just closed) after dismissal when reduced motion is not active', function () {
        stubReducedMotion(false);
        const el = addFloatingSnippet();

        setupQRCodeSnippet();
        el.querySelector('.fl-qr-code-snippet-close').click(); // dismiss

        expect(el.classList.contains('is-open')).toBe(false);
        expect(el.style.visibility).toBe('visible');
    });
});
