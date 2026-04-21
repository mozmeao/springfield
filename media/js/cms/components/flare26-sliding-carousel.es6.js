/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Swiper from 'swiper';
import { Pagination } from 'swiper/modules';

const AUTO_PLAY_INTERVAL_MS = 24000;

class SlidingCarousel {
    constructor(rootEl) {
        this.rootEl = rootEl;
        this.controlsSwiperEl = rootEl.querySelector(
            '.fl-sliding-carousel-controls-swiper'
        );
        this.paginationEl = rootEl.querySelector(
            '.fl-sliding-carousel-pagination'
        );
        this.controls = Array.from(
            rootEl.querySelectorAll('.fl-sliding-carousel-control')
        );
        this.slides = Array.from(
            rootEl.querySelectorAll('.fl-sliding-carousel-slide')
        );
        this.controlsListEl = this.controlsSwiperEl
            ? this.controlsSwiperEl.querySelector(
                  '.fl-sliding-carousel-controls'
              )
            : null;

        if (
            !this.controlsSwiperEl ||
            this.controls.length === 0 ||
            this.slides.length === 0
        ) {
            return;
        }

        this.currentIndex = 0;
        this.autoSlideTimer = null;
        this.autoSlideActive = true;
        this.userPaused = false;
        this.controlsSwiper = null;

        // Preload all videos so they start quickly on slide change
        this.slides.forEach((slide) => {
            const video = slide.querySelector('video');
            if (video) {
                video.preload = 'auto';
                video.load();
            }
        });

        this._bindEvents();
        this._init();
    }

    // --- Video helpers ---

    getVideoFromSlide(slideEl) {
        return slideEl.querySelector('video');
    }

    getAnimationButton(videoEl) {
        const container = videoEl.closest('.fl-video');
        return container && container.querySelector('.js-animation-pause');
    }

    pauseVideo(videoEl) {
        videoEl.pause();
        videoEl.autoplay = false;
        const btn = this.getAnimationButton(videoEl);
        if (btn) {
            btn.querySelector('.js-pause-icon').hidden = true;
            btn.querySelector('.js-play-icon').hidden = false;
            btn.setAttribute('aria-label', btn.dataset.labelPlay);
            btn.classList.add('is-paused');
        }
    }

    playVideo(videoEl) {
        videoEl.play();
        videoEl.autoplay = true;
        const btn = this.getAnimationButton(videoEl);
        if (btn) {
            btn.classList.remove('is-paused');
            btn.querySelector('.js-pause-icon').hidden = false;
            btn.querySelector('.js-play-icon').hidden = true;
            btn.setAttribute('aria-label', btn.dataset.labelPause);
        }
    }

    pauseAllVideos() {
        this.slides.forEach((slide) => {
            const videoEl = this.getVideoFromSlide(slide);
            if (videoEl) {
                this.pauseVideo(videoEl);
            }
        });
    }

    // --- Slide activation ---

    goToSlide(index) {
        const prevIndex = this.currentIndex;
        this.slides[prevIndex].classList.remove('is-active');
        this.slides[prevIndex].classList.add('is-exiting');
        this.slides[prevIndex].setAttribute('aria-hidden', 'true');
        this.controls[prevIndex].classList.remove('is-active');
        this.controls[prevIndex].setAttribute('aria-current', 'false');

        this.pauseAllVideos();
        this.currentIndex = index;

        const intervalMs = this.getMaxSlideIntervalMs();
        this.controls[this.currentIndex].style.setProperty(
            '--fl-slide-interval',
            `${intervalMs}ms`
        );
        this.controls[this.currentIndex].classList.add('is-active');
        this.controls[this.currentIndex].setAttribute('aria-current', 'true');

        // Force border animation restart by toggling a class on the box
        const box = this.controls[this.currentIndex].querySelector(
            '.fl-sliding-carousel-box'
        );
        if (box) {
            box.classList.add('no-animate');
            void box.offsetWidth;
            box.classList.remove('no-animate');
        }

        this.slides[this.currentIndex].classList.add('is-active');
        this.slides[this.currentIndex].setAttribute('aria-hidden', 'false');

        if (!this.userPaused) {
            const videoEl = this.getVideoFromSlide(
                this.slides[this.currentIndex]
            );
            if (videoEl) {
                videoEl.currentTime = 0;
                this.playVideo(videoEl);
            }
        }

        if (
            this.controlsSwiper &&
            this.controlsSwiper.realIndex !== this.currentIndex
        ) {
            this.controlsSwiper.slideToLoop(this.currentIndex);
        }

        // Clean up exiting slide after fade completes (matches --token-transition-slow)
        setTimeout(() => {
            this.slides[prevIndex].classList.remove('is-exiting');
        }, 300);
    }

    // --- Autoplay ---

    getMaxSlideIntervalMs() {
        let maxMs = 0;
        for (const slide of this.slides) {
            const videoEl = this.getVideoFromSlide(slide);
            if (videoEl && !isNaN(videoEl.duration) && videoEl.duration > 0) {
                maxMs = Math.max(maxMs, videoEl.duration * 1000);
            }
        }
        return maxMs > 0 ? maxMs : AUTO_PLAY_INTERVAL_MS;
    }

