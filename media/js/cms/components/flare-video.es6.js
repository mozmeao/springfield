/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import VideoEngagement from '../../base/datalayer-videoengagement.es6';

function applyVideoAspectRatios() {
    const videoContainers = document.querySelectorAll(
        '.fl-video[data-aspect-ratio]'
    );

    videoContainers.forEach(function (container) {
        const ratio = container.getAttribute('data-aspect-ratio');

        if (!ratio) {
            return;
        }

        container.style.aspectRatio = ratio;
    });
}

function honorReducedMotionForAutoplay() {
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    document.querySelectorAll('video[autoplay]').forEach(function (video) {
        // Pause immediately — more reliable than removing the autoplay attribute,
        // which browsers may have already acted on before JS runs.
        video.pause();

        // Guard against the browser restarting playback (e.g. after seek).
        video.addEventListener(
            'play',
            function () {
                video.pause();
            },
            { once: true }
        );

        // Update the paired pause/play button if one exists.
        const container = video.closest('.fl-video');
        const pauseBtn =
            container && container.querySelector('.js-animation-pause');
        if (pauseBtn) {
            pauseBtn.classList.add('is-paused');
            pauseBtn.setAttribute(
                'aria-label',
                pauseBtn.dataset.labelPlay || ''
            );
            const pauseIcon = pauseBtn.querySelector('.js-pause-icon');
            const playIcon = pauseBtn.querySelector('.js-play-icon');
            if (pauseIcon) pauseIcon.hidden = true;
            if (playIcon) playIcon.hidden = false;
        }
    });
}

function initVideoPlayers() {
    const videoButtons = document.querySelectorAll('.js-video-play');

    videoButtons.forEach(function (button) {
        button.addEventListener('click', function (e) {
            e.preventDefault();

            const videoType = button.getAttribute('data-video-type');
            const container = button.closest('.fl-video');

            if (!container) return;

            if (videoType === 'youtube') {
                const videoId = button.getAttribute('data-video-id');

                if (!videoId) return;

                const iframe = document.createElement('iframe');
                iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`;
                iframe.title = button.getAttribute('aria-label') || 'Video';
                iframe.allowFullscreen = true;
                button.remove();
                container.appendChild(iframe);
            } else if (videoType === 'cdn') {
                const videoUrl = button.getAttribute('data-video-url');
                const posterUrl = button.getAttribute('data-video-poster');

                if (!videoUrl) return;

                const video = document.createElement('video');
                video.controls = true;

                if (
                    window.matchMedia('(prefers-reduced-motion: reduce)')
                        .matches
                ) {
                    video.autoplay = false;
                } else {
                    video.autoplay = true;
                }

                if (posterUrl) {
                    video.poster = posterUrl;
                }

                const source = document.createElement('source');
                source.src = videoUrl;
                source.type = 'video/webm';

                video.appendChild(source);

                button.remove();
                container.appendChild(video);

                video.addEventListener('play', VideoEngagement.handleStart, {
                    once: true
                });

                // Floor duration because we don't need precise numbers here
                video.addEventListener('loadedmetadata', (e) => {
                    VideoEngagement.duration = Math.floor(e.target.duration);
                });

                // 'timeupdate' will handle both video_progress and video_complete data
                // ('ended' not reliable: if 'loop' is true, it will not fire)
                video.addEventListener(
                    'timeupdate',
                    VideoEngagement.throttledProgress
                );
            }
        });
    });
}

export default function setupVideo() {
    applyVideoAspectRatios();
    honorReducedMotionForAutoplay();
    initVideoPlayers();
}
