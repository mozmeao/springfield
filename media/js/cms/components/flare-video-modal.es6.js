/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Each trigger opens the dialog rendered right after it, so a duplicated
// button keeps its own video and title.

function getVideoId(triggerEl) {
    try {
        return new URL(triggerEl.href).searchParams.get('v');
    } catch (e) {
        return null;
    }
}

// Cmd, Ctrl, Shift, Alt or a non-primary button keep the link's own
// behaviour, such as opening the video on YouTube in a new tab.
function isModifiedClick(event) {
    return (
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
    );
}

export function initVideoModals() {
    const triggerEls = document.querySelectorAll('.fl-video-modal-trigger');

    triggerEls.forEach(function (triggerEl) {
        const wrapperEl = triggerEl.nextElementSibling;
        const dialogEl =
            wrapperEl && wrapperEl.querySelector('.fl-video-dialog');
        const frameEl =
            dialogEl && dialogEl.querySelector('.fl-video-dialog-frame');
        const videoId = getVideoId(triggerEl);

        if (!frameEl || !videoId) {
            return;
        }

        // Only now does the link open a dialog; without the JS it goes to YouTube.
        triggerEl.setAttribute('aria-haspopup', 'dialog');

        triggerEl.addEventListener('click', function (event) {
            if (isModifiedClick(event)) {
                return;
            }
            event.preventDefault();

            const iframe = document.createElement('iframe');
            iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0`;
            iframe.title = dialogEl.getAttribute('aria-label') || 'Video';
            iframe.allow =
                'autoplay; encrypted-media; picture-in-picture; fullscreen';
            iframe.allowFullscreen = true;
            frameEl.replaceChildren(iframe);
            dialogEl.showModal();
        });

        const closeButtonEl = dialogEl.querySelector('.fl-dialog-close-button');
        if (closeButtonEl) {
            closeButtonEl.addEventListener('click', function () {
                dialogEl.close();
            });
        }

        // Removing the iframe is what stops playback on close.
        dialogEl.addEventListener('close', function () {
            frameEl.replaceChildren();
        });
    });
}

export default function setupVideoModals() {
    initVideoModals();
}
