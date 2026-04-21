/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Swiper from 'swiper';
import { Autoplay } from 'swiper/modules';

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

    // based on https://codepen.io/jarvis73045/pen/rNgwbNJ
    swiperWrapperEl.addEventListener('pointerenter', (e) => {
        if (e.pointerType !== 'mouse') return;
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

    swiperWrapperEl.addEventListener('pointerleave', (e) => {
        if (e.pointerType !== 'mouse') return;

        const distance =
            swiperInstance.width * swiperInstance.activeIndex +
            swiperInstance.getTranslate();

        // Avoid distance that is exactly 0
        duration = distance !== 0 ? duration : 0;
        swiperInstance.slideTo(swiperInstance.activeIndex, duration);
        startTimer = setTimeout(() => {
            swiperInstance.autoplay.start();
        }, duration);
    });
}

export default function setupScrollingCardGrid() {
    document.addEventListener('DOMContentLoaded', () => {
        document
            .querySelectorAll('[data-js="fl-card-grid-scroll"]')
            .forEach(initScrollingCardGrid);
    });
}
