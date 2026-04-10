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
    let autoPlayTimer = null;
    let autoPlayActive = true;

    function activate(index) {
        controls[currentIndex].classList.remove('is-active');
        controls[currentIndex].setAttribute('aria-current', 'false');
        slides[currentIndex].classList.remove('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'true');

        currentIndex = index;

        controls[currentIndex].classList.add('is-active');
        controls[currentIndex].setAttribute('aria-current', 'true');
        slides[currentIndex].classList.add('is-active');
        slides[currentIndex].setAttribute('aria-hidden', 'false');
    }

    function startAutoPlay() {
        autoPlayTimer = setInterval(() => {
            activate((currentIndex + 1) % slides.length);
        }, AUTO_PLAY_INTERVAL_MS);
    }

    function stopAutoPlay() {
        clearInterval(autoPlayTimer);
        autoPlayTimer = null;
        autoPlayActive = false;
        rootEl.classList.add('is-paused');
    }

    controls.forEach((control, idx) => {
        control.addEventListener('click', () => {
            if (autoPlayActive) {
                stopAutoPlay();
            }
            if (idx !== currentIndex) {
                activate(idx);
            }
        });

        control.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                control.click();
            }
        });
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(autoPlayTimer);
        } else if (autoPlayActive) {
            startAutoPlay();
        }
    });

    startAutoPlay();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.fl-carousel').forEach(initFlare26Carousel);
    document
        .querySelectorAll('[data-js="fl-sliding-carousel"]')
        .forEach(initSlidingCarousel);
});
