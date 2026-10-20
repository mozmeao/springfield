/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// flare-dialogs.es6.js opens and closes the dialog; this adds the player.
// The video ID is read from the trigger, not the dialog, so a trigger whose
// dialog id is duplicated on the page still plays its own video.

function getVideoId(triggerEl) {
    try {
        return new URL(triggerEl.href).searchParams.get('v');
    } catch (e) {
        return null;
    }
}

export function initVideoModals() {
    const triggerEls = document.querySelectorAll('.fl-video-modal-trigger');

    triggerEls.forEach(function (triggerEl) {
        const dialogEl = document.getElementById(triggerEl.dataset.targetId);
        const frameEl =
            dialogEl && dialogEl.querySelector('.fl-video-dialog-frame');
        const videoId = getVideoId(triggerEl);

        if (!frameEl || !videoId) {
            return;
        }

        // Only now does the link open a dialog; without the JS it goes to YouTube.
        triggerEl.setAttribute('aria-haspopup', 'dialog');

        triggerEl.addEventListener('click', function (event) {
            event.preventDefault();

            const iframe = document.createElement('iframe');
            iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(videoId)}?autoplay=1&rel=0`;
            iframe.title = dialogEl.getAttribute('aria-label') || 'Video';
            iframe.allow =
                'autoplay; encrypted-media; picture-in-picture; fullscreen';
            iframe.allowFullscreen = true;
            frameEl.replaceChildren(iframe);
        });

        // Removing the iframe is what stops playback on close.
        dialogEl.addEventListener('close', function () {
            frameEl.replaceChildren();
        });
    });
}

export default function setupVideoModals() {
    initVideoModals();
}
