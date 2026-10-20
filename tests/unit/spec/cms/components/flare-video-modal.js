/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { initVideoModals } from '../../../../../media/js/cms/components/flare-video-modal.es6';

describe('flare-video-modal.es6.js', function () {
    let container;

    function addVideoModal(videoId, dialogId) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <a href="https://www.youtube.com/watch?v=${videoId}"
               class="fl-dialog-trigger fl-video-modal-trigger"
               data-target-id="${dialogId}">Watch</a>
            <dialog id="${dialogId}" class="fl-dialog fl-video-dialog" aria-label="Campaign video">
                <button type="button" class="fl-dialog-close-button">Close</button>
                <div class="fl-video-dialog-frame"></div>
            </dialog>
        `;
        container.appendChild(wrapper);
        return wrapper;
    }

    function click(el) {
        const event = new MouseEvent('click', {
            bubbles: true,
            cancelable: true
        });
        el.dispatchEvent(event);
        return event;
    }

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
    });

    afterEach(function () {
        container.remove();
    });

    it('tells assistive tech the link opens a dialog', function () {
        const el = addVideoModal('abc123', 'video-modal-1');
        initVideoModals();

        expect(
            el
                .querySelector('.fl-video-modal-trigger')
                .getAttribute('aria-haspopup')
        ).toBe('dialog');
    });

    it('adds an autoplaying nocookie player on click instead of following the link', function () {
        const el = addVideoModal('abc123', 'video-modal-1');
        initVideoModals();

        const event = click(el.querySelector('.fl-video-modal-trigger'));

        expect(event.defaultPrevented).toBe(true);
        const iframe = el.querySelector('.fl-video-dialog-frame iframe');
        expect(iframe.src).toBe(
            'https://www.youtube-nocookie.com/embed/abc123?autoplay=1&rel=0'
        );
        expect(iframe.title).toBe('Campaign video');
        expect(iframe.allow).toContain('autoplay');
    });

    it('removes the player on close and adds a fresh one on reopen', function () {
        const el = addVideoModal('abc123', 'video-modal-1');
        initVideoModals();
        const trigger = el.querySelector('.fl-video-modal-trigger');
        const frame = el.querySelector('.fl-video-dialog-frame');

        click(trigger);
        el.querySelector('dialog').dispatchEvent(new Event('close'));
        expect(frame.querySelector('iframe')).toBeNull();

        click(trigger);
        expect(frame.querySelectorAll('iframe').length).toBe(1);
    });

    it('plays the clicked trigger’s video when two dialogs share an id', function () {
        const first = addVideoModal('first111', 'video-modal-dup');
        const second = addVideoModal('second22', 'video-modal-dup');
        initVideoModals();

        click(second.querySelector('.fl-video-modal-trigger'));

        // getElementById resolves to the first dialog for both triggers.
        const iframe = first.querySelector('.fl-video-dialog-frame iframe');
        expect(iframe.src).toContain('/embed/second22?');
    });
});
