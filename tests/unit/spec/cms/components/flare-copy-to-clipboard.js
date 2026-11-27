/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupCopyToClipboardButtons from '../../../../../media/js/cms/components/flare-copy-to-clipboard.es6';

describe('flare-copy-to-clipboard.es6.js', function () {
    let container;
    let button;
    let statusRegion;

    beforeEach(function () {
        jasmine.clock().install();
        spyOn(navigator.clipboard, 'writeText').and.returnValue(
            Promise.resolve()
        );

        container = document.createElement('div');
        container.innerHTML = `
            <button type="button" data-js="fl-copy-to-clipboard"
                data-copy-value="https://example.com" data-label-success="Copied!">
                <span class="fl-copy-to-clipboard-label">Copy link</span>
                <span class="fl-copy-to-clipboard-label-success hidden">Copied!</span>
                <span class="fl-copy-to-clipboard-icon-default"></span>
                <span class="fl-copy-to-clipboard-icon-success hidden"></span>
            </button>
            <span class="fl-copy-to-clipboard-status" role="status"></span>`;
        document.body.appendChild(container);
        button = container.querySelector('button');
        statusRegion = container.querySelector('[role="status"]');

        setupCopyToClipboardButtons();
    });

    afterEach(function () {
        jasmine.clock().uninstall();
        container.remove();
    });

    async function clickAndWaitForCopy() {
        button.click();
        await navigator.clipboard.writeText.calls.mostRecent().returnValue;
    }

    it('announces the success message in the live region outside the button', async function () {
        await clickAndWaitForCopy();

        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
            'https://example.com'
        );
        expect(statusRegion.textContent).toEqual('Copied!');
    });

    it('shows the success label and keeps the button enabled', async function () {
        await clickAndWaitForCopy();

        expect(
            button
                .querySelector('.fl-copy-to-clipboard-label')
                .classList.contains('hidden')
        ).toBeTrue();
        expect(
            button
                .querySelector('.fl-copy-to-clipboard-label-success')
                .classList.contains('hidden')
        ).toBeFalse();
        expect(button.classList.contains('is-copied')).toBeTrue();
        expect(button.disabled).toBeFalse();
    });

    it('restores the default label and clears the live region after the reset delay', async function () {
        await clickAndWaitForCopy();
        jasmine.clock().tick(2000);

        expect(
            button
                .querySelector('.fl-copy-to-clipboard-label')
                .classList.contains('hidden')
        ).toBeFalse();
        expect(button.classList.contains('is-copied')).toBeFalse();
        expect(statusRegion.textContent).toEqual('');
    });
});
