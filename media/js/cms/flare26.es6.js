/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

document.addEventListener('DOMContentLoaded', () => {
    initCarousel();
});

function initCarousel() {
    const carouselItems = document.querySelectorAll(
        '.fl-carousel-control-item'
    );

    carouselItems.forEach((item) => {
        item.addEventListener('click', (e) => {
            e.preventDefault();

            const targetImageId = item.getAttribute('aria-controls');
            if (!targetImageId) {
                return;
            }

            const targetImage = document.getElementById(targetImageId);
            if (!targetImage) {
                return;
            }

            const allItems = document.querySelectorAll(
                '.fl-carousel-control-item'
            );
            const allImages = document.querySelectorAll('.fl-carousel-image');

            allItems.forEach((controlItem) => {
                controlItem.classList.remove('active');
            });

            allImages.forEach((image) => {
                image.classList.remove('active');
            });

            item.classList.add('active');
            targetImage.classList.add('active');
        });
    });
}
