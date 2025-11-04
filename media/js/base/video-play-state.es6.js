/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const VIDEO_STATE = 'data-js-video-state';

// adapted from https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/play#examples
async function toggleButton(button, isPlaying) {
    if (isPlaying) {
        button.setAttribute(VIDEO_STATE, 'playing');
    } else {
        button.setAttribute(VIDEO_STATE, 'paused');
    }
}

async function playVideo(video, button) {
    try {
        await video.play();
        toggleButton(button, true);
    } catch (err) {
        // make sure button reflects that video is still not playing
        toggleButton(button, false);
    }
}

function handleButtonClick(e) {
    const button = e.currentTarget;
    const video = button.nextElementSibling;

    if (video.paused) {
        playVideo(video, button);
    } else {
        video.pause();
        toggleButton(button, false);
    }
}

function init() {
    // play or pause video on button click
    const playStateButtons = document.querySelectorAll(
        `button[${VIDEO_STATE}]`
    );
    playStateButtons.forEach((button) => {
        // when no reduced motion pref, start playing
        if (window.Mozilla.Utils.allowsMotion()) {
            const video = button.nextElementSibling;
            playVideo(video, button);
        }
        button.addEventListener('click', (e) => handleButtonClick(e));
    });
}

init();
