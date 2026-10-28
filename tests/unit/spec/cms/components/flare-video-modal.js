/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { initVideoModals } from '../../../../../media/js/cms/components/flare-video-modal.es6';

describe('flare-video-modal.es6.js', function () {
    let container;

    function addVideoModal(videoId, title = 'Campaign video') {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <a href="https://www.youtube.com/watch?v=${videoId}" class="fl-video-modal-trigger">Watch</a>
            <div class="fl-video-modal-wrapper">
                <dialog class="fl-dialog fl-video-dialog" aria-label="${title}">
                    <button type="button" class="fl-dialog-close-button">Close</button>
                    <div class="fl-video-dialog-frame"></div>
                </dialog>
            </div>
        `;
        container.appendChild(wrapper);
        return wrapper;
    }

    function click(el, options = {}) {
        const event = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            ...options
        });
        el.dispatchEvent(event);
        return event;
    }

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
    });

    afterEach(function () {
        container.querySelectorAll('dialog[open]').forEach((dialog) => {
            dialog.close();
        });
        container.remove();
    });

    it('tells assistive tech the link opens a dialog', function () {
        const el = addVideoModal('abc123');
        initVideoModals();

        expect(
            el
                .querySelector('.fl-video-modal-trigger')
                .getAttribute('aria-haspopup')
        ).toBe('dialog');
    });

    it('opens the modal with an autoplaying nocookie player instead of following the link', function () {
        const el = addVideoModal('abc123');
        initVideoModals();

        const event = click(el.querySelector('.fl-video-modal-trigger'));

        expect(event.defaultPrevented).toBe(true);
        expect(el.querySelector('dialog').open).toBe(true);
        const iframe = el.querySelector('.fl-video-dialog-frame iframe');
        expect(iframe.src).toBe(
            'https://www.youtube-nocookie.com/embed/abc123?autoplay=1&rel=0'
        );
        expect(iframe.title).toBe('Campaign video');
        expect(iframe.allow).toContain('autoplay');
    });

    ['metaKey', 'ctrlKey', 'shiftKey', 'altKey'].forEach(function (modifier) {
        it(`leaves a ${modifier} click to the browser`, function () {
            const el = addVideoModal('abc123');
            initVideoModals();
            const trigger = el.querySelector('.fl-video-modal-trigger');
            // Keep the test page from navigating to YouTube.
            trigger.addEventListener('click', (event) =>
                event.preventDefault()
            );

            click(trigger, { [modifier]: true });

            expect(el.querySelector('dialog').open).toBe(false);
            expect(
                el.querySelector('.fl-video-dialog-frame iframe')
            ).toBeNull();
        });
    });

    it('closes from the close button and removes the player', async function () {
        const el = addVideoModal('abc123');
        initVideoModals();
        const dialog = el.querySelector('dialog');
        // The close event fires as its own task after close() returns.
        const closed = new Promise((resolve) =>
            dialog.addEventListener('close', resolve, { once: true })
        );

        click(el.querySelector('.fl-video-modal-trigger'));
        click(el.querySelector('.fl-dialog-close-button'));
        await closed;

        expect(dialog.open).toBe(false);
        expect(el.querySelector('.fl-video-dialog-frame iframe')).toBeNull();
    });

    it('adds a fresh player when reopened', function () {
        const el = addVideoModal('abc123');
        initVideoModals();
        const trigger = el.querySelector('.fl-video-modal-trigger');

        click(trigger);
        el.querySelector('dialog').close();
        click(trigger);

        expect(
            el.querySelectorAll('.fl-video-dialog-frame iframe').length
        ).toBe(1);
    });

    it('gives each of two duplicated buttons its own dialog, video and title', function () {
        const first = addVideoModal('first111', 'First video');
        const second = addVideoModal('second22', 'Second video');
        initVideoModals();

        click(second.querySelector('.fl-video-modal-trigger'));

        expect(first.querySelector('dialog').open).toBe(false);
        expect(second.querySelector('dialog').open).toBe(true);
        const iframe = second.querySelector('.fl-video-dialog-frame iframe');
        expect(iframe.src).toContain('/embed/second22?');
        expect(iframe.title).toBe('Second video');
    });
});
