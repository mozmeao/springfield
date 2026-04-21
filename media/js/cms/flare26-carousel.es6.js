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

export default function setupCarousels() {
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.fl-carousel').forEach(initFlare26Carousel);
    });
}