    scheduleNextSlide() {
        const intervalMs = this.getMaxSlideIntervalMs();
        this.autoSlideTimer = setTimeout(() => {
            this.goToSlide((this.currentIndex + 1) % this.slides.length);
            this.scheduleNextSlide();
        }, intervalMs);
    }

    startAutoSlide() {
        this.scheduleNextSlide();
    }

    stopAutoSlide() {
        clearTimeout(this.autoSlideTimer);
        this.autoSlideTimer = null;
        this.autoSlideActive = false;
    }

    restartAutoSlide() {
        clearInterval(this.autoSlideTimer);
        this.autoSlideActive = true;
        this.autoSlideTimer = setInterval(() => {
            this.goToSlide((this.currentIndex + 1) % this.slides.length);
        }, AUTO_PLAY_INTERVAL_MS);
    }

    // --- Mobile controls Swiper ---

    initControlsSwiper() {
        if (this.controlsSwiper) return;
        // Set row layout BEFORE Swiper measures slide widths
        if (this.controlsListEl) {
            this.controlsListEl.style.flexDirection = 'row';
        }
        this.controlsSwiper = new Swiper(this.controlsSwiperEl, {
            modules: [Pagination],
            wrapperClass: 'fl-sliding-carousel-controls',
            slideClass: 'fl-sliding-carousel-control',
            centeredSlides: true,
            slidesPerView: 1.2,
            spaceBetween: 16,
            speed: 400,
            rewind: true,
            pagination: {
                el: this.paginationEl,
                clickable: true,
                bulletClass: 'fl-sliding-carousel-dot',
                bulletActiveClass: 'is-active',
                // Use <button> with aria-label for accessibility
                renderBullet: (index, className) =>
                    `<button class="${className}" aria-label="Go to slide ${index + 1}"></button>`
            }
        });
        this.controlsSwiper.on('slideChange', () => {
            const idx = this.controlsSwiper.realIndex;
            if (idx !== this.currentIndex) {
                if (this.autoSlideActive) this.stopAutoSlide();
                this.goToSlide(idx);
            }
        });
        this.controlsSwiper.slideToLoop(this.currentIndex, 0);
    }

    destroyControlsSwiper() {
        if (!this.controlsSwiper) return;
        this.controlsSwiper.destroy(true, true);
        this.controlsSwiper = null;
        if (this.controlsListEl) {
            this.controlsListEl.style.flexDirection = '';
        }
    }

    // --- Event binding ---

    _bindEvents() {
        this.controls.forEach((ctrl, idx) => {
            ctrl.addEventListener('click', () => {
                if (idx !== this.currentIndex) {
                    this.goToSlide(idx);
                    this.restartAutoSlide();
                }
            });
            ctrl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    ctrl.click();
                }
            });
        });

        this.slides.forEach((slide) => {
            const btn = slide.querySelector('.js-animation-pause');
            if (!btn) return;
            btn.addEventListener('click', () => {
                const videoEl = this.getVideoFromSlide(slide);
                if (!videoEl) return;
                this.userPaused = !this.userPaused;
                if (this.userPaused) {
                    this.pauseVideo(videoEl);
                    this.rootEl.classList.add('is-paused');
                } else {
                    this.playVideo(videoEl);
                    this.rootEl.classList.remove('is-paused');
                }
            });
        });

        const mq = window.matchMedia('(min-width: 900px)');
        mq.addEventListener('change', (e) => {
            if (e.matches) {
                this.destroyControlsSwiper();
            } else {
                this.initControlsSwiper();
            }
        });
        if (!mq.matches) {
            this.initControlsSwiper();
        }

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearTimeout(this.autoSlideTimer);
            } else if (this.autoSlideActive) {
                this.startAutoSlide();
            }
        });
    }

    // --- Init ---

    _init() {
        this.pauseAllVideos();
        this.goToSlide(0);
        this.startAutoSlide();

        // If any video hasn't loaded metadata yet, the interval above used the
        // fallback. Once all metadata is available, restart the active slide so
        // the animation and timer reflect the actual max video duration.
        const pendingMetadata = this.slides
            .map((slide) => this.getVideoFromSlide(slide))
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
                if (!this.autoSlideActive) return;
                const intervalMs = this.getMaxSlideIntervalMs();
                const ctrl = this.controls[this.currentIndex];
                ctrl.classList.remove('is-active');
                ctrl.style.setProperty(
                    '--fl-slide-interval',
                    `${intervalMs}ms`
                );
                void ctrl.offsetWidth; // force reflow to restart the CSS animation
                ctrl.classList.add('is-active');
                clearTimeout(this.autoSlideTimer);
                this.scheduleNextSlide();
            });
        }
    }
}

export default function setupSlidingCarousels() {
    document.addEventListener('DOMContentLoaded', () => {
        document
            .querySelectorAll('[data-js="fl-sliding-carousel"]')
            .forEach((el) => new SlidingCarousel(el));
    });
}
