/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Swiper from 'swiper';
import { EffectFade } from 'swiper/modules';

function initFlare26Carousel(rootEl) {
    const viewportEl = rootEl.querySelector('.fl-carousel-viewport');
    const controls = Array.from(
        rootEl.querySelectorAll('.fl-carousel-control-item')
    );
    const slideCount = rootEl.querySelectorAll('.fl-carousel-slide').length;

    if (!viewportEl || controls.length === 0 || slideCount === 0) {
        return;
    }

    const swiper = new Swiper(viewportEl, {
        modules: [EffectFade],
        wrapperClass: 'fl-carousel-container',
        slideClass: 'fl-carousel-slide',
        effect: 'fade',
        fadeEffect: { crossFade: true },
        loop: true,
        allowTouchMove: false,
        speed: 400
    });

    const onSlideChange = () => {
        controls.forEach((control, idx) => {
            control.classList.toggle('active', idx === swiper.realIndex);
        });
    };

    swiper.on('slideChange', onSlideChange);
    onSlideChange();

    controls.forEach((controlEl, idx) => {
        controlEl.addEventListener('click', (e) => {
            e.preventDefault();
            if (idx !== swiper.realIndex) {
                swiper.slideToLoop(idx);
            }
        });

        controlEl.addEventListener('animationend', (e) => {
            if (e.animationName === 'progress-circle' && slideCount > 1) {
                swiper.slideNext();
            }
        });
    });

    document.addEventListener('visibilitychange', () => {
        rootEl.classList.toggle('is-paused', document.hidden);
    });
}

const AUTO_PLAY_INTERVAL_MS = 10000;

function initSlidingCarousel(rootEl) {
    const controls = Array.from(
        rootEl.querySelectorAll('.fl-sliding-carousel-control')
    );
    const slides = Array.from(
        rootEl.querySelectorAll('.fl-sliding-carousel-slide')
    );

    if (controls.length === 0 || slides.length === 0) {
        return;
    }

    let currentIndex = 0;
    let autoSlideTimer = null;
    let autoSlideActive = true;
    let userPaused = false;

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
        }
    }

    function playVideo(videoEl) {
        videoEl.play();
        videoEl.autoplay = true;
        const btn = getAnimationButton(videoEl);
        if (btn) {
            btn.querySelector('.js-pause-icon').hidden = false;
            btn.querySelector('.js-play-icon').hidden = true;
            btn.setAttribute('aria-label', btn.dataset.labelPause);
        }
    }

    function pauseAllVideos() {
        slides.forEach((slide) => {
            const videoEl = getVideoFromSlide(slide);
            if (videoEl) {
                videoEl.currentTime = 0;
                pauseVideo(videoEl);
            }
        });
    }

    // --- Slide activation ---

    function activateSlideByIndex(index) {
        controls[currentIndex].classList.remove('is-active');
        controls[currentIndex].setAttribute('aria-current', 'false');
        slides[currentIndex].classList.remove('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'true');

        pauseAllVideos();
        currentIndex = index;

        controls[currentIndex].classList.add('is-active');
        controls[currentIndex].setAttribute('aria-current', 'true');
        slides[currentIndex].classList.add('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'false');

        if (!userPaused) {
            const videoEl = getVideoFromSlide(slides[currentIndex]);
            if (videoEl) {
                playVideo(videoEl);
            }
        }
    }

    // --- Auto-slide ---

    function startAutoSlide() {
        activateSlideByIndex(0);
        autoSlideTimer = setInterval(() => {
            activateSlideByIndex((currentIndex + 1) % slides.length);
        }, AUTO_PLAY_INTERVAL_MS);
    }

    function stopAutoSlide() {
        clearInterval(autoSlideTimer);
        autoSlideTimer = null;
        autoSlideActive = false;
        rootEl.classList.add('is-paused');
    }

    // --- Event wiring ---

    controls.forEach((control, idx) => {
        control.addEventListener('click', () => {
            if (autoSlideActive) {
                stopAutoSlide();
            }
            if (idx !== currentIndex) {
                activateSlideByIndex(idx);
            }
        });

        control.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                control.click();
            }
        });
    });

    slides.forEach((slide) => {
        const btn = slide.querySelector('.js-animation-pause');
        if (!btn) return;
        btn.addEventListener('click', () => {
            const videoEl = getVideoFromSlide(slide);
            if (!videoEl) return;
            userPaused = !userPaused;
            if (userPaused) {
                pauseVideo(videoEl);
            } else {
                playVideo(videoEl);
            }
        });
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(autoSlideTimer);
        } else if (autoSlideActive) {
            startAutoSlide();
        }
    });

    // --- Init ---

    pauseAllVideos();
    startAutoSlide();
}

function initScrollingCardGrid(el) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const SPEED = 0.3; // pixels per frame
    let paused = false;
    let position = 0;

    // Clone all children for a seamless loop
    const originals = Array.from(el.children);
    originals.forEach((card) => {
        const clone = card.cloneNode(true);
        clone.setAttribute('aria-hidden', 'true');
        el.appendChild(clone);
    });

    // Measure the width of one full set (originals only)
    function getLoopWidth() {
        const gap = parseFloat(getComputedStyle(el).gap) || 0;
        return originals.reduce((sum, card) => sum + card.offsetWidth + gap, 0);
    }

    function step() {
        if (!paused) {
            position += SPEED;
            const loopWidth = getLoopWidth();
            if (position >= loopWidth) {
                position -= loopWidth;
            }
            el.scrollLeft = Math.floor(position);
        }
        requestAnimationFrame(step);
    }

    // --- Hover pause ---
    el.addEventListener('mouseenter', () => {
        paused = true;
    });
    el.addEventListener('mouseleave', () => {
        paused = false;
    });
    el.addEventListener('focusin', () => {
        paused = true;
    });
    el.addEventListener('focusout', () => {
        paused = false;
    });

    // --- Click-and-drag scroll ---
    let dragging = false;
    let dragStartX = 0;
    let dragStartPosition = 0;

    el.addEventListener('mousedown', (e) => {
        dragging = true;
        paused = true;
        dragStartX = e.clientX;
        dragStartPosition = position;
        el.style.cursor = 'grabbing';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        const delta = dragStartX - e.clientX;
        const loopWidth = getLoopWidth();
        position =
            (((dragStartPosition + delta) % loopWidth) + loopWidth) % loopWidth;
        el.scrollLeft = Math.floor(position);
    });

    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        el.style.cursor = '';
        // Keep paused only if mouse is still over the element
        if (!el.matches(':hover')) paused = false;
    });

    requestAnimationFrame(step);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.fl-carousel').forEach(initFlare26Carousel);
    document
        .querySelectorAll('[data-js="fl-sliding-carousel"]')
        .forEach(initSlidingCarousel);
    document
        .querySelectorAll('[data-js="fl-card-grid-scroll"]')
        .forEach(initScrollingCardGrid);
});
