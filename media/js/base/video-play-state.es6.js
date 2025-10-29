/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// IMPORTANT: use with 'video-prefers-reduced-motion' JS

const VIDEO_STATE = 'data-js-video-state';

async function togglePlayState(e) {
    const button = e.currentTarget;
    const video = button.nextElementSibling; // fragile
    if (video.paused) {
        try {
            await video.play();
            button.setAttribute(VIDEO_STATE, 'playing');
        } catch (err) {
            // call sentry?
        }
    } else {
        video.pause();
        button.setAttribute(VIDEO_STATE, 'paused');
    }
}

function init() {
    // play or pause video on button click
    const playStateButtons = document.querySelectorAll(
        `button[${VIDEO_STATE}]`
    );
    playStateButtons.forEach((button) => {
        // when reduced motion pref, initiate as paused
        // remove controls because the button is available
        if (!window.Mozilla.Utils.allowsMotion()) {
            button.setAttribute(VIDEO_STATE, 'paused');
            button.nextElementSibling.removeAttribute('controls'); // fragile selector
        }
        button.addEventListener('click', (e) => togglePlayState(e));
    });
}

init();
