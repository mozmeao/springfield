/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Swiper from 'swiper';
import { Pagination } from 'swiper/modules';

const AUTO_PLAY_INTERVAL_MS = 24000;

function initSlidingCarousel(rootEl) {
    const controlsSwiperEl = rootEl.querySelector(
        '.fl-sliding-carousel-controls-swiper'
    );
    const paginationEl = rootEl.querySelector(
        '.fl-sliding-carousel-pagination'
    );

    const controls = Array.from(
        rootEl.querySelectorAll('.fl-sliding-carousel-control')
    );
    const slides = Array.from(
        rootEl.querySelectorAll('.fl-sliding-carousel-slide')
    );

    if (!controlsSwiperEl || controls.length === 0 || slides.length === 0) {
        return;
    }

    let currentIndex = 0;
    let autoSlideTimer = null;
    let autoSlideActive = true;
    let userPaused = false;
    let controlsSwiper = null;

    // Preload all videos so they start quickly on slide change
    slides.forEach((slide) => {
        const video = slide.querySelector('video');
        if (video) {
            video.preload = 'auto';
            video.load();
        }
    });

    // --- Video helpers ---

    function getVideoFromSlide(slideEl) {
        return slideEl.querySelector('video');
    }

    function getAnimationButton(videoEl) {
        const container = videoEl.closest('.fl-video');
        return container && container.querySelector('.js-animation-pause');
    }

    function pauseVideo(videoEl) {
        videoEl.pause();
        videoEl.autoplay = false;
        const btn = getAnimationButton(videoEl);
        if (btn) {
            btn.querySelector('.js-pause-icon').hidden = true;
            btn.querySelector('.js-play-icon').hidden = false;
            btn.setAttribute('aria-label', btn.dataset.labelPlay);
            btn.classList.add('is-paused');
        }
    }

    function playVideo(videoEl) {
        videoEl.play();
        videoEl.autoplay = true;
        const btn = getAnimationButton(videoEl);
        if (btn) {
            btn.classList.remove('is-paused');
            btn.querySelector('.js-pause-icon').hidden = false;
            btn.querySelector('.js-play-icon').hidden = true;
            btn.setAttribute('aria-label', btn.dataset.labelPause);
        }
    }

    function pauseAllVideos() {
        slides.forEach((slide) => {
            const videoEl = getVideoFromSlide(slide);
            if (videoEl) {
                pauseVideo(videoEl);
            }
        });
    }

    // --- Slide activation ---

    function goToSlide(index) {
        const prevIndex = currentIndex;
        slides[prevIndex].classList.remove('is-active');
        slides[prevIndex].classList.add('is-exiting');
        slides[prevIndex].setAttribute('aria-hidden', 'true');
        controls[prevIndex].classList.remove('is-active');
        controls[prevIndex].setAttribute('aria-current', 'false');

        pauseAllVideos();
        currentIndex = index;

        const intervalMs = getMaxSlideIntervalMs();
        controls[currentIndex].style.setProperty(
            '--fl-slide-interval',
            `${intervalMs}ms`
        );
        controls[currentIndex].classList.add('is-active');
        controls[currentIndex].setAttribute('aria-current', 'true');

        // Force border animation restart by toggling a class on the box
        const box = controls[currentIndex].querySelector(
            '.fl-sliding-carousel-box'
        );
        if (box) {
            box.classList.add('no-animate');
            void box.offsetWidth;
            box.classList.remove('no-animate');
        }

        slides[currentIndex].classList.add('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'false');

        if (!userPaused) {
            const videoEl = getVideoFromSlide(slides[currentIndex]);
            if (videoEl) {
                videoEl.currentTime = 0;
                playVideo(videoEl);
            }
        }

        if (controlsSwiper && controlsSwiper.realIndex !== currentIndex) {
            controlsSwiper.slideToLoop(currentIndex);
        }

        // Clean up exiting slide after fade completes (matches --token-transition-slow)
        setTimeout(() => {
            slides[prevIndex].classList.remove('is-exiting');
        }, 300);
    }

    // --- Autoplay ---

    function getMaxSlideIntervalMs() {
        let maxMs = 0;
        for (const slide of slides) {
            const videoEl = getVideoFromSlide(slide);
            if (videoEl && !isNaN(videoEl.duration) && videoEl.duration > 0) {
                maxMs = Math.max(maxMs, videoEl.duration * 1000);
            }
        }
        return maxMs > 0 ? maxMs : AUTO_PLAY_INTERVAL_MS;
    }

    function scheduleNextSlide() {
        const intervalMs = getMaxSlideIntervalMs();
        autoSlideTimer = setTimeout(() => {
            goToSlide((currentIndex + 1) % slides.length);
            scheduleNextSlide();
        }, intervalMs);
    }

    function startAutoSlide() {
        scheduleNextSlide();
    }

    function stopAutoSlide() {
        clearTimeout(autoSlideTimer);
        autoSlideTimer = null;
        autoSlideActive = false;
    }

    function restartAutoSlide() {
        clearInterval(autoSlideTimer);
        autoSlideActive = true;
        autoSlideTimer = setInterval(() => {
            goToSlide((currentIndex + 1) % slides.length);
        }, AUTO_PLAY_INTERVAL_MS);
    }

    // --- Controls (desktop click + keyboard) ---

    controls.forEach((ctrl, idx) => {
        ctrl.addEventListener('click', () => {
            if (idx !== currentIndex) {
                goToSlide(idx);
                restartAutoSlide();
            }
        });

        ctrl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                ctrl.click();
            }
        });
    });

    // --- Video pause buttons ---

    slides.forEach((slide) => {
        const btn = slide.querySelector('.js-animation-pause');
        if (!btn) return;
        btn.addEventListener('click', () => {
            const videoEl = getVideoFromSlide(slide);
            if (!videoEl) return;
            userPaused = !userPaused;
            if (userPaused) {
                pauseVideo(videoEl);
                rootEl.classList.add('is-paused');
            } else {
                playVideo(videoEl);
                rootEl.classList.remove('is-paused');
            }
        });
    });

    // --- Mobile controls Swiper ---

    const mq = window.matchMedia('(min-width: 900px)');

    const controlsListEl = controlsSwiperEl.querySelector(
        '.fl-sliding-carousel-controls'
    );

    function initControlsSwiper() {
        if (controlsSwiper) return;
        // Set row layout BEFORE Swiper measures slide widths
        if (controlsListEl) controlsListEl.style.flexDirection = 'row';
        controlsSwiper = new Swiper(controlsSwiperEl, {
            modules: [Pagination],
            wrapperClass: 'fl-sliding-carousel-controls',
            slideClass: 'fl-sliding-carousel-control',
            centeredSlides: true,
            slidesPerView: 1.2,
            spaceBetween: 16,
            speed: 400,
            rewind: true,
            pagination: {
                el: paginationEl,
                clickable: true,
                bulletClass: 'fl-sliding-carousel-dot',
                bulletActiveClass: 'is-active',
                // Use <button> with aria-label for accessibility
                renderBullet: (index, className) =>
                    `<button class="${className}" aria-label="Go to slide ${index + 1}"></button>`
            }
        });
        controlsSwiper.on('slideChange', () => {
            const idx = controlsSwiper.realIndex;
            if (idx !== currentIndex) {
                if (autoSlideActive) stopAutoSlide();
                goToSlide(idx);
            }
        });
        controlsSwiper.slideToLoop(currentIndex, 0);
    }

    function destroyControlsSwiper() {
        if (!controlsSwiper) return;
        controlsSwiper.destroy(true, true);
        controlsSwiper = null;
        if (controlsListEl) controlsListEl.style.flexDirection = '';
    }

    mq.addEventListener('change', (e) => {
        if (e.matches) {
            destroyControlsSwiper();
        } else {
            initControlsSwiper();
        }
    });

    if (!mq.matches) {
        initControlsSwiper();
    }

    // --- Visibility ---

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearTimeout(autoSlideTimer);
        } else if (autoSlideActive) {
            startAutoSlide();
        }
    });

    // --- Init ---

    pauseAllVideos();
    goToSlide(0);
    startAutoSlide();

    // If any video hasn't loaded metadata yet, the interval above used the
    // fallback. Once all metadata is available, restart the active slide so
    // the animation and timer reflect the actual max video duration.
    const pendingMetadata = slides
        .map(getVideoFromSlide)
        .filter((v) => v && isNaN(v.duration))
        .map(
            (v) =>
                new Promise((resolve) => {
                    v.addEventListener('loadedmetadata', resolve, {
                        once: true
                    });
                    v.addEventListener('error', resolve, { once: true });
                })
        );

    if (pendingMetadata.length > 0) {
        Promise.all(pendingMetadata).then(() => {
            if (!autoSlideActive) return;
            const intervalMs = getMaxSlideIntervalMs();
            const ctrl = controls[currentIndex];
            ctrl.classList.remove('is-active');
            ctrl.style.setProperty('--fl-slide-interval', `${intervalMs}ms`);
            void ctrl.offsetWidth; // force reflow to restart the CSS animation
            ctrl.classList.add('is-active');
            clearTimeout(autoSlideTimer);
            scheduleNextSlide();
        });
    }
}

export default function setupSlidingCarousels() {
    document.addEventListener('DOMContentLoaded', () => {
        document
            .querySelectorAll('[data-js="fl-sliding-carousel"]')
            .forEach(initSlidingCarousel);
    });
}
