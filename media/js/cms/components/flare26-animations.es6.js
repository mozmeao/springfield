/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function initAnimations() {
    const animations = document.querySelectorAll('.fl-animation');

    animations.forEach(function (container) {
        const video = container.querySelector('video');
        const button = container.querySelector('.js-animation-play');
        const playback = container.getAttribute('data-playback');

        if (!video || !button) return;

        if (
            playback === 'autoplay_once' &&
            !window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ) {
            video.play().catch(function () {
                container.classList.remove('fl-animation-playing');
            });
        } else if (playback === 'autoplay_once') {
            container.classList.remove('fl-animation-playing');
        }

        video.addEventListener('ended', function () {
            container.classList.remove('fl-animation-playing');
            video.currentTime = 0;
        });

        button.addEventListener('click', function () {
            container.classList.add('fl-animation-playing');
            video.currentTime = 0;
            video.play().catch(function () {
                container.classList.remove('fl-animation-playing');
            });
        });
    });
}

function initAnimationPauseButtons() {
    const pauseButtons = document.querySelectorAll('.js-animation-pause');

    pauseButtons.forEach(function (button) {
        // Buttons inside the sliding carousel are handled by flare26.es6.js
        if (button.closest('[data-js="fl-sliding-carousel"]')) return;

        const container = button.closest('.fl-video');
        if (!container) return;

        const video = container.querySelector('video');
        if (!video) return;

        const pauseIcon = button.querySelector('.js-pause-icon');
        const playIcon = button.querySelector('.js-play-icon');

        button.addEventListener('click', function () {
            if (video.paused) {
                video.play().catch();
                button.setAttribute('aria-label', button.dataset.labelPause);
                button.classList.remove('is-paused');
                pauseIcon.hidden = false;
                playIcon.hidden = true;
            } else {
                video.pause();
                button.setAttribute('aria-label', button.dataset.labelPlay);
                pauseIcon.hidden = true;
                playIcon.hidden = false;
                button.classList.add('is-paused');
            }
        });
    });
}

export default function setupAnimations() {
    initAnimations();
    initAnimationPauseButtons();
}
