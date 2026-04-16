/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Swiper from 'swiper';
import { Autoplay, EffectFade } from 'swiper/modules';

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

    // --- Dot pagination ---

    const dots = [];

    if (paginationEl) {
        slides.forEach((_, i) => {
            const dot = document.createElement('button');
            dot.className = 'fl-sliding-carousel-dot';
            dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
            dot.addEventListener('click', () => {
                if (autoSlideActive) stopAutoSlide();
                goToSlide(i);
            });
            paginationEl.appendChild(dot);
            dots.push(dot);
        });
    }

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

    function goToSlide(index) {
        controls[currentIndex].classList.remove('is-active');
        controls[currentIndex].setAttribute('aria-current', 'false');
        slides[currentIndex].classList.remove('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'true');
        if (dots[currentIndex])
            dots[currentIndex].classList.remove('is-active');

        pauseAllVideos();
        currentIndex = index;

        controls[currentIndex].classList.add('is-active');
        controls[currentIndex].setAttribute('aria-current', 'true');
        slides[currentIndex].classList.add('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'false');
        if (dots[currentIndex]) dots[currentIndex].classList.add('is-active');

        if (!userPaused) {
            const videoEl = getVideoFromSlide(slides[currentIndex]);
            if (videoEl) playVideo(videoEl);
        }

        if (controlsSwiper && controlsSwiper.realIndex !== currentIndex) {
            controlsSwiper.slideToLoop(currentIndex);
        }
    }

    // --- Autoplay ---

    function startAutoSlide() {
        autoSlideTimer = setInterval(() => {
            goToSlide((currentIndex + 1) % slides.length);
        }, AUTO_PLAY_INTERVAL_MS);
    }

    function stopAutoSlide() {
        clearInterval(autoSlideTimer);
        autoSlideTimer = null;
        autoSlideActive = false;
        rootEl.classList.add('is-paused');
    }

    // --- Controls (desktop click + keyboard) ---

    controls.forEach((ctrl, idx) => {
        ctrl.addEventListener('click', () => {
            if (autoSlideActive) stopAutoSlide();
            if (idx !== currentIndex) goToSlide(idx);
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
            } else {
                playVideo(videoEl);
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
            wrapperClass: 'fl-sliding-carousel-controls',
            slideClass: 'fl-sliding-carousel-control',
            centeredSlides: true,
            slidesPerView: 1.2,
            spaceBetween: 16,
            speed: 400,
            rewind: true
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
            clearInterval(autoSlideTimer);
        } else if (autoSlideActive) {
            startAutoSlide();
        }
    });

    // --- Init ---

    pauseAllVideos();
    goToSlide(0);
    startAutoSlide();
}

function initScrollingCardGrid(swiperWrapperEl) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    let duration;
    let distanceRatio;
    let startTimer;

    const swiperInstance = new Swiper(swiperWrapperEl, {
        modules: [Autoplay],
        wrapperClass: 'fl-card-grid-scroll-inner',
        slideClass: 'fl-card-grid-scroll-item',
        slidesPerView: 'auto',
        loop: true,
        speed: 8000,
        spaceBetween: 16, // --token-spacing-lg
        autoplay: {
            delay: 0,
            disableOnInteraction: false,
            waitForTransition: true
        }
    });

    const setEasing = (easing = 'ease') => {
        swiperWrapperEl.style.setProperty('--easing', easing);
    };

    // based on https://codepen.io/jarvis73045/pen/rNgwbNJ
    swiperWrapperEl.addEventListener('mouseover', () => {
        if (startTimer) clearTimeout(startTimer);

        // Stop slide at current translate.
        swiperInstance.setTranslate(swiperInstance.getTranslate());

        // Calculating the distance between current slide and next slide.
        // 0.3 is equal to 30% distance to the next slide.
        // distanceRatio = Math.abs((swiper.width * swiper.activeIndex + swiper.getTranslate()) / swiper.width);

        // currentSlideWidth for slidesPerView > 1
        const currentSlideWidth =
            swiperInstance.slides[swiperInstance.activeIndex].offsetWidth;
        distanceRatio = Math.abs(
            (currentSlideWidth * swiperInstance.activeIndex +
                swiperInstance.getTranslate()) /
                currentSlideWidth
        );

        // The duration that playing to the next slide
        duration = swiperInstance.params.speed * distanceRatio;
        swiperInstance.autoplay.stop();
    });

    swiperWrapperEl.addEventListener('mouseout', () => {
        const distance =
            swiperInstance.width * swiperInstance.activeIndex +
            swiperInstance.getTranslate();

        // Avoid distance that is exactly 0
        duration = distance !== 0 ? duration : 0;
        swiperInstance.slideTo(swiperInstance.activeIndex, duration);
        startTimer = setTimeout(() => {
            setEasing('linear');
            swiperInstance.autoplay.start();
        }, duration);
    });
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
