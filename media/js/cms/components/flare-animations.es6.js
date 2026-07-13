/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

function isAlphaWebmUnsupported() {
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) return true;
    // iPadOS 13+ may use a desktop-class UA (contains "Macintosh") to request desktop sites.
    // Use touch points to distinguish it from real macOS Safari.
    if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return true;
    return /^((?!chrome|android|crios|fxios).)*safari/i.test(ua);
}

function isAlphaWebm(src) {
    return /-alpha\.webm(\?|$)/i.test(src);
}

function swapAlphaWebmForPoster() {
    if (!isAlphaWebmUnsupported()) return;

    document.querySelectorAll('.fl-video').forEach(function (container) {
        const video = container.querySelector('video');
        if (!video) return;

        const source = video.querySelector('source');
        if (!source || !isAlphaWebm(source.getAttribute('src') || source.src))
            return;

        const poster = video.getAttribute('poster');
        if (!poster) return;

        const fallbackImg = video.querySelector('img');
        const img = document.createElement('img');
        img.src = poster;
        img.alt = fallbackImg ? fallbackImg.alt : '';
        img.className = 'fl-video-poster';
        video.replaceWith(img);

        container.querySelectorAll('.fl-video-play').forEach(function (btn) {
            btn.remove();
        });
        container.classList.remove('fl-animation-playing');
    });
}

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
        // Buttons inside the sliding carousel are handled by flare.es6.js
        if (button.closest('[data-js="fl-sliding-carousel"]')) return;

        const container = button.closest('.fl-video');
        if (!container) return;

        const video = container.querySelector('video');
        if (!video) return;

        const pauseIcon = button.querySelector('.js-pause-icon');
        const playIcon = button.querySelector('.js-play-icon');

        button.addEventListener('click', function () {
            if (video.paused) {
                video.play().catch((error) => {
                    if (error && error.name === 'AbortError') return;
                    throw error;
                });
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
    swapAlphaWebmForPoster();
    initAnimations();
    initAnimationPauseButtons();
}
